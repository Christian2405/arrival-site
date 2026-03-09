"""
Memory service — user preferences via Supabase.

Replaces Mem0 with a lightweight Supabase-backed preference system.
Tracks brands the user works on, equipment types, and preferred units.
Auto-extracts preferences from conversation patterns over time.

Gracefully degrades if Supabase is not configured.
"""

import asyncio
import logging
import time

from app import config

logger = logging.getLogger(__name__)

# Hard timeout for preference retrieval
RETRIEVE_TIMEOUT = 2.0  # seconds

# Known brands for auto-extraction (lowercase)
_KNOWN_BRANDS = {
    "carrier", "bryant", "trane", "american standard", "goodman", "amana",
    "lennox", "rheem", "ruud", "york", "coleman", "daikin", "mitsubishi",
    "fujitsu", "lg", "samsung", "bosch", "navien", "rinnai", "noritz",
    "takagi", "ao smith", "bradford white", "weil-mclain", "buderus",
    "viessmann", "lochinvar", "mr cool", "midea", "gree", "cooper hunter",
    "haier", "heil", "comfortmaker", "tempstar", "keeprite", "arcoaire",
}

# Known equipment types for auto-extraction (lowercase)
_KNOWN_EQUIPMENT = {
    "furnace", "air conditioner", "heat pump", "mini split", "boiler",
    "water heater", "tankless", "condenser", "air handler", "package unit",
    "rooftop unit", "chiller", "ductless", "vrf", "vrv", "geothermal",
    "thermostat", "humidifier", "dehumidifier",
}


async def retrieve_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    """
    Retrieve user preferences for this user.
    Returns a list of preference strings to inject into the system prompt.
    Hard timeout of 2 seconds — returns empty rather than blocking chat.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return []

    try:
        t0 = time.monotonic()

        import httpx
        async with httpx.AsyncClient(timeout=RETRIEVE_TIMEOUT) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/user_preferences",
                headers={
                    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "preferred_units,common_brands,equipment_types",
                },
            )

            if resp.status_code != 200:
                return []

            rows = resp.json()
            if not rows:
                return []

            prefs = rows[0]
            memories = []

            brands = prefs.get("common_brands") or []
            if brands:
                memories.append(f"This tech frequently works on: {', '.join(brands)}")

            equipment = prefs.get("equipment_types") or []
            if equipment:
                memories.append(f"Common equipment: {', '.join(equipment)}")

            units = prefs.get("preferred_units", "imperial")
            if units == "metric":
                memories.append("Prefers metric units (Celsius, mm, liters, kPa)")

            elapsed = time.monotonic() - t0
            if memories:
                logger.info(f"[memory] Retrieved {len(memories)} preferences in {elapsed:.2f}s")
            return memories

    except Exception as e:
        logger.debug(f"[memory] Preference retrieval skipped: {e}")
        return []


async def store_memory(user_id: str, messages: list[dict]) -> None:
    """
    Extract brand and equipment mentions from the conversation
    and update user preferences if they appear frequently.
    Fire-and-forget — errors are logged but not raised.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return

    try:
        # Extract brands and equipment from the conversation
        all_text = " ".join(
            msg.get("content", "").lower() for msg in messages if msg.get("content")
        )

        mentioned_brands = [b for b in _KNOWN_BRANDS if b in all_text]
        mentioned_equipment = [e for e in _KNOWN_EQUIPMENT if e in all_text]

        if not mentioned_brands and not mentioned_equipment:
            return

        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {
                "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
            }

            # Get existing preferences
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/user_preferences",
                headers=headers,
                params={"user_id": f"eq.{user_id}", "select": "common_brands,equipment_types"},
            )

            if resp.status_code == 200 and resp.json():
                # Update existing
                existing = resp.json()[0]
                existing_brands = set(existing.get("common_brands") or [])
                existing_equipment = set(existing.get("equipment_types") or [])

                new_brands = existing_brands | set(mentioned_brands)
                new_equipment = existing_equipment | set(mentioned_equipment)

                # Only update if something changed (keep lists reasonable)
                if new_brands != existing_brands or new_equipment != existing_equipment:
                    await client.patch(
                        f"{config.SUPABASE_URL}/rest/v1/user_preferences",
                        headers=headers,
                        params={"user_id": f"eq.{user_id}"},
                        json={
                            "common_brands": list(new_brands)[:20],  # Cap at 20
                            "equipment_types": list(new_equipment)[:15],  # Cap at 15
                            "updated_at": "now()",
                        },
                    )
                    logger.info(f"[memory] Updated preferences: +{len(mentioned_brands)} brands, +{len(mentioned_equipment)} equipment")
            else:
                # Insert new row
                if mentioned_brands or mentioned_equipment:
                    await client.post(
                        f"{config.SUPABASE_URL}/rest/v1/user_preferences",
                        headers=headers,
                        json={
                            "user_id": user_id,
                            "common_brands": mentioned_brands[:20],
                            "equipment_types": mentioned_equipment[:15],
                        },
                    )
                    logger.info(f"[memory] Created preferences for {user_id[:8]}…")

    except Exception as e:
        logger.debug(f"[memory] Preference update skipped: {e}")
