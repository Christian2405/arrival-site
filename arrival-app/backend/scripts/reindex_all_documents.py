"""
Re-index all documents — fixes docs uploaded while Pinecone quota was exhausted.

Fetches every document from the Supabase documents table (using service role key
so it bypasses RLS), downloads from Storage, and re-indexes into Pinecone.

Usage:
    python -m scripts.reindex_all_documents

    # Dry run — list docs without re-indexing:
    python -m scripts.reindex_all_documents --dry-run

    # Re-index a specific user only:
    python -m scripts.reindex_all_documents --user-id <uuid>
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
_env_file = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_file, override=True)

import httpx
from app import config
from app.services.rag import index_document, PineconeQuotaError


async def fetch_all_documents(user_id: str | None = None) -> list[dict]:
    """Fetch all documents from Supabase using service role key (bypasses RLS)."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    headers = {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    params = {"select": "id,storage_path,uploaded_by,team_id,filename", "limit": "1000"}
    if user_id:
        params["uploaded_by"] = f"eq.{user_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/documents",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


async def download_file(storage_path: str) -> bytes | None:
    """Download a file from Supabase Storage using service role key."""
    url = (
        f"{config.SUPABASE_URL}/storage/v1/object/"
        f"{config.SUPABASE_STORAGE_BUCKET}/{storage_path}"
    )
    headers = {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            print(f"    SKIP: File not found in storage: {storage_path}")
            return None
        resp.raise_for_status()
        return resp.content


def guess_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    elif lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif lower.endswith((".txt", ".md", ".csv")):
        return "text/plain"
    return "application/octet-stream"


async def main():
    parser = argparse.ArgumentParser(description="Re-index all Supabase documents into Pinecone")
    parser.add_argument("--dry-run", action="store_true", help="List docs without re-indexing")
    parser.add_argument("--user-id", help="Only re-index docs for this user UUID")
    args = parser.parse_args()

    if not config.PINECONE_API_KEY:
        print("ERROR: PINECONE_API_KEY not set in .env")
        sys.exit(1)

    print(f"Fetching documents from Supabase...")
    docs = await fetch_all_documents(user_id=args.user_id)
    print(f"Found {len(docs)} document(s)\n")

    if not docs:
        print("Nothing to index.")
        return

    if args.dry_run:
        for d in docs:
            print(f"  [{d.get('uploaded_by','?')[:8]}] {d.get('storage_path','?')}")
        return

    total_ok = 0
    total_fail = 0

    for doc in docs:
        doc_id = doc.get("id", "")
        storage_path = doc.get("storage_path", "")
        user_id = doc.get("uploaded_by", "")
        team_id = doc.get("team_id")

        # Strip timestamp prefix from filename for display
        raw_filename = storage_path.split("/")[-1] if storage_path else "unknown"
        filename = raw_filename.split("_", 1)[1] if "_" in raw_filename else raw_filename
        content_type = guess_content_type(filename)

        print(f"[{filename}] user={user_id[:8] if user_id else '?'}")
        print(f"  storage_path: {storage_path}")

        file_bytes = await download_file(storage_path)
        if file_bytes is None:
            total_fail += 1
            continue

        print(f"  Downloaded {len(file_bytes):,} bytes")

        try:
            chunks = await index_document(
                document_id=doc_id,
                user_id=user_id,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                team_id=team_id,
            )
            if chunks > 0:
                print(f"  ✓ Indexed {chunks} chunks")
                total_ok += 1
            else:
                print(f"  ✗ Indexed 0 chunks (no text extracted?)")
                total_fail += 1
        except PineconeQuotaError as e:
            print(f"  ✗ QUOTA ERROR: {e}")
            print("  Stopping — upgrade Pinecone plan and re-run.")
            break
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            total_fail += 1

        print()

    print(f"Done. {total_ok} succeeded, {total_fail} failed.")


if __name__ == "__main__":
    asyncio.run(main())
