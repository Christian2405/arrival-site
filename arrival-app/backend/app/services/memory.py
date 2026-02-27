"""
Memory service — persistent user memory via Mem0 Platform.
Retrieves relevant memories before chat, stores new facts after.
Gracefully degrades if MEM0_API_KEY is not set.

Performance: Mem0 API can be extremely slow (10-15s observed).
retrieve_memories() has a hard 3-second timeout — returns empty on timeout
rather than blocking the entire chat pipeline.
"""

import asyncio
import logging
import time

from app import config

logger = logging.getLogger(__name__)

# Hard timeout for memory retrieval — Mem0 can take 15+ seconds.
# Better to skip memories than make the user wait.
RETRIEVE_TIMEOUT = 3.0  # seconds

_client = None


def _get_client():
    """Lazy-init the Mem0 client. Returns None if no API key."""
    global _client
    if _client is None:
        if not config.MEM0_API_KEY:
            return None
        try:
            from mem0 import MemoryClient
            _client = MemoryClient(api_key=config.MEM0_API_KEY)
        except Exception as e:
            logger.error(f"[memory] Failed to initialize Mem0 client: {e}")
            return None
    return _client


async def retrieve_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    """
    Retrieve relevant memories for this user given the current query.
    Returns a list of memory strings, or empty list on failure/timeout.
    Hard timeout of 3 seconds — returns empty rather than blocking chat.
    """
    client = _get_client()
    if not client:
        return []

    try:
        t0 = time.monotonic()
        # Wrap in timeout so Mem0 can't block the pipeline
        results = await asyncio.wait_for(
            asyncio.to_thread(
                client.search, query=query, user_id=user_id, limit=limit
            ),
            timeout=RETRIEVE_TIMEOUT,
        )
        # mem0 returns list of dicts with 'memory' key
        memories = []
        if isinstance(results, list):
            for r in results:
                mem = r.get("memory", "") if isinstance(r, dict) else ""
                if mem:
                    memories.append(mem)
        elapsed = time.monotonic() - t0
        logger.info(f"[memory] Retrieved {len(memories)} memories in {elapsed:.2f}s")
        return memories
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - t0
        logger.warning(f"[memory] Retrieve TIMED OUT after {elapsed:.2f}s (limit={RETRIEVE_TIMEOUT}s) — skipping memories")
        return []
    except Exception as e:
        logger.warning(f"[memory] Retrieve error: {e}")
        return []


async def store_memory(user_id: str, messages: list[dict]) -> None:
    """
    Store new facts from the conversation exchange.
    Mem0 auto-extracts meaningful facts from the messages.
    This is fire-and-forget — errors are logged but not raised.
    No timeout since this runs in the background (not blocking the response).
    """
    client = _get_client()
    if not client:
        return

    try:
        t0 = time.monotonic()
        await asyncio.to_thread(client.add, messages=messages, user_id=user_id)
        logger.info(f"[memory] Stored memory in {time.monotonic()-t0:.2f}s")
    except Exception as e:
        logger.warning(f"[memory] Store error: {e}")
