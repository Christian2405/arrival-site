"""
Voice WebSocket router — /ws/voice-session
Streaming voice pipeline: Deepgram Live STT → Claude Streaming → ElevenLabs Streaming TTS.
Single persistent WebSocket per session. Server-side VAD via Deepgram endpointing.
"""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app import config
from app.services.deepgram_live import DeepgramLiveSession
from app.services.elevenlabs_ws import ElevenLabsStreamSession
from app.services.anthropic import stream_chat_with_claude
from app.services.error_codes import lookup_error_code, format_error_code_context
from app.services.diagnostic_flows import lookup_diagnostic_flow, format_diagnostic_context
from app.services.job_context import get_job_context, format_job_context_prompt
from app.services.rag import retrieve_context
from app.services.supabase import get_user_team_id, log_query
from app.services.usage import check_query_limit
from app.middleware.auth import decode_jwt_token

logger = logging.getLogger(__name__)

router = APIRouter()

# Visual keywords — strip image if none present (same as voice_chat.py)
_VISUAL_KEYWORDS = {
    "see", "look", "show", "camera", "picture", "photo", "image",
    "what's this", "what is this", "what's that", "what is that",
    "this look", "that look", "what do you", "point", "pointing",
    "check this", "check that", "wrong here", "wrong with",
    "identify", "read this", "read that", "model number",
    "what brand", "what model",
}

# Sentence boundary pattern for TTS chunking
_SENTENCE_BOUNDARY = re.compile(r'[.!?;:—]\s')
_MIN_CHUNK_SIZE = 20  # Don't flush tiny fragments to TTS


def _wants_visual(transcript: str) -> bool:
    """Check if transcript contains visual keywords."""
    lower = transcript.lower()
    return any(kw in lower for kw in _VISUAL_KEYWORDS)


def _strip_wav_header(data: bytes) -> bytes:
    """
    Strip WAV/RIFF header from audio data to get raw PCM bytes.
    The frontend sends complete WAV files (expo-av records to .wav),
    but Deepgram expects raw linear16 PCM when encoding=linear16.
    """
    if len(data) < 44:
        return data
    # Look for the "data" chunk marker — PCM samples start right after it + 4-byte size
    pos = data.find(b'data')
    if pos >= 0 and pos + 8 <= len(data):
        return data[pos + 8:]
    # Fallback: if it starts with RIFF header, skip standard 44-byte header
    if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        return data[44:]
    # Not a WAV file — return as-is (already raw PCM)
    return data


def _split_at_boundary(text: str) -> tuple[str, str]:
    """Split text at the last sentence boundary. Returns (to_send, remainder)."""
    # Find the last sentence boundary
    matches = list(_SENTENCE_BOUNDARY.finditer(text))
    if not matches:
        return text, ""
    last_match = matches[-1]
    split_pos = last_match.end()
    return text[:split_pos], text[split_pos:]


class VoiceSession:
    """Per-session state for a streaming voice WebSocket."""

    def __init__(
        self,
        websocket: WebSocket,
        user_id: str,
        mode: Literal["default", "job"],
    ):
        self.ws = websocket
        self.user_id = user_id
        self.mode = mode
        self.conversation_history: list[dict] = []
        self.current_image: str | None = None
        self.generation = 0  # Incremented on interrupt to cancel stale pipelines
        self.deepgram: DeepgramLiveSession | None = None
        self.pipeline_task: asyncio.Task | None = None
        self._t0 = time.monotonic()

    async def send_json(self, data: dict) -> None:
        """Send a JSON event to the client."""
        try:
            await self.ws.send_json(data)
        except Exception:
            pass  # Client may have disconnected

    async def send_audio_chunk(self, mp3_bytes: bytes) -> None:
        """Send MP3 audio as base64 JSON (React Native can't reliably receive binary frames)."""
        try:
            await self.ws.send_json({
                "type": "audio_chunk",
                "data": base64.b64encode(mp3_bytes).decode("ascii"),
            })
        except Exception:
            pass


