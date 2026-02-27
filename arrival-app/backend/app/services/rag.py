"""
RAG service — document chunking and retrieval via Pinecone integrated inference.
Pinecone handles embedding automatically using the model configured on the index
(e.g. multilingual-e5-large), so NO external embedding API (OpenAI) is needed.
Gracefully degrades if PINECONE_API_KEY is not set.
"""

import asyncio
import time
import tempfile
import os

from app import config

_pc_index = None

CHUNK_SIZE = 2000       # characters (~500 tokens)
CHUNK_OVERLAP = 200     # characters overlap between chunks


class DocumentTooShortError(Exception):
    """Raised when a document's extracted text is too short to index."""
    pass


def _get_pinecone_index():
    """Lazy-init Pinecone index. Returns None if no API key."""
    global _pc_index
    if _pc_index is None:
        if not config.PINECONE_API_KEY:
            return None
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=config.PINECONE_API_KEY)
            _pc_index = pc.Index(config.PINECONE_INDEX_NAME)
        except Exception as e:
            print(f"[rag] Failed to init Pinecone: {e}")
            return None
    return _pc_index


def _reset_pinecone_index():
    """Reset the cached Pinecone index so the next call re-initializes."""
    global _pc_index
    _pc_index = None


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF via a temp file (Bug #21)."""
    import fitz  # pymupdf
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        doc = fitz.open(filename=tmp_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text.strip()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from .docx bytes using python-docx (Bug #22)."""
    try:
        import docx
        import io
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        print("[rag] python-docx not installed — cannot extract .docx files. "
              "Install with: pip install python-docx")
        return ""
    except Exception as e:
        print(f"[rag] Failed to extract text from .docx: {e}")
        return ""


def extract_text_from_file(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Extract text from supported file types. Returns empty string for unsupported."""
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        return extract_text_from_pdf_bytes(file_bytes)
    elif (content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          or filename.lower().endswith(".docx")):
        # Bug #22: .docx support
        return extract_text_from_docx(file_bytes)
    elif content_type.startswith("text/") or filename.lower().endswith((".txt", ".md", ".csv")):
        # Bug #43: Non-UTF-8 text decode — try utf-8 first, then latin-1 as fallback
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")
    else:
        # Images, videos, and other binary files — skip
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    Tries to break at sentence boundaries for cleaner chunks.
    """
    # Bug #19: Lower the threshold from 100 to 20 characters
    if not text or len(text) < 20:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary if not at end of text
        if end < len(text):
            last_period = chunk.rfind(". ")
            last_newline = chunk.rfind("\n")
            break_at = max(last_period, last_newline)
            if break_at > chunk_size // 2:
                chunk = chunk[: break_at + 1]
                end = start + break_at + 1

        chunks.append(chunk.strip())

        new_start = end - overlap
        # Bug #8: Infinite loop guard — if start doesn't advance, force it forward
        if new_start <= start:
            new_start = start + 1
            if new_start >= len(text):
                break
        start = new_start

    # Filter out very short chunks
    return [c for c in chunks if len(c) > 50]


async def index_document(
    document_id: str,
    user_id: str,
    filename: str,
    file_bytes: bytes,
    content_type: str,
    team_id: str | None = None,
) -> int:
    """
    Extract text, chunk, and upsert records to Pinecone.
    Pinecone auto-embeds using the model configured on the index.
    Returns chunk count (0 if skipped or failed).
    Raises DocumentTooShortError if text is too short (Bug #19).

    Bug #1: If team_id is provided, upserts into namespace=f"team_{team_id}"
    instead of user_id, so all team members can search the same namespace.
    """
    index = _get_pinecone_index()
    if not index:
        return 0

    # Extract text
    text = extract_text_from_file(file_bytes, content_type, filename)
    if not text:
        print(f"[rag] No text extracted from {filename} ({content_type})")
        return 0

    # Bug #19: Raise a meaningful error if text is too short
    if len(text) < 20:
        raise DocumentTooShortError(
            f"Document '{filename}' has only {len(text)} characters of text. "
            "Minimum is 20 characters for indexing."
        )

    # Chunk
    chunks = chunk_text(text)
    if not chunks:
        print(f"[rag] No chunks produced from {filename} (text length: {len(text)})")
        return 0

    # Bug #1: Determine the namespace
    namespace = f"team_{team_id}" if team_id else user_id

    # Build records — Pinecone integrated inference auto-embeds the 'text' field
    records = []
    for i, chunk in enumerate(chunks):
        records.append({
            "_id": f"{document_id}_{i}",
            "text": chunk,  # Already sized to CHUNK_SIZE (2000 chars)
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "chunk_index": i,
        })

    # Upsert to Pinecone in batches of 100
    # Bug #20: Add retry on batch upsert; Bug #7: Reset index on connection errors
    total_upserted = 0
    try:
        for batch_start in range(0, len(records), 100):
            batch = records[batch_start : batch_start + 100]
            success = False
            for attempt in range(2):  # Bug #20: 1 retry (2 attempts total)
                try:
                    index.upsert_records(namespace=namespace, records=batch)
                    total_upserted += len(batch)
                    success = True
                    break
                except (ConnectionError, OSError, TimeoutError) as conn_err:
                    # Bug #7: Reset cached index on connection/network errors
                    _reset_pinecone_index()
                    index = _get_pinecone_index()
                    if index is None:
                        print(f"[rag] Pinecone re-init failed after connection error: {conn_err}")
                        return total_upserted
                    if attempt == 0:
                        print(f"[rag] Pinecone upsert connection error, retrying in 2s: {conn_err}")
                        await asyncio.sleep(2)
                    else:
                        print(f"[rag] Pinecone upsert failed after retry: {conn_err}")
                except Exception as e:
                    # Bug #7: Also reset on generic Pinecone errors that may be transient
                    if "connect" in str(e).lower() or "timeout" in str(e).lower():
                        _reset_pinecone_index()
                        index = _get_pinecone_index()
                        if index is None:
                            return total_upserted
                    if attempt == 0:
                        print(f"[rag] Pinecone upsert error, retrying in 2s: {e}")
                        await asyncio.sleep(2)
                    else:
                        print(f"[rag] Pinecone upsert failed after retry: {e}")
            if not success:
                # Bug #20: Return the count of successfully upserted chunks so far
                print(f"[rag] Partial index: {total_upserted}/{len(records)} chunks for {filename}")
                return total_upserted

        print(f"[rag] Indexed {total_upserted} chunks for {filename}")
        return total_upserted
    except Exception as e:
        # Bug #7: Reset on unexpected errors
        if "connect" in str(e).lower() or "timeout" in str(e).lower():
            _reset_pinecone_index()
        print(f"[rag] Pinecone upsert error: {e}")
        return total_upserted


async def delete_document_vectors(document_id: str, user_id: str, team_id: str | None = None) -> None:
    """
    Remove all vectors for a document from Pinecone.
    Bug #23: Use ID-based deletion pattern instead of metadata filtering.
    """
    index = _get_pinecone_index()
    if not index:
        return

    namespace = f"team_{team_id}" if team_id else user_id

    try:
        # Bug #23: Generate IDs matching the pattern used during upsert
        # Delete in batches of IDs: document_id_0, document_id_1, ..., document_id_N
        # Use a reasonable max (1000 chunks = 2M chars of text, should cover any document)
        MAX_CHUNKS = 1000
        ids_to_delete = [f"{document_id}_{i}" for i in range(MAX_CHUNKS)]

        # Delete in batches of 100 IDs
        for batch_start in range(0, len(ids_to_delete), 100):
            batch = ids_to_delete[batch_start : batch_start + 100]
            try:
                index.delete(ids=batch, namespace=namespace)
            except Exception:
                pass  # Some IDs won't exist, that's fine

        print(f"[rag] Deleted vectors for document {document_id}")
    except (ConnectionError, OSError, TimeoutError) as conn_err:
        # Bug #7: Reset cached index on connection errors
        _reset_pinecone_index()
        print(f"[rag] Vector delete connection error (index reset): {conn_err}")
    except Exception as e:
        if "connect" in str(e).lower() or "timeout" in str(e).lower():
            _reset_pinecone_index()
        print(f"[rag] Vector delete error: {e}")


async def retrieve_context(
    user_id: str,
    query: str,
    top_k: int = 5,
    team_id: str | None = None,
) -> list[dict]:
    """
    Search Pinecone with text query — Pinecone auto-embeds using the
    model configured on the index. Returns list of { text, filename, score }.

    Bug #1: If team_id is provided, query BOTH user namespace AND team namespace,
    then merge and deduplicate results sorted by relevance score.
    """
    index = _get_pinecone_index()
    if not index:
        return []

    def _do_search(namespace: str) -> list[dict]:
        """Run a single Pinecone search against the given namespace."""
        try:
            results = index.search(
                namespace=namespace,
                query={"inputs": {"text": query}, "top_k": top_k},
                fields=["text", "filename"],
            )

            context = []
            for hit in results.result.hits:
                score = hit.get("_score", 0)
                if score > 0.3:  # Relevance threshold
                    fields = hit.get("fields", {})
                    context.append({
                        "text": fields.get("text", ""),
                        "filename": fields.get("filename", ""),
                        "score": score,
                    })
            return context
        except (ConnectionError, OSError, TimeoutError) as conn_err:
            # Bug #7: Reset cached index on connection errors
            _reset_pinecone_index()
            print(f"[rag] Retrieve connection error (index reset): {conn_err}")
            return []
        except Exception as e:
            if "connect" in str(e).lower() or "timeout" in str(e).lower():
                _reset_pinecone_index()
            print(f"[rag] Retrieve error: {e}")
            return []

    try:
        # Always search the user's personal namespace
        user_results = _do_search(user_id)

        # Bug #1: If team_id provided, also search the team namespace
        if team_id:
            team_namespace = f"team_{team_id}"
            team_results = _do_search(team_namespace)

            # Merge and deduplicate by text content
            seen_texts = set()
            merged = []
            for item in user_results + team_results:
                text_key = item["text"][:200]  # Use first 200 chars as dedup key
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    merged.append(item)

            # Sort by relevance score descending
            merged.sort(key=lambda x: x["score"], reverse=True)
            return merged[:top_k]

        return user_results

    except Exception as e:
        print(f"[rag] Retrieve error: {e}")
        return []
