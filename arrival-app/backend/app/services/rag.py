"""
RAG service — document chunking and retrieval via Pinecone integrated inference.
Pinecone handles embedding automatically using the model configured on the index
(e.g. multilingual-e5-large), so NO external embedding API (OpenAI) is needed.
Gracefully degrades if PINECONE_API_KEY is not set.
"""

from app import config

_pc_index = None

CHUNK_SIZE = 2000       # characters (~500 tokens)
CHUNK_OVERLAP = 200     # characters overlap between chunks


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


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    import fitz  # pymupdf
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    return text.strip()


def extract_text_from_file(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Extract text from supported file types. Returns empty string for unsupported."""
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif content_type.startswith("text/") or filename.lower().endswith((".txt", ".md", ".csv")):
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        # Images, videos, and other binary files — skip
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    Tries to break at sentence boundaries for cleaner chunks.
    """
    if not text or len(text) < 100:
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
        start = end - overlap

    # Filter out very short chunks
    return [c for c in chunks if len(c) > 50]


async def index_document(
    document_id: str,
    user_id: str,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> int:
    """
    Extract text, chunk, and upsert records to Pinecone.
    Pinecone auto-embeds using the model configured on the index.
    Returns chunk count (0 if skipped or failed).
    """
    index = _get_pinecone_index()
    if not index:
        return 0

    # Extract text
    text = extract_text_from_file(file_bytes, content_type, filename)
    if not text:
        print(f"[rag] No text extracted from {filename} ({content_type})")
        return 0

    # Chunk
    chunks = chunk_text(text)
    if not chunks:
        print(f"[rag] No chunks produced from {filename} (text length: {len(text)})")
        return 0

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

    # Upsert to Pinecone in batches of 100 (namespace = user_id for isolation)
    try:
        for batch_start in range(0, len(records), 100):
            batch = records[batch_start : batch_start + 100]
            index.upsert_records(namespace=user_id, records=batch)
        print(f"[rag] Indexed {len(chunks)} chunks for {filename}")
        return len(chunks)
    except Exception as e:
        print(f"[rag] Pinecone upsert error: {e}")
        return 0


async def delete_document_vectors(document_id: str, user_id: str) -> None:
    """Remove all vectors for a document from Pinecone."""
    index = _get_pinecone_index()
    if not index:
        return

    try:
        # Pinecone serverless supports delete by metadata filter
        index.delete(
            filter={"document_id": {"$eq": document_id}},
            namespace=user_id,
        )
        print(f"[rag] Deleted vectors for document {document_id}")
    except Exception as e:
        print(f"[rag] Vector delete error: {e}")


async def retrieve_context(
    user_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Search Pinecone with text query — Pinecone auto-embeds using the
    model configured on the index. Returns list of { text, filename, score }.
    """
    index = _get_pinecone_index()
    if not index:
        return []

    try:
        results = index.search(
            namespace=user_id,
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
    except Exception as e:
        print(f"[rag] Retrieve error: {e}")
        return []