def _build_voice_prompt(
    mode: str,
    user_id: str,
    error_code_context: str,
    diagnostic_context: str,
) -> tuple[str, int, str | None, dict | None]:
    """
    Build the voice prompt prefix, max_tokens, voice_id, and voice_settings.
    Extracted from voice_chat.py to share between REST and WS endpoints.
    Returns: (prompt_prefix, max_tokens, voice_id, voice_settings)
    """
    if mode == "job":
        job_ctx = get_job_context(user_id)
        job_context_prompt = format_job_context_prompt(job_ctx) + "\n\n" if job_ctx else ""

        voice_prompt_prefix = (
            job_context_prompt
            + "You're a 50-year vet working alongside a tech on a job. You're their buddy — "
            "you talk about anything, answer anything. Short, confident, natural. "
            "1-3 sentences max. This is spoken aloud — don't drone on.\n\n"
            "RULES:\n"
            "- Answer what they asked, nothing extra. Simple question = simple answer.\n"
            "- Lead with the most likely cause. Don't list 5 things.\n"
            "- If they ask about a specific error code or blink code and you don't have verified data for it, "
            "say 'I don't have that code memorized — what does the chart on the unit show?' NEVER guess error codes.\n"
            "- If they ask something non-trade (weather, sports, lunch), just chat naturally. You're a person, not a manual.\n"
            "- If you tell them to check something, ask what they find.\n"
            "- If they confirm ('yeah I see it'), give the next step.\n"
            "- If they say 'it's fine' or 'no' or push back, DROP IT IMMEDIATELY. Say 'Fair enough' or 'Got it' and move on.\n"
            "- If they challenge something you said ('what are you talking about', 'there's no leak', 'that's wrong'), "
            "IMMEDIATELY back off. Say 'My bad' or 'Alright, scratch that'. NEVER double down. NEVER insist.\n"
            "- NEVER make something up. If you're not sure, say so. A wrong answer wastes the tech's time.\n"
            "- No filler: no 'Great question', no 'Let me know if you need anything'.\n"
            "- If image attached and they asked about it, reference it. Otherwise ignore it completely.\n\n"
            "EXAMPLES:\n"
            "Q: 'Superheat target on a TXV?' → 'Subcooling, not superheat — 10 to 12 degrees. What are you reading?'\n"
            "Q: 'Carrier keeps short cycling' → 'Flame sensor. Pull it, emery cloth, fixes it 80% of the time.'\n"
            "Q: 'What size wire for 40 amps?' → '8 gauge copper. Over 50 feet, bump to 6.'\n"
            "Q: 'Yeah I see the corrosion' → 'Emery cloth and NoOx. Want me to walk you through it?'\n"
            "Q: 'There's no leak here' → 'My bad, must have misread that. What are you looking at?'\n"
            "Q: 'What do you think about the Bears game?' → 'Don't get me started. What a season though.'\n"
        )
        if error_code_context:
            voice_prompt_prefix += "\n\n" + error_code_context
        elif diagnostic_context:
            voice_prompt_prefix += "\n\n" + diagnostic_context

        return (
            voice_prompt_prefix,
            150,
            config.ELEVENLABS_JOB_VOICE_ID,
            {"stability": 0.75, "similarity_boost": 0.85, "style": 0.0, "use_speaker_boost": True},
        )
    else:
        voice_prompt_prefix = (
            "Keep it to 1-3 sentences. This is spoken aloud — make it sound natural, not written.\n\n"
            "RULES:\n"
            "- Just answer the question they asked. Nothing else.\n"
            "- No 'Great question!' No 'I'd be happy to help.' No 'Let me know if you have other questions.'\n"
            "- Use contractions. Say 'you're' not 'you are', 'don't' not 'do not'.\n"
            "- Use 'probably', 'usually', 'most likely' — that's how people talk.\n"
            "- If they ask about a specific error code/blink code and you don't have verified data, "
            "say 'I don't have that code memorized — check the chart on the unit door.' NEVER guess error codes.\n"
            "- NEVER make something up. If you don't know a specific detail, say 'I'm not sure about that one.'\n"
            "- If an image is attached, ONLY describe it if the user explicitly asked about something visual. "
            "For ANY other question, COMPLETELY IGNORE the image.\n"
            "- Continue the conversation naturally. Don't repeat yourself.\n"
            "- NEVER volunteer observations about the image. NEVER say 'I can see...' unless they asked you to look.\n"
            "- If the user pushes back or says you're wrong, back off immediately. Say 'my bad' and move on.\n\n"
            "EXAMPLE RESPONSES (match this tone):\n"
            "Q: 'What causes a furnace to short cycle?'\n"
            "A: 'Usually it's a dirty flame sensor — pull it and clean it with emery cloth. If that's not it, "
            "check your filter, a clogged filter will overheat it and trip the limit switch.'\n\n"
            "Q: 'How do I check a capacitor?'\n"
            "A: 'Kill the power, discharge it, then put your meter on microfarads. Compare what you read to "
            "what's printed on the cap — if it's more than 10% off, swap it.'\n"
        )
        if error_code_context:
            voice_prompt_prefix += "\n\n" + error_code_context
        elif diagnostic_context:
            voice_prompt_prefix += "\n\n" + diagnostic_context

        return (voice_prompt_prefix, 200, None, None)


