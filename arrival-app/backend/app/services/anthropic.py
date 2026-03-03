"""
LLM service using Anthropic Claude API with vision support.
Supports memory injection, RAG context, and Job Mode frame analysis.
Bug #16: Uses AsyncAnthropic client to avoid blocking the event loop.
"""

import json
import logging
import time
import anthropic

from app import config

logger = logging.getLogger(__name__)

# Lazy singleton — avoid re-creating the client on every request
# Bug #16: Changed from synchronous Anthropic to AsyncAnthropic
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    """Return a shared async Anthropic client, creating it on first use."""
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


async def chat_with_claude(
    message: str,
    image_base64: str | None = None,
    conversation_history: list[dict] | None = None,
    user_memories: list[str] | None = None,
    rag_context: list[dict] | None = None,
    max_tokens: int = 1024,
    system_prompt_prefix: str = "",
    model: str | None = None,
) -> dict:
    """
    Send a message (optionally with an image) to Claude and get a response.
    Injects user memories and RAG document context into the system prompt.
    Returns: { response, source, confidence }
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = _get_client()

    # Build messages array from history
    messages = []
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # Build current message content
    content_parts = []

    if image_base64:
        if image_base64.startswith("iVBOR"):
            media_type = "image/png"
        elif image_base64.startswith("UklGR"):
            media_type = "image/webp"
        elif image_base64.startswith("R0lGOD"):
            media_type = "image/gif"
        else:
            media_type = "image/jpeg"

        content_parts.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_base64,
            },
        })

    content_parts.append({"type": "text", "text": message})
    messages.append({"role": "user", "content": content_parts})

    # Build enhanced system prompt with memories + RAG context
    system_prompt = config.SYSTEM_PROMPT

    if system_prompt_prefix:
        system_prompt = system_prompt_prefix + "\n\n" + system_prompt

    if user_memories:
        memory_block = "\n".join(f"- {m}" for m in user_memories)
        system_prompt += f"""

## User Context (from previous conversations)
{memory_block}

Use this context to personalize your response. Reference their equipment, trade, or past issues when relevant."""

    if rag_context:
        context_block = ""
        for ctx in rag_context:
            score_pct = f"{ctx['score']:.0%}" if ctx.get('score') else ""
            context_block += f"\n### From: {ctx['filename']}"
            if score_pct:
                context_block += f" (relevance: {score_pct})"
            context_block += f"\n{ctx['text']}\n"
        system_prompt += f"""

