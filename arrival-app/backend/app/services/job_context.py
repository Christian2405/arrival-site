"""
Job Mode equipment context — simple in-memory session store.
When a tech enters Job Mode, they can set what equipment they're working on.
This context is injected into voice chat prompts for more relevant responses.

TTL: Context expires after 8 hours of inactivity (a work day).
"""

import time
import logging

logger = logging.getLogger(__name__)

# In-memory context store: user_id -> { equipment_type, brand, model, set_at }
_job_contexts: dict[str, dict] = {}

# 8-hour TTL — a full work shift
JOB_CONTEXT_TTL = 8 * 60 * 60  # seconds

# Valid equipment types
EQUIPMENT_TYPES = [
    "furnace",
    "air_conditioner",
    "heat_pump",
    "water_heater",
    "tankless",
    "mini_split",
    "electrical_panel",
    "boiler",
    "plumbing",
    "other",
]

# Common brands (for quick-select in frontend)
COMMON_BRANDS = [
    "Carrier", "Bryant", "Trane", "American Standard",
    "Lennox", "Rheem", "Ruud", "Goodman", "Amana",
    "York", "Coleman", "Heil", "Tempstar",
    "Daikin", "Mitsubishi", "Fujitsu", "LG",
    "Rinnai", "Navien", "Noritz", "Takagi",
    "AO Smith", "Bradford White", "State",
    "Square D", "Eaton", "Siemens", "GE",
]


def set_job_context(
    user_id: str,
    equipment_type: str,
    brand: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Set the equipment context for a user's job mode session.
    Returns the stored context.
    """
    ctx = {
        "equipment_type": equipment_type,
        "brand": brand,
        "model": model,
        "set_at": time.time(),
    }
    _job_contexts[user_id] = ctx
    logger.info(f"[job-context] Set for {user_id[:8]}…: {equipment_type} {brand or ''} {model or ''}")

    # Prune expired contexts periodically
    _prune_expired()

    return ctx


def get_job_context(user_id: str) -> dict | None:
    """
    Get the current equipment context for a user.
    Returns None if no context set or context has expired.
    """
    ctx = _job_contexts.get(user_id)
    if not ctx:
        return None

    # Check TTL
    if time.time() - ctx["set_at"] > JOB_CONTEXT_TTL:
        del _job_contexts[user_id]
        return None

    return ctx


def clear_job_context(user_id: str) -> bool:
    """Clear the equipment context for a user. Returns True if there was context to clear."""
    if user_id in _job_contexts:
        del _job_contexts[user_id]
        logger.info(f"[job-context] Cleared for {user_id[:8]}…")
        return True
    return False


def format_job_context_prompt(ctx: dict) -> str:
    """
    Format the job context as a prompt prefix for Claude.
    Injected before the voice chat prompt.
    """
    parts = []
    equip_display = ctx["equipment_type"].replace("_", " ")
    parts.append(f"The tech is currently working on a {equip_display}")
    if ctx.get("brand"):
        parts[-1] = f"The tech is currently working on a {ctx['brand']} {equip_display}"
    if ctx.get("model"):
        parts[-1] += f" (model: {ctx['model']})"
    parts.append("Keep answers specific to this equipment.")
    parts.append("If they ask about something else, still answer but relate back to the job when relevant.")
    return " ".join(parts)


def _prune_expired():
    """Remove expired contexts to prevent unbounded memory growth."""
    now = time.time()
    expired = [uid for uid, ctx in _job_contexts.items()
               if now - ctx["set_at"] > JOB_CONTEXT_TTL]
    for uid in expired:
        del _job_contexts[uid]
    if expired:
        logger.debug(f"[job-context] Pruned {len(expired)} expired contexts")
