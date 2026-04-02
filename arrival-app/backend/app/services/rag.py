"""
RAG service — document chunking and retrieval via Pinecone integrated inference.
Pinecone handles embedding automatically using the model configured on the index
(e.g. multilingual-e5-large), so NO external embedding API (OpenAI) is needed.
Gracefully degrades if PINECONE_API_KEY is not set.
"""

import asyncio
import logging
import time
import tempfile
import os

from app import config

logger = logging.getLogger(__name__)

_pc_index = None

CHUNK_SIZE = 2000       # characters (~500 tokens)
CHUNK_OVERLAP = 200     # characters overlap between chunks


class DocumentTooShortError(Exception):
    """Raised when a document's extracted text is too short to index."""
    pass


class PineconeQuotaError(Exception):
    """Raised when Pinecone rejects the upsert due to embedding token quota exhaustion."""
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
            logger.warning(f"[rag] Failed to init Pinecone: {e}")
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
        logger.warning("[rag] python-docx not installed — cannot extract .docx files. "
                       "Install with: pip install python-docx")
        return ""
    except Exception as e:
        logger.warning(f"[rag] Failed to extract text from .docx: {e}")
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


# ---------------------------------------------------------------------------
# Structure-aware chunking — keeps tables, code blocks, and numbered lists intact
# ---------------------------------------------------------------------------

import re as _re

# Patterns that indicate structural boundaries we should NOT split within
_SECTION_HEADER = _re.compile(r"^(?:#{1,4}\s|[A-Z][A-Z\s]{3,}$|Chapter\s+\d|Section\s+\d)", _re.MULTILINE)
_TABLE_ROW = _re.compile(r"^\s*\|.*\|", _re.MULTILINE)
_NUMBERED_STEP = _re.compile(r"^\s*\d{1,2}[\.\)]\s", _re.MULTILINE)
_ERROR_CODE_LINE = _re.compile(
    r"(?:code|error|fault|blink|flash|LED|status)\s*[:=]?\s*(?:[A-Z]?\d{1,4})",
    _re.IGNORECASE,
)


