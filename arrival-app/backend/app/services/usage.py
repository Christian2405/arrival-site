"""
Usage limits — tier-based query and document limits.
Centralizes all limit checking logic for reuse across routers.

Tier definitions are the single source of truth for the backend.
Uses the existing `queries` and `documents` tables — no new tables needed.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone

from app import config
from app.services.supabase import _get_client, _service_db_headers

logger = logging.getLogger(__name__)

# ── Tier definitions ──────────────────────────────────────────────
TIER_LIMITS = {
    "free":       {"max_queries_per_day": 8,     "max_documents": 3,    "job_mode": True},
    "pro":        {"max_queries_per_day": 30,    "max_documents": 20,   "job_mode": True},
    "business":   {"max_queries_per_day": 9999,  "max_documents": 9999, "job_mode": True},
    "enterprise": {"max_queries_per_day": 9999,  "max_documents": 9999, "job_mode": True},
}

# In-memory plan cache: user_id -> (plan, timestamp)
# Using OrderedDict for LRU eviction instead of clearing all entries
_plan_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
_plan_cache_lock = asyncio.Lock()
_PLAN_CACHE_TTL = 60.0  # seconds
_PLAN_CACHE_MAX = 5000   # max entries before LRU eviction


def get_tier_limits(plan: str) -> dict:
    """Return the limits dict for a given plan."""
    if plan not in TIER_LIMITS:
        logger.warning(f"[usage] Unknown plan '{plan}' — defaulting to free tier")
    return TIER_LIMITS.get(plan, TIER_LIMITS["free"])


async def get_user_plan(user_id: str) -> str:
    """
    Look up the user's active subscription plan from the subscriptions table.
    Cached in-memory for 60 seconds to avoid repeated DB calls.
    Returns 'free' if no active subscription found.
    """
    now = time.monotonic()

    # Check cache (with lock to prevent race conditions on shared dict)
    async with _plan_cache_lock:
        if user_id in _plan_cache:
            cached_plan, cached_at = _plan_cache[user_id]
            if now - cached_at < _PLAN_CACHE_TTL:
                # Move to end for LRU tracking
                _plan_cache.move_to_end(user_id)
                return cached_plan

    plan = "free"  # default

    try:
        client = _get_client()
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/subscriptions",
            headers=_service_db_headers(),
            params={
                "user_id": f"eq.{user_id}",
                "status": "eq.active",
                "select": "plan,trial_ends_at,stripe_subscription_id",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        resp.raise_for_status()
        rows = resp.json()
        if rows:
            row = rows[0]
            sub_plan = row.get("plan", "free")
            trial_ends_at = row.get("trial_ends_at")
            stripe_id = row.get("stripe_subscription_id")

            # If trial has expired and no Stripe subscription (no payment), downgrade to free
            if trial_ends_at and not stripe_id:
                try:
                    trial_end = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > trial_end:
                        logger.info(f"[usage] Trial expired for {user_id[:8]}... — downgrading to free")
                        plan = "free"
                    else:
                        plan = sub_plan
                except (ValueError, TypeError):
                    plan = sub_plan
            else:
                plan = sub_plan
    except Exception as e:
        logger.warning(f"[usage] Plan lookup failed for {user_id[:8]}...: {e}")

    # Update cache with LRU eviction (evict oldest entries, not nuke entire cache)
    async with _plan_cache_lock:
        _plan_cache[user_id] = (plan, now)
        while len(_plan_cache) > _PLAN_CACHE_MAX:
            _plan_cache.popitem(last=False)  # Remove oldest entry
    return plan


async def get_daily_query_count(user_id: str) -> int:
    """
    Count queries made by this user today (UTC midnight reset).
    Uses the existing queries table with Supabase count=exact header.
    """
    today_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")

    try:
        client = _get_client()
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/queries",
            headers={
                **_service_db_headers(),
                "Prefer": "count=exact",
            },
            params={
                "user_id": f"eq.{user_id}",
                "created_at": f"gte.{today_start}",
                "select": "id",
                "limit": "0",
            },
        )
        resp.raise_for_status()
        # Supabase returns count in content-range header: "0-0/42" or "*/0"
        content_range = resp.headers.get("content-range", "")
        if "/" in content_range:
            count_str = content_range.split("/")[-1]
            if count_str != "*":
                try:
                    return int(count_str)
                except ValueError:
                    logger.warning(f"[usage] Malformed content-range count: '{count_str}'")
                    return 0
        return 0
    except Exception as e:
        logger.warning(f"[usage] Query count failed for {user_id[:8]}...: {e}")
        return 0  # Fail open — don't block users on count errors


async def get_document_count(user_id: str) -> int:
    """
    Count personal documents owned by this user.
    Team documents (team_id != null) don't count against individual limits.
    """
    try:
        client = _get_client()
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/documents",
            headers={
                **_service_db_headers(),
                "Prefer": "count=exact",
            },
            params={
                "uploaded_by": f"eq.{user_id}",
                "team_id": "is.null",
                "select": "id",
                "limit": "0",
            },
        )
        resp.raise_for_status()
        content_range = resp.headers.get("content-range", "")
        if "/" in content_range:
            count_str = content_range.split("/")[-1]
            if count_str != "*":
                try:
                    return int(count_str)
                except ValueError:
                    logger.warning(f"[usage] Malformed content-range count: '{count_str}'")
                    return 0
        return 0
    except Exception as e:
        logger.warning(f"[usage] Document count failed for {user_id[:8]}...: {e}")
        return 0


async def check_query_limit(user_id: str) -> dict:
    """
    Check if user is allowed to make another query.
    Returns: { allowed, queries_used, query_limit, plan }
    query_limit of -1 means unlimited.
    """
    plan = await get_user_plan(user_id)
    limits = get_tier_limits(plan)
    max_queries = limits["max_queries_per_day"]

    # Unlimited tier — skip the count query
    if max_queries >= 9999:
        return {
            "allowed": True,
            "queries_used": 0,
            "query_limit": -1,
            "plan": plan,
        }

    queries_used = await get_daily_query_count(user_id)

    return {
        "allowed": queries_used < max_queries,
        "queries_used": queries_used,
        "query_limit": max_queries,
        "plan": plan,
    }


async def check_document_limit(user_id: str) -> dict:
    """
    Check if user is allowed to upload another document.
    Returns: { allowed, documents_count, document_limit, plan }
    document_limit of -1 means unlimited.
    """
    plan = await get_user_plan(user_id)
    limits = get_tier_limits(plan)
    max_docs = limits["max_documents"]

    # Unlimited tier — skip the count query
    if max_docs >= 9999:
        return {
            "allowed": True,
            "documents_count": 0,
            "document_limit": -1,
            "plan": plan,
        }

    doc_count = await get_document_count(user_id)

    return {
        "allowed": doc_count < max_docs,
        "documents_count": doc_count,
        "document_limit": max_docs,
        "plan": plan,
    }
