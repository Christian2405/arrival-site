# Arrival Backend API

FastAPI backend for the Arrival mobile app — AI voice & camera assistant for trade workers.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/stt` | Speech-to-Text (Deepgram) |
| POST | `/api/chat` | AI Chat with vision (Claude) |
| POST | `/api/tts` | Text-to-Speech (ElevenLabs) |
| POST | `/api/upload` | Upload document (Supabase) |
| GET | `/api/documents` | List user documents |
| DELETE | `/api/documents/{id}` | Delete a document |

All AI endpoints support `?demo=true` for canned responses without API keys.

## Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Demo Mode

Every AI endpoint accepts `?demo=true` query parameter. Returns realistic HVAC/trade responses without API keys.

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app, CORS, router includes
    config.py            # All settings from env vars
    routers/
      stt.py             # POST /api/stt
      chat.py            # POST /api/chat
      tts.py             # POST /api/tts
      documents.py       # Upload, list, delete documents
    services/
      deepgram.py        # Deepgram STT
      anthropic.py       # Claude vision + chat
      elevenlabs.py      # ElevenLabs TTS
      supabase.py        # Supabase storage
      demo.py            # Canned demo responses
    middleware/
      auth.py            # Supabase JWT validation
  requirements.txt
  .env.example
  README.md
```
