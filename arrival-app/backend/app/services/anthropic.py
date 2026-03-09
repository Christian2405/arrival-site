"""
LLM service using Anthropic Claude API with vision support.
Supports memory injection, RAG context, and Job Mode frame analysis.
Bug #16: Uses AsyncAnthropic client to avoid blocking the event loop.
"""

import json
import logging
import time
from typing import AsyncGenerator
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

    # Confidence-aware tone guidance
    # Pre-score evidence quality to shape Claude's tone
    _evidence_strength = "none"
    if rag_context:
        _top = max(ctx.get("score", 0) for ctx in rag_context)
        if _top > 0.5 or (_top > 0.3 and len(rag_context) >= 2):
            _evidence_strength = "strong"
        else:
            _evidence_strength = "weak"

    if _evidence_strength == "strong":
        system_prompt += "\n\nYou have strong documentation backing this answer. Be direct and authoritative."
    elif _evidence_strength == "weak":
        system_prompt += "\n\nYour documentation matches are weak for this question. Prefix your answer with a brief hedge like 'I think' or 'You might want to verify, but...' — be honest about your certainty without being overly cautious. Never say the word 'confidence' or mention percentages."
    elif _evidence_strength == "none" and not user_memories:
        system_prompt += "\n\nYou're answering from general trade knowledge without documentation. If the question is specific to a model or procedure, briefly note you're going from general experience, not their docs."

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
        "rag_chunks_used": [
            {"id": ctx.get("filename", ""), "score": round(ctx.get("score", 0), 3)}
            for ctx in (rag_context or [])
        ],
    }


async def stream_chat_with_claude(
    message: str,
    image_base64: str | None = None,
    conversation_history: list[dict] | None = None,
    user_memories: list[str] | None = None,
    rag_context: list[dict] | None = None,
    max_tokens: int = 1024,
    system_prompt_prefix: str = "",
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Streaming version of chat_with_claude.
    Yields text delta strings as they arrive from Claude.
    Same prompt construction logic as chat_with_claude.
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = _get_client()

    # Build messages array from history (same as chat_with_claude)
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

    # Build enhanced system prompt (same as chat_with_claude)
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

    # Confidence-aware tone guidance (same logic as chat_with_claude)
    _evidence_strength = "none"
    if rag_context:
        _top = max(ctx.get("score", 0) for ctx in rag_context)
        if _top > 0.5 or (_top > 0.3 and len(rag_context) >= 2):
            _evidence_strength = "strong"
        else:
            _evidence_strength = "weak"

    if _evidence_strength == "strong":
        system_prompt += "\n\nYou have strong documentation backing this answer. Be direct and authoritative."
    elif _evidence_strength == "weak":
        system_prompt += "\n\nYour documentation matches are weak for this question. Prefix your answer with a brief hedge like 'I think' or 'You might want to verify, but...' — be honest about your certainty without being overly cautious. Never say the word 'confidence' or mention percentages."
    elif _evidence_strength == "none" and not user_memories:
        system_prompt += "\n\nYou're answering from general trade knowledge without documentation. If the question is specific to a model or procedure, briefly note you're going from general experience, not their docs."

    use_model = model or config.ANTHROPIC_MODEL
    t0 = time.monotonic()
    total_chars = 0

    async with client.messages.stream(
        model=use_model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            total_chars += len(text)
            yield text

    elapsed = time.monotonic() - t0
    logger.info(
        f"[claude-stream] {use_model} → {total_chars} chars in {elapsed:.2f}s"
    )


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

    analysis_prompt = f"""You're a 50-year vet glancing at a tech's phone camera. Helpful but not jumpy.
{job_context_line}{session_memory_line}
DEFAULT: say "OK" if nothing useful to mention.

SAY OK when:
- Normal rooms, walls, floors, ceilings — nothing trade-related visible
- Equipment that looks normal and operational
- Dark, blurry, or unclear images
- You already mentioned it this session

SPEAK UP when you can clearly see:
- Safety issue: exposed wiring, gas smell indicators, active leak (flowing water, not a stain)
- Damaged component: bulging cap, scorched board, cracked fitting, corroded terminal
- Useful info: readable data plate, model number, brand name the tech might want
- Dirty/worn parts: visibly clogged filter, dirty coils, worn belts
- Code violation: wrong wire gauge, missing cover, improper support

RULES:
- Be confident in what you see, hedge on what you're guessing. "That looks like..." not "There's definitely..."
- A shadow is not a leak. A stain is not active water. Don't diagnose from ambiguous phone photos.
- ONE observation per frame, ONE sentence, under 15 words.
- If the tech is just walking around or pointing at normal stuff, say OK.

FORMAT — JSON:
{{"severity": "warning", "message": "Coils look pretty caked up — when's the last time those were cleaned?"}}

"critical" = immediate danger to life ONLY. Everything else = "warning"."""

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
        model=config.ANTHROPIC_VOICE_MODEL,
        max_tokens=300,
        system=analysis_prompt,
        messages=messages,
    )

    if not response.content:
        raise ValueError("Empty AI response")

    text = response.content[0].text.strip()

    # "OK" or any variation means nothing notable
    text_lower = text.lower().strip('"\'., ')
    if (
        text_lower.startswith("ok")
        or text_lower.startswith("nothing")
        or text_lower.startswith("everything look")
        or text_lower.startswith("all good")
        or text_lower.startswith("looks normal")
        or text_lower.startswith("no issues")
        or text_lower.startswith("can't see")
        or text_lower.startswith("hard to tell")
        or len(text_lower) < 5
    ):
        return {"alert": False, "message": None, "severity": None}

    # Try to parse JSON response — ONLY valid JSON triggers an alert
    try:
        data = json.loads(text)
        msg = data.get("message", "")
        # Double-check the message itself isn't an "OK" variant
        if not msg or msg.lower().strip().startswith("ok") or msg.lower().strip().startswith("nothing"):
            return {"alert": False, "message": None, "severity": None}
        return {
            "alert": True,
            "message": msg,
            "severity": data.get("severity", "warning"),
        }
    except json.JSONDecodeError:
        # Non-JSON response = model didn't follow alert format = probably nothing noteworthy.
        # Only treat as alert if it's very short (likely a direct observation, not rambling).
        if len(text) < 80 and not any(w in text_lower for w in ["ok", "nothing", "normal", "fine", "good", "clear"]):
            logger.info(f"[frame] Non-JSON alert: {text[:60]}")
            return {
                "alert": True,
                "message": text,
                "severity": "warning",
            }
        return {"alert": False, "message": None, "severity": None}
