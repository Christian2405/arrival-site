"""
Error Codes API router — GET /api/error-codes
Serves the built-in error code database to the frontend for browsing.
No auth required — these are public reference data.
"""

from fastapi import APIRouter
from app.services.error_codes import ERROR_CODE_DB

router = APIRouter()

# Brand display name overrides (where .title() doesn't produce the right result)
_BRAND_DISPLAY_NAMES = {
    "ao_smith": "AO Smith",
    "bradford_white": "Bradford White",
}


def _brand_display_name(brand_key: str) -> str:
    """Convert brand_key (e.g. 'ao_smith') to display name (e.g. 'AO Smith')."""
    return _BRAND_DISPLAY_NAMES.get(brand_key, brand_key.replace("_", " ").title())


def _flatten_brand_codes(brand_data: dict) -> list[dict]:
    """
    Flatten the nested brand structure (equipment_type → codes) into a flat list.
    ERROR_CODE_DB is: brand → { equipment_type: { code: { meaning, causes, fix } } }
    Returns: [{ code, meaning, causes, fix, equipment_type }, ...]
    """
    flat = []
    for equip_type, codes in brand_data.items():
        if not isinstance(codes, dict):
            continue
        for code_key, info in codes.items():
            if not isinstance(info, dict):
                continue
            flat.append({
                "code": code_key,
                "meaning": info.get("meaning", ""),
                "causes": info.get("causes", []),
                "fix": info.get("action", ""),
                "equipment_type": equip_type,
            })
    return flat


def _count_brand_codes(brand_data: dict) -> int:
    """Count total unique codes across all equipment types for a brand."""
    total = 0
    seen_equip_dicts = set()  # Avoid double-counting aliased equipment types
    for equip_type, codes in brand_data.items():
        if not isinstance(codes, dict):
            continue
        # Multiple equipment type keys can point to the same dict (aliases)
        dict_id = id(codes)
        if dict_id in seen_equip_dicts:
            continue
        seen_equip_dicts.add(dict_id)
        total += len(codes)
    return total


@router.get("/error-codes")
async def get_brands():
    """
    Returns all brands with their code counts.
    Used by the frontend Codes page to show the brand list.
    """
    brands = []
    for brand_key, brand_data in ERROR_CODE_DB.items():
        code_count = _count_brand_codes(brand_data)
        brands.append({
            "id": brand_key,
            "name": _brand_display_name(brand_key),
            "code_count": code_count,
        })

    # Sort by name
    brands.sort(key=lambda b: b["name"])
    return {"brands": brands, "total_codes": sum(b["code_count"] for b in brands)}


@router.get("/error-codes/{brand_id}")
async def get_brand_codes(brand_id: str):
    """
    Returns all error codes for a specific brand, flattened across equipment types.
    """
    brand_data = ERROR_CODE_DB.get(brand_id, {})
    if not brand_data:
        return {"brand": brand_id, "brand_id": brand_id, "codes": []}

    # Flatten nested structure and deduplicate aliased equipment types
    seen_equip_dicts = set()
    code_list = []
    for equip_type, codes in brand_data.items():
        if not isinstance(codes, dict):
            continue
        dict_id = id(codes)
        if dict_id in seen_equip_dicts:
            continue
        seen_equip_dicts.add(dict_id)
        for code_key, info in codes.items():
            if not isinstance(info, dict):
                continue
            code_list.append({
                "code": code_key,
                "meaning": info.get("meaning", ""),
                "causes": info.get("causes", []),
                "fix": info.get("action", ""),
            })

    # Sort codes naturally
    code_list.sort(key=lambda c: c["code"])

    return {
        "brand": _brand_display_name(brand_id),
        "brand_id": brand_id,
        "codes": code_list,
    }
