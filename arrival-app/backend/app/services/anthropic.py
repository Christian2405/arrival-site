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


async def analyze_frame(image_base64: str) -> dict:
    """
    Analyze a camera frame for Job Mode.
    Returns { alert: bool, message: str|None, severity: str|None }
    Claude only responds substantively if something notable is detected.
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set.")

    client = _get_client()

    analysis_prompt = """You are a passive observer on a trade worker's phone camera. Your job is ONLY to flag genuine, clear safety hazards.

RESPOND "OK" UNLESS ALL THREE CONDITIONS ARE MET:
1. You can clearly see and identify the specific object or condition (not guessing)
2. It is an immediate safety hazard (active leak, exposed live wires, gas flame where it shouldn't be, structural collapse risk)
3. You are highly confident — if you're even slightly unsure, say OK

ALWAYS RESPOND "OK" FOR:
- Cosmetic damage (peeling paint, wallpaper, stains, discoloration, scratches, dents)
- Things that MIGHT be damage but could also be normal wear, shadows, or camera artifacts
- Anything you'd need to touch, smell, or measure to confirm
- Conditions that aren't an immediate danger, even if they need repair eventually
- Dark, blurry, or unclear images
- Anything you can't identify with certainty

Respond with exactly: OK

ONLY if you see a clear, unmistakable, immediate hazard, respond with a JSON object:
{"severity": "warning", "message": "Hey, [describe ONLY what you can actually see — not what you think it might mean]"}

CRITICAL RULES:
- NEVER guess what's behind a wall, above a ceiling, or outside the frame
- NEVER diagnose from a single image — describe what you see, not what you think caused it
- NEVER say "water damage", "mold", "structural issue" unless it's unmistakable and severe
- Use "critical" ONLY for immediate danger to life (sparking wires, active fire, gas ignition)
- When in doubt, ALWAYS say OK. A missed cosmetic issue is fine. A false alarm is annoying."""

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
