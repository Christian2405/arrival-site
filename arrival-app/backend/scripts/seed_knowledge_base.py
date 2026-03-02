"""
Seed Knowledge Base — Index PDFs into Pinecone's `global_knowledge` namespace.

Usage:
    python -m scripts.seed_knowledge_base ./path/to/pdfs/

    # Or index a single file:
    python -m scripts.seed_knowledge_base ./manuals/rheem_fault_codes.pdf

Requires:
    PINECONE_API_KEY and PINECONE_INDEX_NAME set in .env (or environment).
"""

import asyncio
import os
import sys
from pathlib import Path

# Allow running as `python -m scripts.seed_knowledge_base` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.services.rag import (
    extract_text_from_file,
    chunk_text,
    chunk_text_smart,
    _get_pinecone_index,
)

NAMESPACE = "global_knowledge"


def _content_type_from_filename(filename: str) -> str:
    """Guess content type from file extension."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "md": "text/markdown",
        "csv": "text/csv",
    }.get(ext, "application/octet-stream")


async def index_file(filepath: Path) -> int:
    """Index a single file into the global_knowledge namespace. Returns chunk count."""
    index = _get_pinecone_index()
    if not index:
        print(f"  ERROR: Pinecone not configured (check PINECONE_API_KEY)")
        return 0

    filename = filepath.name
    content_type = _content_type_from_filename(filename)

    print(f"  Reading {filepath}...")
    file_bytes = filepath.read_bytes()

    text = extract_text_from_file(file_bytes, content_type, filename)
    if not text:
        print(f"  SKIP: No text extracted from {filename}")
        return 0

    print(f"  Extracted {len(text)} chars from {filename}")

    # Use structure-aware chunking for PDFs/docs (trade manuals)
    is_structured = filename.lower().endswith((".pdf", ".docx"))
    if is_structured:
        chunks = chunk_text_smart(text)
        if not chunks:
            chunks = chunk_text(text)  # Fallback
        print(f"  Smart-chunked into {len(chunks)} chunks")
    else:
        chunks = chunk_text(text)
    if not chunks:
        print(f"  SKIP: No chunks produced from {filename}")
        return 0

    # Use a stable document ID based on filename so re-runs overwrite
    doc_id = f"global_{filename.replace(' ', '_').replace('.', '_')}"

    records = []
    for i, chunk in enumerate(chunks):
        records.append({
            "_id": f"{doc_id}_{i}",
            "text": chunk,
            "document_id": doc_id,
            "user_id": "system",
            "filename": filename,
            "chunk_index": i,
        })

    # Upsert in batches of 96 (Pinecone integrated inference limit)
    total = 0
    for batch_start in range(0, len(records), 96):
        batch = records[batch_start : batch_start + 96]
        try:
            await asyncio.to_thread(
                index.upsert_records, namespace=NAMESPACE, records=batch
            )
            total += len(batch)
            print(f"  Upserted batch {batch_start // 96 + 1} ({len(batch)} records)")
        except Exception as e:
            print(f"  ERROR upserting batch: {e}")

    print(f"  Indexed {total} chunks for {filename}")
    return total


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.seed_knowledge_base <path-to-pdfs-or-file>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if not target.exists():
        print(f"ERROR: Path does not exist: {target}")
        sys.exit(1)

    # Check config
    if not config.PINECONE_API_KEY:
        print("ERROR: PINECONE_API_KEY not set. Check your .env file.")
        sys.exit(1)

    print(f"Pinecone index: {config.PINECONE_INDEX_NAME}")
    print(f"Namespace: {NAMESPACE}")
    print()

    files = []
    if target.is_file():
        files = [target]
    else:
        # Collect all supported files from directory
        for ext in ("*.pdf", "*.docx", "*.txt", "*.md"):
            files.extend(target.glob(ext))
        files.sort()

    if not files:
        print(f"No supported files found in {target}")
        sys.exit(1)

    print(f"Found {len(files)} file(s) to index:\n")

    total_chunks = 0
    for f in files:
        print(f"[{f.name}]")
        chunks = await index_file(f)
        total_chunks += chunks
        print()

    print(f"Done! Indexed {total_chunks} total chunks into '{NAMESPACE}' namespace.")


if __name__ == "__main__":
    asyncio.run(main())