@router.websocket("/voice-session")
async def voice_session(
    websocket: WebSocket,
    token: str = Query(""),
    mode: str = Query("default"),
):
    """
    Streaming voice session WebSocket.
    Client streams audio, server streams back transcripts + audio.
    """
    # Authenticate
    try:
        payload = await decode_jwt_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception as e:
        logger.warning(f"[voice-ws] Auth failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await websocket.accept()
    logger.info(f"[voice-ws] Session started: user={user_id} mode={mode}")

    session = VoiceSession(websocket, user_id, mode)

    # Set up Deepgram callbacks
    async def on_interim(text: str):
        await session.send_json({"type": "transcript_interim", "text": text})

    async def on_final(text: str):
        pass  # We accumulate finals internally, speech_final triggers pipeline

    async def on_speech_final(transcript: str):
        """Called when Deepgram detects end of utterance. Triggers response pipeline."""
        gen = session.generation
        # Cancel any in-progress pipeline
        if session.pipeline_task and not session.pipeline_task.done():
            session.pipeline_task.cancel()
        session.pipeline_task = asyncio.create_task(
            _handle_utterance(session, transcript, gen)
        )

    async def on_dg_error(msg: str):
        await session.send_json({"type": "error", "message": f"STT error: {msg}"})

    # Connect Deepgram
    session.deepgram = DeepgramLiveSession(
        on_interim_transcript=on_interim,
        on_final_transcript=on_final,
        on_speech_final=on_speech_final,
        on_error=on_dg_error,
    )

    audio_chunk_count = 0
    audio_byte_total = 0

    try:
        await session.deepgram.connect()
        logger.info(f"[voice-ws] Deepgram connected, sending ready state")
        await session.send_json({"type": "state", "state": "ready"})

        # Main receive loop
        while True:
            try:
                msg = await websocket.receive()
            except WebSocketDisconnect:
                break

            if "bytes" in msg:
                # Binary frame = audio chunk → strip WAV header, forward raw PCM to Deepgram
                raw_pcm = _strip_wav_header(msg["bytes"])
                if raw_pcm:
                    audio_chunk_count += 1
                    audio_byte_total += len(raw_pcm)
                    if audio_chunk_count == 1:
                        logger.info(f"[voice-ws] First binary audio chunk: {len(msg['bytes'])}B raw → {len(raw_pcm)}B PCM")
                    await session.deepgram.send_audio(raw_pcm)

            elif "text" in msg:
                try:
                    data = json.loads(msg["text"])
                    event_type = data.get("type", "")

                    if event_type == "audio":
                        # JSON-encoded audio (base64) — React Native compatibility
                        audio_b64 = data.get("data", "")
                        if audio_b64:
                            audio_bytes = base64.b64decode(audio_b64)
                            raw_pcm = _strip_wav_header(audio_bytes)
                            if raw_pcm:
                                audio_chunk_count += 1
                                audio_byte_total += len(raw_pcm)
                                if audio_chunk_count == 1:
                                    logger.info(
                                        f"[voice-ws] First JSON audio chunk: {len(audio_bytes)}B wav → {len(raw_pcm)}B PCM"
                                    )
                                elif audio_chunk_count % 50 == 0:
                                    logger.info(f"[voice-ws] Audio: {audio_chunk_count} chunks, {audio_byte_total/1024:.0f}KB total")
                                await session.deepgram.send_audio(raw_pcm)

                    elif event_type == "config":
                        # Session configuration
                        session.conversation_history = data.get("conversation_history", [])
                        session.current_image = data.get("image_base64")
                        if data.get("mode"):
                            session.mode = data["mode"]
                        logger.info(
                            f"[voice-ws] Config: mode={session.mode} "
                            f"history={len(session.conversation_history)} "
                            f"has_image={bool(session.current_image)}"
                        )

                    elif event_type == "interrupt":
                        session.generation += 1
                        session.deepgram.reset_utterance()
                        if session.pipeline_task and not session.pipeline_task.done():
                            session.pipeline_task.cancel()
                        await session.send_json({"type": "interrupted"})
                        await session.send_json({"type": "state", "state": "ready"})
                        logger.info("[voice-ws] Interrupted")

                    elif event_type == "image_update":
                        session.current_image = data.get("image_base64")

                    elif event_type == "end_session":
                        logger.info("[voice-ws] Client requested session end")
                        break

                    elif event_type == "ping":
                        pass  # Heartbeat — no response needed

                except json.JSONDecodeError:
                    logger.warning(f"[voice-ws] Invalid JSON received")

    except WebSocketDisconnect:
        logger.info(f"[voice-ws] Client disconnected")
    except Exception as e:
        logger.error(f"[voice-ws] Session error: {e}", exc_info=True)
    finally:
        # Cleanup
        if session.pipeline_task and not session.pipeline_task.done():
            session.pipeline_task.cancel()
        if session.deepgram:
            await session.deepgram.close()
        elapsed = time.monotonic() - session._t0
        logger.info(f"[voice-ws] Session ended after {elapsed:.1f}s")


async def _handle_utterance(session: VoiceSession, transcript: str, gen: int) -> None:
    """
    Process a complete utterance: error code lookup → Claude streaming → ElevenLabs streaming TTS.
    Checks session.generation == gen before each step to support cancellation.
    """
    t0 = time.monotonic()

    try:
        await session.send_json({"type": "transcript_final", "text": transcript})
        await session.send_json({"type": "state", "state": "processing"})

        if session.generation != gen:
            return

        # --- Error code + diagnostic lookup (instant) ---
        error_code_result = lookup_error_code(transcript)
        error_code_context = format_error_code_context(error_code_result) if error_code_result else ""
        if error_code_result:
            logger.info(f"[voice-ws] Error code hit: {error_code_result['brand']} {error_code_result['code']}")

        diagnostic_context = ""
        if not error_code_result:
            diag_result = lookup_diagnostic_flow(transcript)
            if diag_result:
                diagnostic_context = format_diagnostic_context(diag_result)
                logger.info(f"[voice-ws] Diagnostic flow: {diag_result['title']}")

        # --- Image handling ---
        image = session.current_image if _wants_visual(transcript) else None

        # --- RAG (default mode only, speculative) ---
        rag_context = []
        if session.mode != "job":
            try:
                team_id = await get_user_team_id(session.user_id)
                rag_context = await asyncio.wait_for(
                    retrieve_context(session.user_id, transcript, team_id=team_id),
                    timeout=3.0,
                )
            except asyncio.TimeoutError:
                logger.warning("[voice-ws] RAG timeout — proceeding without")
            except Exception as e:
                logger.warning(f"[voice-ws] RAG failed: {e}")

        if session.generation != gen:
            return

        # --- Build prompt ---
        prompt_prefix, max_tokens, voice_id, voice_settings = _build_voice_prompt(
            session.mode, session.user_id, error_code_context, diagnostic_context
        )

        # --- Sanitize history (same logic as voice_chat.py) ---
        _content_limit = 500 if session.mode == "job" else 2000
        _history_limit = 6 if session.mode == "job" else 10
        safe_history = []
        for msg in session.conversation_history[-_history_limit:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                content = str(msg.get("content", ""))[:_content_limit]
                if content:
                    if safe_history and safe_history[-1]["role"] == msg["role"]:
                        safe_history[-1]["content"] += "\n" + content
                    else:
                        safe_history.append({"role": msg["role"], "content": content})

        # --- Start ElevenLabs streaming TTS ---
        audio_sent = False

        async def on_audio(mp3_bytes: bytes):
            nonlocal audio_sent
            if session.generation != gen:
                return
            if not audio_sent:
                await session.send_json({"type": "state", "state": "speaking"})
                audio_sent = True
            await session.send_audio_chunk(mp3_bytes)

        async def on_tts_done():
            if session.generation == gen:
                await session.send_json({"type": "audio_end"})
                await session.send_json({"type": "state", "state": "ready"})

        async def on_tts_error(msg: str):
            logger.error(f"[voice-ws] TTS error: {msg}")

        el_session = ElevenLabsStreamSession(
            on_audio_chunk=on_audio,
            on_done=on_tts_done,
            on_error=on_tts_error,
            voice_id=voice_id,
            voice_settings=voice_settings,
        )
        await el_session.connect()

        if session.generation != gen:
            await el_session.close()
            return

        # --- Stream Claude → ElevenLabs → Client ---
        text_buffer = ""
        full_response = ""

        try:
            async for delta in stream_chat_with_claude(
                message=transcript,
                image_base64=image,
                conversation_history=safe_history,
                rag_context=rag_context if rag_context else None,
                max_tokens=max_tokens,
                system_prompt_prefix=prompt_prefix,
                model=config.ANTHROPIC_VOICE_MODEL,
            ):
                if session.generation != gen:
                    break

                full_response += delta
                text_buffer += delta

                # Send text to client
                await session.send_json({"type": "response_text", "text": delta, "done": False})

                # Flush to TTS on sentence boundaries
                if len(text_buffer) >= _MIN_CHUNK_SIZE and _SENTENCE_BOUNDARY.search(text_buffer):
                    to_send, text_buffer = _split_at_boundary(text_buffer)
                    if to_send.strip():
                        await el_session.send_text(to_send)
        except asyncio.CancelledError:
            logger.info("[voice-ws] Claude stream cancelled (interrupted)")
        except Exception as e:
            logger.error(f"[voice-ws] Claude stream error: {e}", exc_info=True)

        # Flush remaining text to TTS
        if text_buffer.strip() and session.generation == gen:
            await el_session.send_text(text_buffer)

        if session.generation == gen:
            await el_session.flush()
            await session.send_json({"type": "response_text", "text": "", "done": True})

        # Wait for TTS to finish sending audio
        if el_session.connected and session.generation == gen:
            try:
                await asyncio.wait_for(
                    asyncio.ensure_future(_wait_for_tts(el_session)),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.warning("[voice-ws] TTS timeout — closing")

        await el_session.close()

        # Always send audio_end and ready state to prevent client getting stuck
        if session.generation == gen:
            if not audio_sent:
                # TTS never produced audio — still need to signal completion
                await session.send_json({"type": "audio_end"})
            await session.send_json({"type": "state", "state": "ready"})

        # Update conversation history
        if full_response and session.generation == gen:
            session.conversation_history.append({"role": "user", "content": transcript})
            session.conversation_history.append({"role": "assistant", "content": full_response})

        elapsed = time.monotonic() - t0
        logger.info(f"[voice-ws] Utterance handled in {elapsed:.2f}s: '{transcript[:40]}' → {len(full_response)} chars")

        # Fire-and-forget logging
        if full_response:
            asyncio.create_task(_safe_log(
                session.user_id, transcript, full_response, image is not None
            ))

    except asyncio.CancelledError:
        logger.info("[voice-ws] Pipeline cancelled")
    except Exception as e:
        logger.error(f"[voice-ws] Pipeline error: {e}", exc_info=True)
        await session.send_json({"type": "error", "message": "Something went wrong. Try again."})
        await session.send_json({"type": "state", "state": "ready"})


async def _wait_for_tts(el_session: ElevenLabsStreamSession) -> None:
    """Wait for ElevenLabs to finish sending audio."""
    while el_session.connected:
        await asyncio.sleep(0.1)


async def _safe_log(user_id: str, transcript: str, response: str, has_image: bool) -> None:
    """Fire-and-forget query logging."""
    try:
        await log_query(
            user_id=user_id,
            question=transcript,
            response=response,
            source="Claude AI (streaming)",
            confidence="medium",
            has_image=has_image,
        )
    except Exception as e:
        logger.warning(f"[voice-ws] Log failed: {e}")
