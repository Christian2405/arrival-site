"""
Error Codes API router — GET /api/error-codes
Serves the built-in error code database to the frontend for browsing.
No auth required — these are public reference data.
"""

from fastapi import APIRouter
from app.services.error_codes import ERROR_CODE_DB

router = APIRouter()


@router.get("/error-codes")
async def get_brands():
    """
    Returns all brands with their code counts.
    Used by the frontend Codes page to show the brand list.
    """
    brands = []
    for brand_key, codes in ERROR_CODE_DB.items():
        # Convert brand_key to display name
        display_name = brand_key.replace("_", " ").title()
        if brand_key == "ao_smith":
            display_name = "AO Smith"
        elif brand_key == "bradford_white":
            display_name = "Bradford White"

        brands.append({
            "id": brand_key,
            "name": display_name,
            "code_count": len(codes),
        })

    # Sort by name
    brands.sort(key=lambda b: b["name"])
    return {"brands": brands, "total_codes": sum(b["code_count"] for b in brands)}


@router.get("/error-codes/{brand_id}")
async def get_brand_codes(brand_id: str):
    """
    Returns all error codes for a specific brand.
    """
    codes = ERROR_CODE_DB.get(brand_id, {})
    if not codes:
        return {"brand": brand_id, "codes": []}

    # Convert to list format
    code_list = []
    for code, info in codes.items():
        code_list.append({
            "code": code,
            "meaning": info.get("meaning", ""),
            "causes": info.get("causes", []),
            "fix": info.get("fix", ""),
        })

    # Sort codes naturally
    code_list.sort(key=lambda c: c["code"])

    display_name = brand_id.replace("_", " ").title()
    if brand_id == "ao_smith":
        display_name = "AO Smith"
    elif brand_id == "bradford_white":
        display_name = "Bradford White"

    return {
        "brand": display_name,
        "brand_id": brand_id,
        "codes": code_list,
    }
