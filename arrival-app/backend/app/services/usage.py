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
    "free":       {"max_queries_per_day": 8,     "max_documents": 3,    "job_mode": True, "job_mode_minutes": 5},
    "pro":        {"max_queries_per_day": 30,    "max_documents": 10,   "job_mode": True, "job_mode_minutes": 30},
    "business":   {"max_queries_per_day": 9999,  "max_documents": 9999, "job_mode": True, "job_mode_minutes": -1},
    "enterprise": {"max_queries_per_day": 9999,  "max_documents": 9999, "job_mode": True, "job_mode_minutes": -1},
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

        # Auto-create pro trial if no subscription exists (self-heal if frontend insert failed)
        if not rows:
            try:
                from datetime import timedelta
                trial_end = datetime.now(timezone.utc) + timedelta(days=7)
                create_resp = await client.post(
                    f"{config.SUPABASE_URL}/rest/v1/subscriptions",
                    headers={**_service_db_headers(), "Prefer": "return=representation"},
                    json={
                        "user_id": user_id,
                        "plan": "pro",
                        "status": "active",
                        "trial_ends_at": trial_end.isoformat(),
                    },
                )
                if create_resp.status_code < 300:
                    rows = create_resp.json()
                    logger.info(f"[usage] Auto-created pro trial for {user_id[:8]}...")
                else:
                    logger.warning(f"[usage] Auto-create trial failed: {create_resp.status_code} {create_resp.text[:200]}")
            except Exception as e:
                logger.warning(f"[usage] Auto-create trial failed: {e}")

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


async def get_job_mode_seconds_today(user_id: str) -> int:
    """
    Get total job mode seconds used today by summing duration_seconds
    from job_mode_usage table. Includes currently-active sessions by
    calculating elapsed time from started_at.
    """
    today_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")

    try:
        client = _get_client()
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/job_mode_usage",
            headers=_service_db_headers(),
            params={
                "user_id": f"eq.{user_id}",
                "started_at": f"gte.{today_start}",
                "select": "duration_seconds,started_at,ended_at",
            },
        )
        resp.raise_for_status()
        rows = resp.json()

        total = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            dur = row.get("duration_seconds")
            if dur is not None:
                total += dur
            elif row.get("started_at") and not row.get("ended_at"):
                # Active session — calculate elapsed
                try:
                    started = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
                    total += int((now - started).total_seconds())
                except (ValueError, TypeError):
                    pass
        return total
    except Exception as e:
        logger.warning(f"[usage] Job mode time query failed for {user_id[:8]}...: {e}")
        return 0


async def log_job_mode_start(user_id: str, room_name: str) -> str | None:
    """Log the start of a job mode session. Returns the row ID."""
    try:
        client = _get_client()
        resp = await client.post(
            f"{config.SUPABASE_URL}/rest/v1/job_mode_usage",
            headers={**_service_db_headers(), "Prefer": "return=representation"},
            json={
                "user_id": user_id,
                "room_name": room_name,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        resp.raise_for_status()
        rows = resp.json()
        row_id = rows[0]["id"] if rows else None
        logger.info(f"[usage] Job mode session started for {user_id[:8]}... (id={row_id})")
        return row_id
    except Exception as e:
        logger.warning(f"[usage] Failed to log job mode start: {e}")
        return None


async def log_job_mode_end(row_id: str, duration_seconds: int):
    """Log the end of a job mode session."""
    try:
        client = _get_client()
        resp = await client.patch(
            f"{config.SUPABASE_URL}/rest/v1/job_mode_usage",
            headers=_service_db_headers(),
            params={"id": f"eq.{row_id}"},
            json={
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration_seconds,
            },
        )
        resp.raise_for_status()
        logger.info(f"[usage] Job mode session ended (id={row_id}, {duration_seconds}s)")
    except Exception as e:
        logger.warning(f"[usage] Failed to log job mode end: {e}")


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
