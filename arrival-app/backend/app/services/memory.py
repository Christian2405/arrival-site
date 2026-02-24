"""
Memory service — persistent user memory via Mem0 Platform.
Retrieves relevant memories before chat, stores new facts after.
Gracefully degrades if MEM0_API_KEY is not set.
"""

from app import config

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
            print(f"[memory] Failed to initialize Mem0 client: {e}")
            return None
    return _client


async def retrieve_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    """
    Retrieve relevant memories for this user given the current query.
    Returns a list of memory strings, or empty list on failure.
    """
    client = _get_client()
    if not client:
        return []

    try:
        results = client.search(query=query, user_id=user_id, limit=limit)
        # mem0 returns list of dicts with 'memory' key
        memories = []
        if isinstance(results, list):
            for r in results:
                mem = r.get("memory", "") if isinstance(r, dict) else ""
                if mem:
                    memories.append(mem)
        return memories
    except Exception as e:
        print(f"[memory] Retrieve error: {e}")
        return []


async def store_memory(user_id: str, messages: list[dict]) -> None:
    """
    Store new facts from the conversation exchange.
    Mem0 auto-extracts meaningful facts from the messages.
    This is fire-and-forget — errors are logged but not raised.
    """
    client = _get_client()
    if not client:
        return

    try:
        client.add(messages=messages, user_id=user_id)
    except Exception as e:
        print(f"[memory] Store error: {e}")
