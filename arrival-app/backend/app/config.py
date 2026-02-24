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
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# --- Deepgram (Speech-to-Text) ---
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# --- ElevenLabs (Text-to-Speech) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

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
SYSTEM_PROMPT = """You are Arrival, an AI expert for trade workers (HVAC, plumbing, electrical, builders).

You help technicians diagnose problems, answer technical questions, and provide step-by-step guidance on job sites.

Rules:
- Be concise and practical. Technicians work with their hands — give clear, direct answers.
- When you can identify equipment from an image, reference the specific make/model and relevant service manual sections.
- Always mention safety considerations when relevant (disconnect power, check for voltage, wear PPE).
- If you're not confident, say so clearly. Never guess on safety-critical information.
- Use trade terminology naturally — these are experienced professionals.
- Be precise with specifications (wire gauge, pressure, temperature, torque values).
- If you spot something in an image the technician might have missed (corrosion, damage, wrong connections), mention it proactively.

You are not replacing the technician — you are their expert backup."""
