"""
Account management router — DELETE /api/account
Handles account deletion (Apple App Store requirement).
"""

import logging
from fastapi import APIRouter, HTTPException, Request

from app import config
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.delete("/account")
async def delete_account(request: Request):
    """
    Delete the authenticated user's account and all associated data.
    Apple App Store requires this per guideline 5.1.1(v).
    """
    user = await get_current_user(request)
    user_id = user["user_id"]

    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Failed to delete account. Please contact support.")

    import httpx

    headers = {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Delete in order: dependent data first
            tables = [
                # Spatial data (CASCADE handles spatial_labels via spatial_clips FK)
                ("spatial_sequences", {"user_id": f"eq.{user_id}"}),
                ("spatial_clips", {"session_id": f"in.(select id from spatial_sessions where user_id=eq.{user_id})"}),
                ("spatial_sessions", {"user_id": f"eq.{user_id}"}),
                # Core user data
                ("queries", {"user_id": f"eq.{user_id}"}),
                ("saved_answers", {"user_id": f"eq.{user_id}"}),
                ("team_members", {"user_id": f"eq.{user_id}"}),
                ("subscriptions", {"user_id": f"eq.{user_id}"}),
                ("feedback", {"user_id": f"eq.{user_id}"}),
                ("user_preferences", {"user_id": f"eq.{user_id}"}),
                ("users", {"id": f"eq.{user_id}"}),
            ]
            for table_name, params in tables:
                resp = await client.delete(
                    f"{config.SUPABASE_URL}/rest/v1/{table_name}",
                    headers=headers,
                    params=params,
                )
                if resp.status_code >= 400:
                    logger.warning(f"[Account] {table_name} delete returned {resp.status_code} for {user_id}")

            # 6. Delete auth user (Supabase Admin API)
            del_auth_resp = await client.delete(
                f"{config.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers=headers,
            )
            del_auth_resp.raise_for_status()

        logger.info(f"[Account] Deleted account for user {user_id}")
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"[Account] Delete failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account. Please contact support.")
