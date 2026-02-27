"""
LLM service using Anthropic Claude API with vision support.
Supports memory injection, RAG context, and Job Mode frame analysis.
Bug #16: Uses AsyncAnthropic client to avoid blocking the event loop.
"""

import json
import anthropic

from app import config

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
        media_type = "image/jpeg"
        if image_base64.startswith("iVBOR"):
            media_type = "image/png"

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
    response = await client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    if not response.content:
        raise ValueError("Empty AI response")

    # Determine source attribution
    source = "Claude AI Analysis"
    if rag_context:
        filenames = list(set(ctx["filename"] for ctx in rag_context))
        source = f"Claude AI + {', '.join(filenames[:2])}"
        if len(filenames) > 2:
            source += f" (+{len(filenames) - 2} more)"

    return {
        "response": response.content[0].text,
        "source": source,
        "confidence": "high",
    }


async def analyze_frame(image_base64: str) -> dict:
    """
    Analyze a camera frame for Job Mode.
    Returns { alert: bool, message: str|None, severity: str|None }
    Claude only responds substantively if something notable is detected.
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set.")

    client = _get_client()

    analysis_prompt = """You are a job site safety and quality monitor for trade workers.

Analyze this camera frame from a trade worker's job site. ONLY respond if you see something notable:
- Safety hazard (exposed wires, missing PPE, water near electrical, gas leak indicators)
- Incorrect installation (wrong fittings, reversed polarity, improper support)
- Visible damage or wear that needs attention
- Code violation visible in the frame
- Equipment issue the worker might not have noticed

If you see NOTHING notable or the image is unclear/dark/blurry, respond with exactly: OK

If you DO see something notable, respond with a JSON object:
{"severity": "warning", "message": "Brief, actionable alert (1-2 sentences)"}

Use "warning" for general notices, "critical" for safety hazards.
Be concise — the worker is on a job site and will hear this via text-to-speech."""

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
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