## Relevant Documents
The following excerpts are from the user's uploaded documents. Reference them when answering.
{context_block}
When you use information from these documents, cite the filename as your source."""

    # Bug #16: Use await with the async client
    use_model = model or config.ANTHROPIC_MODEL
    t0 = time.monotonic()
    response = await client.messages.create(
        model=use_model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    elapsed = time.monotonic() - t0

    if not response.content:
        raise ValueError("Empty AI response")

    resp_text = response.content[0].text
    logger.info(
        f"[claude] {use_model} max_tokens={max_tokens} "
        f"→ {len(resp_text)} chars in {elapsed:.2f}s "
        f"(input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens})"
    )

    # Determine source attribution
    source = "Claude AI Analysis"
    if rag_context:
        filenames = list(set(ctx["filename"] for ctx in rag_context))
        source = f"Claude AI + {', '.join(filenames[:2])}"
        if len(filenames) > 2:
            source += f" (+{len(filenames) - 2} more)"

    # Confidence scoring based on evidence quality
    confidence = _score_confidence(rag_context, user_memories, resp_text)

    return {
        "response": resp_text,
        "source": source,
        "confidence": confidence,
    }


def _score_confidence(
    rag_context: list[dict] | None,
    user_memories: list[str] | None,
    response_text: str,
) -> str:
    """
    Score confidence based on evidence quality rather than always returning "high".

    Scoring:
    - "high": Strong RAG matches (score > 0.5) OR error code lookup hit OR
              response covers a topic well-covered by the system prompt (common trade knowledge)
    - "medium": Some RAG matches (score 0.3-0.5) OR user memories but no doc match
    - "low": No supporting evidence from any source

    Note: For questions well within the system prompt's knowledge (wire sizing,
    refrigerant specs, common diagnostic patterns), Claude's built-in knowledge
    combined with our expert prompt is high confidence even without RAG.
    """
    # High confidence indicators
    if rag_context:
        top_score = max(ctx.get("score", 0) for ctx in rag_context)
        if top_score > 0.5:
            return "high"
        if top_score > 0.3 and len(rag_context) >= 2:
            return "high"  # Multiple moderate matches = good coverage

    # Check for hedging language in the response — Claude signals uncertainty
    hedging_phrases = [
        "i'm not sure",
        "i don't have specific",
        "i'm not certain",
        "without more information",
        "hard to say",
        "could be several",
        "difficult to determine",
        "you'd need to check",
    ]
    response_lower = response_text.lower()
    has_hedging = any(phrase in response_lower for phrase in hedging_phrases)

    if has_hedging:
        return "low" if not rag_context else "medium"

    # If we have some RAG context but lower scores
    if rag_context:
        return "medium"

    # If we have user memories but no RAG
    if user_memories:
        return "medium"

    # No evidence at all — rely on system prompt knowledge (still decent for common trade questions)
    # The expert system prompt has extensive trade knowledge, so pure-Claude answers
    # on common topics are actually medium confidence, not low
    return "medium"


async def analyze_frame(image_base64: str, job_context: dict | None = None, previous_alerts: list[str] | None = None) -> dict:
    """
    Analyze a camera frame for Job Mode.
    Returns { alert: bool, message: str|None, severity: str|None }
    Claude only responds substantively if something notable is detected.
    Accepts optional job_context with equipment_type, brand, model.
    Accepts optional previous_alerts for session memory (avoids repeating observations).
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set.")

    client = _get_client()

    # Build job context line if equipment is set
    job_context_line = ""
    if job_context:
        parts = []
        if job_context.get("equipment_type"):
            parts.append(job_context["equipment_type"])
        if job_context.get("brand"):
            parts.append(job_context["brand"])
        if job_context.get("model"):
            parts.append(f"model {job_context['model']}")
        if parts:
            job_context_line = f"\nThe tech is currently working on: {', '.join(parts)}. Keep observations relevant to this equipment.\n"

    # Build session memory block from previous alerts
    session_memory_line = ""
    if previous_alerts:
        alert_bullets = "\n".join(f"- \"{a}\"" for a in previous_alerts[-5:])
        session_memory_line = f"""
WHAT YOU'VE ALREADY SAID THIS SESSION:
{alert_bullets}

Do NOT repeat these observations. If you see the same thing, say OK.
If the issue has changed or gotten worse since you last mentioned it, point that out instead.
Be concise — the tech already has context from your earlier observations.
"""

    analysis_prompt = f"""You are an experienced trade veteran watching over a tech's shoulder through their phone camera. You're calm, helpful, and only speak up when it matters. Think of yourself as a knowledgeable coworker — not an alarm system.
{job_context_line}{session_memory_line}
RESPOND "OK" UNLESS you see something a veteran would actually point out to a coworker. That means:
1. You can clearly see and identify what you're looking at (not guessing from blur or shadows)
2. It's something genuinely worth mentioning — a safety issue, a common mistake, something they might miss, or something that could save them time
3. You're confident in what you see — if you're squinting at it, say OK

THINGS WORTH SPEAKING UP ABOUT:
- Safety hazards: exposed live wires, active leaks, gas flame where it shouldn't be, no lockout/tagout
- Common mistakes: wrong wire gauge visible, missing connector, backwards installation, missing support
- Useful observations: "that capacitor looks swollen", "I can see corrosion on those fittings", "that filter is pretty loaded"
- Things they might not have noticed: a second issue nearby, something in the background

ALWAYS SAY "OK" FOR:
- Normal-looking equipment, pipes, wiring, panels (don't narrate the obvious)
- Cosmetic stuff — peeling paint, wallpaper, stains, discoloration, scratches, dents
- Things that MIGHT be an issue but could just as easily be normal wear, shadows, or camera artifacts
- Anything you'd need to touch, smell, or measure to actually confirm
- Dark, blurry, or unclear images — if you can't see it clearly, don't guess
- The same thing you already mentioned (don't repeat yourself)

If you do speak up, respond with a JSON object. Talk like a coworker, not an alarm:
{{"severity": "warning", "message": "Hey, heads up — [what you actually see, described plainly]"}}

TONE EXAMPLES:
- "Hey, that capacitor looks like it's bulging on top — might want to swap it while you're in there."
- "Heads up, I can see some green buildup on those copper fittings."
- "That filter looks pretty clogged — could be your airflow issue right there."
- "Just so you know, that wire nut doesn't look like it's fully seated."

NEVER DO THIS:
- "WARNING: Potential water damage detected on ceiling surface" (too robotic, too diagnostic)
- "ALERT: I notice discoloration that could indicate mold growth" (too alarmist, guessing)
- "I can see what appears to be deterioration consistent with moisture intrusion" (textbook nonsense)

CRITICAL RULES:
- Describe what you SEE, not what you think caused it. "I see brown staining" not "water damage."
- State the surface: wall, ceiling, floor, unit, pipe, panel. Get the basics right.
- NEVER guess what's behind a wall, above a ceiling, or outside the frame.
- Use "critical" severity ONLY for immediate danger to life (sparking, active fire, gas ignition).
- When in doubt, say OK. A false alarm is more annoying than a missed observation."""

    if image_base64.startswith("iVBOR"):
        media_type = "image/png"
    elif image_base64.startswith("UklGR"):
        media_type = "image/webp"
    elif image_base64.startswith("R0lGOD"):
        media_type = "image/gif"
    else:
        media_type = "image/jpeg"

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_base64,
                },
            },
            {"type": "text", "text": "Analyze this job site frame."},
        ],
    }]

    # Bug #16: Use await with the async client
    response = await client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=256,
        system=analysis_prompt,
        messages=messages,
    )

    if not response.content:
        raise ValueError("Empty AI response")

    text = response.content[0].text.strip()

    # "OK" means nothing notable
    if text == "OK" or text.lower().startswith("ok"):
        return {"alert": False, "message": None, "severity": None}

    # Try to parse JSON response
    try:
        data = json.loads(text)
        return {
            "alert": True,
            "message": data.get("message", text),
            "severity": data.get("severity", "warning"),
        }
    except json.JSONDecodeError:
        # Claude responded with plain text instead of JSON — treat as warning
        return {
            "alert": True,
            "message": text,
            "severity": "warning",
        }
