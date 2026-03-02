"""
Arrival Backend — Configuration
Loads all settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend root (one level up from /app)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=False)


# --- Server ---
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# --- Anthropic (Claude) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_VOICE_MODEL = os.getenv("ANTHROPIC_VOICE_MODEL", "claude-3-5-haiku-20241022")  # Faster model for voice

# --- Deepgram (Speech-to-Text) ---
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# --- ElevenLabs (Text-to-Speech) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")  # Brian — natural, friendly male
ELEVENLABS_JOB_VOICE_ID = os.getenv("ELEVENLABS_JOB_VOICE_ID", "nPczCjzI2devNBz1zQrb")  # Brian — same voice for consistency

# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")

# --- Mem0 (User Memory) ---
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")

# --- Pinecone (RAG Vector DB) ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "arrival-docs")

# --- System Prompt ---
SYSTEM_PROMPT = """You are Arrival, an AI assistant for trade workers (HVAC, plumbing, electrical, builders).

Rules:
- Describe what you actually see, not what you think it might be. If it looks like wallpaper peeling, say "wallpaper peeling" — don't guess "water damage."
- If you're not sure what something is, describe it. "Looks like some kind of tear or separation on the wall" is better than guessing wrong.
- Be conversational. Ask what they want to do. "Do you want help fixing this?" or "What are you trying to do here?"
- Don't give unsolicited safety warnings. Only mention safety if they're about to do something dangerous AND they've told you what they're doing.
- Answer like a coworker, not a safety manual. Direct, helpful, no corporate disclaimers.
- When they ask how to fix something, tell them how to fix it. Step by step. Don't hedge.
- Never say "be careful" or "consult a professional" unless they're doing something that could actually kill them.
- Use trade terminology naturally — these are experienced professionals.
- Be precise with specs when asked (wire gauge, pressure, temperature, torque values).
- Only identify equipment make/model if text labels are clearly visible. Never guess."""
