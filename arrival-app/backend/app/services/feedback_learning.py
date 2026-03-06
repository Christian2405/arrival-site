"""
Feedback learning service — the data flywheel.

Two mechanisms:
1. Correction cache: admin-reviewed corrections injected into system prompts
   when a new question matches a known correction (keyword overlap).
2. Negative feedback → Mem0: stores user-specific corrections as memories
   so the AI remembers what it got wrong for each user.

Both are non-blocking and gracefully degrade if services are unavailable.
"""

import asyncio
import logging
import time

import httpx

from app import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory correction cache — refreshed every 5 minutes from Supabase
# ---------------------------------------------------------------------------

_corrections_cache: list[dict] = []
_cache_timestamp: float = 0
CACHE_TTL = 300  # 5 minutes

# Common stop words to exclude from keyword matching
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "what", "how", "why",
    "do", "does", "did", "my", "i", "it", "this", "that", "for", "on",
    "in", "to", "of", "and", "or", "with", "can", "you", "your", "me",
    "should", "would", "could", "will", "be", "have", "has", "had",
    "not", "no", "don't", "doesn't", "didn", "t", "s",
})


async def _refresh_corrections_cache():
    """Fetch all reviewed corrections from Supabase."""
    global _corrections_cache, _cache_timestamp

    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/feedback",
                headers={
                    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "rating": "eq.negative",
                    "correction": "not.is.null",
                    "select": "question,answer,correction,feedback_text",
                    "order": "created_at.desc",
                    "limit": "50",
                },
            )
            resp.raise_for_status()
            _corrections_cache = resp.json()
            _cache_timestamp = time.time()
            logger.info(f"[feedback-learn] Refreshed corrections cache: {len(_corrections_cache)} entries")
    except Exception as e:
        logger.warning(f"[feedback-learn] Cache refresh failed: {e}")


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text, excluding stop words."""
    words = set(text.lower().split())
    return words - _STOP_WORDS


async def get_feedback_context(question: str) -> str | None:
    """
    Check if the current question matches any known corrections.
    Returns a system prompt prefix string, or None.

    Uses keyword overlap for fast matching — no embedding/API call needed.
    Called on every chat request, must be fast.
    """
    global _cache_timestamp

    # Refresh cache if stale
    if time.time() - _cache_timestamp > CACHE_TTL:
        try:
            await asyncio.wait_for(_refresh_corrections_cache(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.debug("[feedback-learn] Cache refresh timed out")

    if not _corrections_cache:
        return None

    question_keywords = _extract_keywords(question)
    if len(question_keywords) < 2:
        return None

    matches = []
    for correction in _corrections_cache:
        cached_keywords = _extract_keywords(correction.get("question", ""))
        overlap = len(question_keywords & cached_keywords)
        if overlap >= 2:  # At least 2 meaningful keyword overlap
            matches.append((overlap, correction))

    if not matches:
        return None

    # Sort by overlap score descending, take top 3
    matches.sort(key=lambda x: x[0], reverse=True)

    lines = [
        "## Known Corrections (from verified feedback)\n"
        "Previous responses on similar topics were marked incorrect. Use these corrections:\n"
    ]
    for _, m in matches[:3]:
        correction_text = m.get("correction") or m.get("feedback_text", "")
        if correction_text:
            lines.append(
                f"- Q: \"{m['question'][:100]}\" — Previous answer was wrong. "
                f"Correction: {correction_text[:300]}"
            )

    return "\n".join(lines) if len(lines) > 1 else None


# ---------------------------------------------------------------------------
# Background task: process negative feedback into learning signals
# ---------------------------------------------------------------------------

async def process_negative_feedback(
    feedback_id: str,
    user_id: str,
    question: str,
    answer: str,
    feedback_text: str | None = None,
) -> None:
    """
    Fire-and-forget background task triggered when a user gives thumbs-down.

    Stores the correction as a Mem0 memory so the AI remembers what it
    got wrong for this specific user. Next time they ask a similar question,
    retrieve_memories() will surface the correction automatically.
    """
    if not feedback_text:
        # No comment = just a thumbs down, nothing actionable for Mem0
        logger.info(f"[feedback-learn] Negative feedback {feedback_id} — no comment, skipping Mem0")
        return

    try:
        from app.services.memory import store_memory

        # Frame the correction as a conversation so Mem0 extracts the right facts
        messages = [
            {"role": "user", "content": f"I asked: {question[:500]}"},
            {"role": "assistant", "content": answer[:500]},
            {"role": "user", "content": f"That answer was wrong. {feedback_text[:500]}"},
        ]

        await store_memory(user_id, messages)
        logger.info(f"[feedback-learn] Stored correction memory for user {user_id[:8]}… (feedback {feedback_id})")

    except Exception as e:
        logger.warning(f"[feedback-learn] Mem0 correction storage failed: {e}")
