"""
Arrival AI — LiveKit Voice Agent

Full-duplex voice agent for trade workers. Replaces the hand-rolled
WebSocket streaming pipeline with LiveKit's production-grade infrastructure.

Pipeline:
  - Deepgram Nova-2 STT (server-side VAD, works next to compressors)
  - Claude Sonnet LLM (50-year veteran trade expert)
  - ElevenLabs Flash v2.5 TTS (<300ms to first audio)
  - LiveKit WebRTC transport (full-duplex, <1s end-to-end)
  - MultilingualModel turn detection (semantic, not silence-based)

Run:
  python -m livekit_agent.agent start

Requires env vars:
  LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
  ANTHROPIC_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY
"""

import json
import logging
import os
import sys

# Add backend root to path so we can import from app.services
_backend_root = os.path.join(os.path.dirname(__file__), "..")
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from livekit.agents import (
    Agent,
    AgentSession,
    AgentServer,
    JobContext,
    RunContext,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, anthropic, elevenlabs, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from app import config
from app.services.error_codes import lookup_error_code

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice prompt prefix — makes Claude sound like a real person on a job site
# ---------------------------------------------------------------------------
VOICE_PROMPT_PREFIX = """You are in a LIVE VOICE CONVERSATION with a trade worker on a job site.
They may have earbuds in and be holding tools. Keep it conversational and fast.

VOICE RULES:
- 2-4 sentences MAX per response. They're working, not reading.
- Use contractions ALWAYS: "don't", "it's", "that's", "you're", "gonna"
- Use natural verbal signposts: "first thing", "here's the deal", "so basically", "9 times out of 10"
- Lead with the answer. Don't set up, don't preamble.
- If they ask something you have a tool for (error codes, docs, memory), USE THE TOOL first.
- Sound like an experienced buddy, not a manual.
- NEVER say "as an AI" or "I don't have the ability" — you're their 50-year vet buddy.
- If you don't know something specific, just say "I'm not sure on that one" like a real person would.
- Don't end with "let me know if you need anything else" — just stop talking.
"""


# ---------------------------------------------------------------------------
# Function Tools — give the agent access to Arrival's knowledge base
# ---------------------------------------------------------------------------

@function_tool()
async def lookup_error_code_tool(
    context: RunContext,
    query: str,
) -> str:
    """Look up an error code, blink code, or fault code for any HVAC, plumbing, or electrical equipment.
    Call this whenever the user mentions an error code, blink code, fault code, or status light pattern.
    Examples: 'Rheem furnace 3 blinks', 'Carrier error 31', 'Rinnai code 11', 'Daikin U4'."""
    try:
        result = lookup_error_code(query)
        if result:
            brand = result.get("brand", "")
            code = result.get("code", "")
            meaning = result.get("meaning", "")
            causes = result.get("causes", [])
            action = result.get("action", "")

            response = f"VERIFIED ERROR CODE DATA for {brand} code {code}:\n"
            response += f"Meaning: {meaning}\n"
            if causes:
                response += "Causes (ranked by field frequency):\n"
                for i, cause in enumerate(causes, 1):
                    response += f"  {i}. {cause}\n"
            if action:
                response += f"Action: {action}\n"
            response += "\nUse this EXACT data in your spoken response. Do NOT substitute your own interpretation."
            return response
        else:
            return (
                f"No verified error code found for '{query}'. "
                "Answer from your expert knowledge but mention you'd want to double-check "
                "that specific code — ask them to read the diagnostic chart on the unit door."
            )
    except Exception as e:
        logger.error(f"Error code lookup failed: {e}")
        return "Error code lookup temporarily unavailable. Answer from your expert knowledge."


@function_tool()
async def search_documents_tool(
    context: RunContext,
    query: str,
) -> str:
    """Search the user's uploaded technical documents, manuals, and specs for relevant information.
    Call this when they ask about specific equipment specs, installation procedures,
    or reference documentation they've uploaded."""
    try:
        from app.services.rag import retrieve_context

        user_id = "unknown"
        if context.userdata and isinstance(context.userdata, dict):
            user_id = context.userdata.get("user_id", "unknown")

        results = await retrieve_context(
            user_id=user_id,
            query=query,
            team_id=None,
        )
        if results:
            text = ""
            for r in results[:3]:
                text += f"\nFrom {r['filename']} (relevance: {r['score']:.0%}):\n{r['text']}\n"
            return f"DOCUMENT SEARCH RESULTS:\n{text}\nCite the filename when you reference this info."
        else:
            return "No relevant documents found. Answer from your expert knowledge."
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return "Document search temporarily unavailable."


@function_tool()
async def recall_user_context_tool(
    context: RunContext,
    query: str,
) -> str:
    """Recall information from previous conversations with this user.
    Call this when the user references past conversations, their equipment, preferences, or ongoing projects."""
    try:
        from app.services.memory import retrieve_memories

        user_id = "unknown"
        if context.userdata and isinstance(context.userdata, dict):
            user_id = context.userdata.get("user_id", "unknown")

        memories = await retrieve_memories(
            user_id=user_id,
            query=query,
        )
        if memories:
            memory_text = "\n".join(f"- {m}" for m in memories)
            return f"USER CONTEXT FROM PREVIOUS CONVERSATIONS:\n{memory_text}\nUse this to personalize your response."
        else:
            return "No relevant memories found for this user."
    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        return "Memory retrieval temporarily unavailable."


# ---------------------------------------------------------------------------
# Agent Server & Entrypoint
# ---------------------------------------------------------------------------

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Called when a participant joins a LiveKit room that needs an agent."""
    await ctx.connect()

    # Parse room name for mode: arrival_{mode}_{userId}_{random}
    room_name = ctx.room.name or ""
    parts = room_name.split("_")
    mode = parts[1] if len(parts) >= 3 else "job"
    user_id_hint = parts[2] if len(parts) >= 3 else "unknown"

    # Try to get full user_id from the first remote participant's metadata
    user_id = user_id_hint
    for participant in ctx.room.remote_participants.values():
        if participant.metadata:
            try:
                meta = json.loads(participant.metadata)
                user_id = meta.get("user_id", user_id)
                mode = meta.get("mode", mode)
            except (json.JSONDecodeError, TypeError):
                pass
            break

    logger.info(f"[arrival-agent] Room={room_name} user={user_id} mode={mode}")

    # Build full instructions
    instructions = VOICE_PROMPT_PREFIX + "\n\n" + config.SYSTEM_PROMPT

    # Create the voice pipeline session
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2",
            language="en",
        ),
        llm=anthropic.LLM(
            model=config.ANTHROPIC_VOICE_MODEL,
            api_key=config.ANTHROPIC_API_KEY,
        ),
        tts=elevenlabs.TTS(
            voice_id=config.ELEVENLABS_JOB_VOICE_ID,
            model="eleven_flash_v2_5",
            api_key=config.ELEVENLABS_API_KEY,
        ),
        turn_detection=MultilingualModel(),
        userdata={"user_id": user_id, "mode": mode},
    )

    # Create agent with tools
    agent = Agent(
        instructions=instructions,
        tools=[
            lookup_error_code_tool,
            search_documents_tool,
            recall_user_context_tool,
        ],
        # Conservative interruption settings for noisy job sites
        allow_interruptions=True,
        min_endpointing_delay=0.5,   # Don't cut them off too fast
        max_endpointing_delay=1.5,   # But don't wait forever either
    )

    await session.start(agent=agent, room=ctx.room)

    # In default/voice mode, greet. In job mode, stay silent until they talk.
    if mode == "default":
        await session.generate_reply(
            instructions="Say a very brief greeting, like 'Hey, what's up?' — 5 words max."
        )
    # Job mode: agent is silently monitoring. Tech speaks when ready.


if __name__ == "__main__":
    cli.run_app(server)
