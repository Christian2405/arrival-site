"""
Download manufacturer PDFs for seeding the global_knowledge base.

Usage:
    python -m scripts.download_manuals
    python -m scripts.download_manuals --output ./manuals/

Downloads PDFs from free, publicly available manufacturer sources.
After downloading, run:
    python -m scripts.seed_knowledge_base ./manuals/
"""

import asyncio
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# PDF Sources — free, publicly available manufacturer documentation
# ---------------------------------------------------------------------------

PDF_SOURCES = [
    # --- Rinnai Tankless ---
    {
        "filename": "Rinnai_Tankless_Diagnostic_Codes.pdf",
        "url": "https://media.rinnai.us/salsify_asset/2b8fa85d-1d96-41ce-86f6-c5d5b2b1e9e9/100000652-Troubleshooting%20TWH%20Diagnostic%20Codes%20(3).pdf",
        "brand": "Rinnai",
    },
    # --- AO Smith ---
    {
        "filename": "AO_Smith_Maintenance_Troubleshooting.pdf",
        "url": "https://university.hotwater.com/wp-content/uploads/sites/2/2022/08/HD_Smith_TSMaintenenceGuide_06-30-21_lowres.pdf",
        "brand": "AO Smith",
    },
    {
        "filename": "AO_Smith_Commercial_Service_Handbook.pdf",
        "url": "https://assets.aosmith.com/damroot/Original/10004/100274940.pdf",
        "brand": "AO Smith",
    },
    {
        "filename": "AO_Smith_Hybrid_Heat_Pump_Handbook.pdf",
        "url": "https://assets.aosmith.com/damroot/Original/10004/100268628.pdf",
        "brand": "AO Smith",
    },
    # --- Lennox ---
    {
        "filename": "Lennox_Communicating_System_Alert_Codes.pdf",
        "url": "https://www.lennox.com/dA/d89d9db1dd/100017c.pdf",
        "brand": "Lennox",
    },
    # --- Goodman ---
    {
        "filename": "Goodman_90_GM9S_GC9S_Service_Manual.pdf",
        "url": "https://www.hvacdirect.com/media/pdf/90%20GM9S%20GC9S%20Service%20Manual.pdf",
        "brand": "Goodman",
    },
    {
        "filename": "Goodman_GCVC96_Service_Instructions.pdf",
        "url": "https://www.hvacdirect.com/media/hvac/pdf/GCVC96-Service.pdf",
        "brand": "Goodman",
    },
    # --- Square D ---
    {
        "filename": "Square_D_QO_QOB_Breaker_Catalog.pdf",
        "url": "https://www.ressupply.com/documents/square_d/QO_and_QOB_Circuit_Breakers.pdf",
        "brand": "Square D",
    },
    # --- NEC ---
    {
        "filename": "NEC_Ampacity_Tables.pdf",
        "url": "https://usawire-cable.com/wp-content/uploads/nec-ampacities.pdf",
        "brand": "NEC",
    },
    # --- Trane ---
    {
        "filename": "Trane_Alert_Codes.pdf",
        "url": "https://star-supply.com/content/Trane%20Alert%20Codes.pdf",
        "brand": "Trane",
    },
]


async def download_pdf(client: httpx.AsyncClient, source: dict, output_dir: Path) -> bool:
    """Download a single PDF. Returns True on success."""
    filepath = output_dir / source["filename"]

    if filepath.exists():
        print(f"  SKIP (already exists): {source['filename']}")
        return True

    try:
        print(f"  Downloading {source['filename']}...")
        response = await client.get(
            source["url"],
            follow_redirects=True,
            timeout=60.0,
        )

        if response.status_code == 200:
            filepath.write_bytes(response.content)
            size_mb = len(response.content) / (1024 * 1024)
            print(f"  OK: {source['filename']} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"  FAILED ({response.status_code}): {source['filename']}")
            return False
    except Exception as e:
        print(f"  ERROR: {source['filename']} — {e}")
        return False


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download manufacturer PDFs")
    parser.add_argument("--output", type=str, default="./manuals/", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(PDF_SOURCES)} manufacturer PDFs to {output_dir}/\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/pdf,*/*",
    }

    async with httpx.AsyncClient(headers=headers) as client:
        results = []
        for source in PDF_SOURCES:
            brand = source["brand"]
            print(f"[{brand}]")
            success = await download_pdf(client, source, output_dir)
            results.append((source["filename"], success))
            print()

    # Summary
    succeeded = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n{'='*60}")
    print(f"Downloaded: {succeeded}/{len(results)}")
    if failed:
        print(f"Failed: {failed}")
        print("\nFailed files:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    print(f"\nNext step: python -m scripts.seed_knowledge_base {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