def chunk_text_smart(text: str, max_chunk_size: int = 3000) -> list[str]:
    """
    Structure-aware chunking that keeps related content together.

    Strategy:
    1. Split text into "sections" using headers and double-newlines.
    2. Within each section, keep tables, numbered lists, and error code blocks intact.
    3. If a section exceeds max_chunk_size, fall back to sentence-boundary splitting.
    4. Small adjacent sections are merged up to max_chunk_size.

    This produces better RAG results for trade manuals because error code tables
    and troubleshooting steps stay as single chunks instead of being split mid-row.
    """
    if not text or len(text) < 20:
        return []

    # Step 1: Split into sections by double newlines or headers
    raw_sections = _re.split(r"\n\s*\n", text)

    # Step 2: Further split on headers within sections
    sections = []
    for section in raw_sections:
        # Check if this section contains multiple headers
        headers = list(_SECTION_HEADER.finditer(section))
        if len(headers) > 1:
            # Split at each header
            for i, match in enumerate(headers):
                start = match.start()
                end = headers[i + 1].start() if i + 1 < len(headers) else len(section)
                sub = section[start:end].strip()
                if sub:
                    sections.append(sub)
        elif section.strip():
            sections.append(section.strip())

    # Step 3: Merge small sections, keep large ones, split oversized ones
    chunks = []
    current_chunk = ""

    for section in sections:
        # Check if this section has structural content we want to keep intact
        has_table = bool(_TABLE_ROW.search(section))
        has_steps = len(_NUMBERED_STEP.findall(section)) >= 2
        has_error_codes = len(_ERROR_CODE_LINE.findall(section)) >= 2
        is_structural = has_table or has_steps or has_error_codes

        if is_structural and len(section) <= max_chunk_size:
            # Flush current buffer
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # Keep this structural section as its own chunk
            chunks.append(section)
        elif len(current_chunk) + len(section) + 2 <= max_chunk_size:
            # Merge into current chunk
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
        else:
            # Flush current buffer
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""

            if len(section) <= max_chunk_size:
                current_chunk = section
            else:
                # Oversized section — fall back to basic splitting
                sub_chunks = chunk_text(section, chunk_size=max_chunk_size, overlap=200)
                chunks.extend(sub_chunks)

    # Flush remaining
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

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
        logger.warning(f"[rag] No text extracted from {filename} ({content_type})")
        return 0

    # Bug #19: Raise a meaningful error if text is too short
    if len(text) < 20:
        raise DocumentTooShortError(
            f"Document '{filename}' has only {len(text)} characters of text. "
            "Minimum is 20 characters for indexing."
        )

    # Chunk — use structure-aware chunking for PDFs and docs (trade manuals),
    # basic chunking for plain text files
    is_structured = content_type == "application/pdf" or filename.lower().endswith((".pdf", ".docx"))
    if is_structured:
        chunks = chunk_text_smart(text)
        if not chunks:
            chunks = chunk_text(text)  # Fallback
        logger.info(f"[rag] Smart-chunked {filename}: {len(chunks)} chunks")
    else:
        chunks = chunk_text(text)
    if not chunks:
        logger.warning(f"[rag] No chunks produced from {filename} (text length: {len(text)})")
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
                    await asyncio.to_thread(index.upsert_records, namespace=namespace, records=batch)
                    total_upserted += len(batch)
                    success = True
                    break
                except (ConnectionError, OSError, TimeoutError) as conn_err:
                    # Bug #7: Reset cached index on connection/network errors
                    _reset_pinecone_index()
                    index = _get_pinecone_index()
                    if index is None:
                        logger.warning(f"[rag] Pinecone re-init failed after connection error: {conn_err}")
                        return total_upserted
                    if attempt == 0:
                        logger.warning(f"[rag] Pinecone upsert connection error, retrying in 2s: {conn_err}")
                        await asyncio.sleep(2)
                    else:
                        logger.warning(f"[rag] Pinecone upsert failed after retry: {conn_err}")
                except Exception as e:
                    # Quota exhaustion (429) — raise immediately, no point retrying
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "embedding token limit" in str(e).lower():
                        raise PineconeQuotaError(
                            "Document indexing failed: Pinecone embedding quota exhausted for this month. "
                            "Upgrade your Pinecone plan at app.pinecone.io to continue indexing documents."
                        )
                    # Bug #7: Also reset on generic Pinecone errors that may be transient
                    if "connect" in str(e).lower() or "timeout" in str(e).lower():
                        _reset_pinecone_index()
                        index = _get_pinecone_index()
                        if index is None:
                            return total_upserted
                    if attempt == 0:
                        logger.warning(f"[rag] Pinecone upsert error, retrying in 2s: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.warning(f"[rag] Pinecone upsert failed after retry: {e}")
            if not success:
                # Bug #20: Return the count of successfully upserted chunks so far
                logger.warning(f"[rag] Partial index: {total_upserted}/{len(records)} chunks for {filename}")
                return total_upserted

        logger.info(f"[rag] Indexed {total_upserted} chunks for {filename}")
        return total_upserted
    except Exception as e:
        # Bug #7: Reset on unexpected errors
        if "connect" in str(e).lower() or "timeout" in str(e).lower():
            _reset_pinecone_index()
        logger.warning(f"[rag] Pinecone upsert error: {e}")
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
                await asyncio.to_thread(index.delete, ids=batch, namespace=namespace)
            except Exception as batch_err:
                # IDs that don't exist are fine, but log real errors
                err_str = str(batch_err).lower()
                if "not found" not in err_str and "no vectors" not in err_str:
                    logger.warning(f"[rag] Vector batch delete error: {batch_err}")

        logger.info(f"[rag] Deleted vectors for document {document_id}")
    except (ConnectionError, OSError, TimeoutError) as conn_err:
        # Bug #7: Reset cached index on connection errors
        _reset_pinecone_index()
        logger.warning(f"[rag] Vector delete connection error (index reset): {conn_err}")
    except Exception as e:
        if "connect" in str(e).lower() or "timeout" in str(e).lower():
            _reset_pinecone_index()
        logger.warning(f"[rag] Vector delete error: {e}")


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
            all_scores = []
            for hit in results.result.hits:
                score = hit.get("_score", 0)
                all_scores.append(score)
                if score > 0.2:  # Relevance threshold — lowered from 0.3 to catch more valid results
                    fields = hit.get("fields", {})
                    context.append({
                        "text": fields.get("text", ""),
                        "filename": fields.get("filename", ""),
                        "score": score,
                    })
            if all_scores:
                logger.debug(f"[rag] {namespace}: scores={[round(s,3) for s in all_scores[:5]]}, kept={len(context)}")
            return context
        except (ConnectionError, OSError, TimeoutError) as conn_err:
            # Bug #7: Reset cached index on connection errors
            _reset_pinecone_index()
            logger.warning(f"[rag] Retrieve connection error (index reset): {conn_err}")
            return []
        except Exception as e:
            if "connect" in str(e).lower() or "timeout" in str(e).lower():
                _reset_pinecone_index()
            logger.warning(f"[rag] Retrieve error: {e}")
            return []

    RAG_TIMEOUT = 4.0  # seconds — return empty rather than blocking
    try:
        t0 = time.monotonic()

        # Build list of namespaces to search in parallel
        search_tasks = [
            asyncio.to_thread(_do_search, user_id),          # User's personal docs
            asyncio.to_thread(_do_search, "global_knowledge"),  # Shared knowledge base
        ]
        task_labels = ["user", "global"]

        if team_id:
            search_tasks.append(asyncio.to_thread(_do_search, f"team_{team_id}"))
            task_labels.append("team")

        # Run all namespace searches in parallel with timeout
        search_results = await asyncio.wait_for(
            asyncio.gather(*search_tasks, return_exceptions=True),
            timeout=RAG_TIMEOUT,
        )

        # Merge and deduplicate results from all namespaces
        seen_texts = set()
        merged = []
        for i, result in enumerate(search_results):
            if isinstance(result, Exception):
                logger.warning(f"[rag] {task_labels[i]} namespace search failed: {result}")
                continue
            is_personal = task_labels[i] in ("user", "team")
            for item in result:
                text_key = item["text"][:200]
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    # Tag so agent knows which source to cite
                    item = {**item, "is_personal": is_personal}
                    merged.append(item)

        # Sort by relevance score descending
        merged.sort(key=lambda x: x["score"], reverse=True)
        final = merged[:top_k]
        ns_label = "+".join(task_labels)
        elapsed = time.monotonic() - t0
        if final:
            top_files = [f"{r['filename']}({r['score']:.0%})" for r in final[:3]]
            logger.info(f"[rag] Search {ns_label} → {len(final)} results in {elapsed:.2f}s: {', '.join(top_files)}")
        else:
            logger.info(f"[rag] Search {ns_label} → 0 results in {elapsed:.2f}s")
        return final

    except asyncio.TimeoutError:
        logger.warning(f"[rag] Search TIMED OUT after {RAG_TIMEOUT}s — skipping RAG context")
        return []
    except Exception as e:
        logger.warning(f"[rag] Retrieve error: {e}")
        return []
