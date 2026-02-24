"""
LLM service using Anthropic Claude API with vision support.
"""

import anthropic

from app import config


async def chat_with_claude(
    message: str,
    image_base64: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Send a message (optionally with an image) to Claude and get a response.
    Returns: { response, source, confidence }
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

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

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=config.SYSTEM_PROMPT,
        messages=messages,
    )

    return {
        "response": response.content[0].text,
        "source": "Claude AI Analysis",
        "confidence": "high",
    }
