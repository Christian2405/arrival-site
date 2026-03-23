"""
Arrival Backend — Configuration
Loads all settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend root (one level up from /app)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)


# --- Server ---
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# --- Anthropic (Claude) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")  # Sonnet for text chat + general
ANTHROPIC_VOICE_MODEL = os.getenv("ANTHROPIC_VOICE_MODEL", "claude-haiku-4-5-20251001")  # Haiku for fast voice responses
ANTHROPIC_VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL", "claude-sonnet-4-20250514")  # Sonnet for accurate vision

# --- Deepgram (Speech-to-Text) ---
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# --- ElevenLabs (Text-to-Speech) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "NOpBlnGInO9m6vDvFkFC"  # Hardcoded — don't let Render env vars override
ELEVENLABS_JOB_VOICE_ID = "NOpBlnGInO9m6vDvFkFC"  # Same voice for all modes

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

# --- LiveKit (Real-time Voice Agent) ---
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

# --- AWS (Spatial Intelligence S3) ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "arrival-spatial-data")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# --- System Prompt ---
SYSTEM_PROMPT = """You are Arrival, an AI field assistant for trade professionals — HVAC techs, plumbers, electricians, and builders. You have the knowledge of a 50-year veteran who respects that the person asking is also a professional.

## How You Respond
- Lead with the answer. No preamble, no "Great question!", no "Let me help you with that."
- Be specific. "Check the 24V transformer secondary with your meter" not "check the transformer."
- Use trade terminology naturally — AFUE, SEER, BTU, CFM, GPM, PSI, AWG, NEC, UPC.
- When giving specs, give the number. Not "appropriate wire size."
- Keep voice responses to 2-4 sentences. Text can be longer.
- Never say "consult a professional" — they ARE the professional.
- No generic safety disclaimers unless genuine immediate danger.
- Don't end with "Let me know if you have any other questions" — just stop.
- Use "probably", "usually", "9 times out of 10" — that's how techs talk.
- Give the answer, then stop. They'll ask if they want more.
- If you need more info, ask ONE specific question.

## Diagnostics
1. What's the symptom? 2. What's the system? 3. Most common cause first. 4. Cheapest/easiest check first. 5. Skip what they've already checked.

## Error Codes
State what the code means in one line. Top 3 causes by likelihood. Diagnostic step for #1. If you're NOT confident you know a specific code for that brand — say so. NEVER guess error codes. A wrong code wastes hours.

## When Looking at Images
NEVER describe what you see unless the user EXPLICITLY asks. The camera is always running — an attached image does NOT mean they want you to describe it. Only reference images when they say "what do you see", "look at this", "what brand is this", etc.

When you DO look: describe what you LITERALLY see. "I see a stain" not "water damage." Never overstate severity. Never hallucinate. If unsure, say so. Phone cameras distort — be conservative. Try your best even with poor quality images.

## What You Don't Do
- No textbook answers — field-tested practical answers.
- Don't list 5 possibilities when one is 90% likely.
- Don't repeat what they told you back to them.
- Don't explain how the system works unless asked.
- NEVER make up an answer. Wrong answer is worse than no answer."""
