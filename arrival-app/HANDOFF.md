# Arrival AI — Handoff Document

**Last Updated:** March 25, 2026

---

## Company Vision (Updated March 25)

**Arrival is a spatial intelligence company.** The app is the data collection engine. Voice Mode and Job Mode get techs to use the camera 1-2 hours a day. The guidance doesn't need to be better than Gemini — it needs to be useful enough that techs open the app.

**Why we win:** Labs train on synthetic scenes and staged demos. We train on millions of hours of real techs doing real work with real outcomes. Messy, chaotic, occluded, noisy. That's the correct training distribution for spatial models that actually work in the real world.

**The finished product:** A spatial intelligence model that powers robotics, AR, autonomous QA, predictive maintenance, training systems. We become the intelligence layer for physical work.

---

## Current State (March 25, 2026)

### What's Working
- **Voice Q&A** — LiveKit full-duplex voice, Deepgram STT, Claude Sonnet LLM, ElevenLabs TTS
- **Camera vision** — WebRTC video track frames to agent, model identifies objects
- **Company docs auto-search** — RAG runs automatically on EVERY query across ALL modes (voice, text, job). User's uploaded manuals searched first.
- **Guidance mode** — User taps "Guide Me", tells AI the task, AI generates knowledge brief and guides via camera
- **Spatial data capture** — Video clips (ffmpeg MP4) uploaded to S3 with auto-labels, sequences, outcome tracking
- **Consent flow** — Modal on first Job Mode entry, settings toggle, backend gating
- **Prompt caching** — System prompt cached on Anthropic (90% discount on cached tokens, 5-min TTL)
- **System prompt trimmed** — Brand reference data moved to RAG. ~800 tokens vs ~3000. Saves ~$9/month per Pro user.
- **TTS filler stripping** — `tts_node` override strips robotic speech before ElevenLabs
- **Website redesigned** — draft.html deployed as production site, contact form connected to Netlify Forms + send-email

### What's Partially Working
- **Camera flip** — Code uses disable → 500ms wait → re-enable cycle. Untested on latest build.
- **Proactive monitor** — Fires based on scene changes, has engineering gates. Not tested on real job site. Will likely need tuning.
- **Verbosity** — Improved but still ~5/10. Short questions get short answers most of the time.

### What's NOT Working / Untested
- **Video track not reaching agent** — Last test showed "no frame available" in logs. LiveKit connects, voice works, but video frames don't arrive. Needs investigation.
- **Pinch-to-zoom** — Works on CameraView (Voice/Text mode). NOT available in Job Mode (LiveKit VideoTrack doesn't expose camera zoom API). CSS scale removed (caused ugly small box).
- **Spatial recording end-to-end** — Code exists, tables created, S3 configured. No clips have been recorded because video track issue above.
- **Voice Mode video recording** — Endpoint exists (`POST /api/spatial/voice-clip`) but frontend doesn't call it yet.

---

## Architecture

### Stack
- **Backend:** FastAPI (Python) on Render (Docker runtime, ffmpeg installed)
- **Frontend:** React Native + Expo (TypeScript), EAS builds
- **Website:** Vanilla HTML/JS/CSS on Netlify (arrivalcompany.com)
- **Auth/DB:** Supabase | **Vector DB:** Pinecone | **AI:** Claude Sonnet (all modes)
- **STT:** Deepgram Nova-2 | **TTS:** ElevenLabs Flash v2.5
- **Spatial:** S3 (arrival-spatial-data) + Supabase tables + ffmpeg encoding
- **Crash reporting:** Sentry

### Critical Architecture Facts
- **Frame delivery:** LiveKit WebRTC video track via `setCameraEnabled(true)` is the ONLY working path for Job Mode. expo-camera `takePictureAsync` is DEAD when LiveKit audio active on iOS.
- **RAG is automatic in all modes:** `on_user_turn_completed` in agent.py auto-searches Pinecone for every query >10 chars. Text/chat mode also auto-searches. `search_knowledge` tool still available as backup.
- **Three modes:** Voice (default), Text, Job — mode selector in home.tsx
- **Guidance:** User taps "Guide Me" → `start_guidance` tool → RAG search → knowledge brief generated → injected into system prompt → proactive monitor watches for that task
- **Proactive monitor:** Background loop, frame-diff-first, single Sonnet call when scene changes. Engineering gates prevent hallucination/repetition. Only active in Job Mode.
- **Spatial capture:** SpatialRecorder class in agent process. Triggered by queries + alerts. Captures 20s of frames at 2fps → ffmpeg → MP4 → S3. Auto-labels from agent state.

### Deployment
- **Render:** Docker build (python:3.13-slim + ffmpeg). `start.sh` launches LiveKit agent background process + uvicorn.
- **render.yaml:** `runtime: docker`, `dockerfilePath: ./Dockerfile`, `startCommand: bash start.sh`
- **Dockerfile CMD:** `bash start.sh` (starts both agent and FastAPI)
- **TestFlight:** EAS production build → `eas submit --platform ios` → App Store Connect → TestFlight

---

## Spatial Intelligence System

### Data Flow
1. User asks question or alert fires → `trigger_recording()` in SpatialRecorder
2. Captures `_latest_frame` every 500ms for 20 seconds (~40 JPEG frames)
3. Pipes to ffmpeg subprocess → H.264 MP4
4. Uploads to S3: `videos/{year}/{month}/{day}/{session_id}/{clip_id}.mp4`
5. Logs metadata to Supabase `spatial_clips` table
6. Auto-generates labels from agent state (semantic, equipment, workflow, action, objects, guided)

### Data Structure
- **`spatial_sessions`** — one per LiveKit room connection
- **`spatial_clips`** — one per recorded video, with sequence_id, sequence_order, parent_clip_id
- **`spatial_labels`** — many per clip (semantic, equipment, action, object, workflow, state, outcome, meta)
- **`spatial_sequences`** — groups clips into workflows (guided tasks or informal equipment-based)

### Labels (auto-generated)
| Type | Source | Status |
|------|--------|--------|
| semantic | What user asked | ✅ Auto |
| equipment | Equipment type/brand from data channel | ✅ Auto |
| workflow | Stage from scene memory | ✅ Auto |
| action | Activity from scene memory | ✅ Auto (with freshness check) |
| object | Objects detected from scene memory | ✅ Auto |
| guided | Whether guidance was active | ✅ Auto |
| outcome | Did the fix work | ✅ Inferred (10-min silence = fixed) + explicit prompt |
| state | Before/after (perceptual hash comparison) | ✅ Auto |

### Sequences
- **Guided sequences:** Created when `start_guidance` called, ended when guidance stops
- **Informal sequences:** Auto-detected when same equipment queried within 5-minute window
- **Auto-close:** Equipment change or timeout → sequence ends with outcome inference

### Consent
- Frontend: Alert modal on first Job Mode entry, toggle in Settings → "AI training recordings"
- Backend: `recording_consent` in participant metadata, SpatialRecorder skips if false
- Supabase: `spatial_capture_consent` column on profiles table

---

## Pricing & Margins (March 25)

| Plan | Price | Daily Limit | Est. Cost/Month | Margin |
|------|-------|-------------|-----------------|--------|
| Free | $0 | 8 questions | ~$3.60 | Loss leader |
| Pro | $20 | 40 questions | ~$12 (with caching) | ~$8 |
| Business | $200/seat | 250 questions + Job Mode | ~$30-50 (with reduced proactive) | ~$150-170 |

**Cost reductions applied:**
- System prompt trimmed from ~3000 to ~800 tokens (brand data → RAG)
- Prompt caching on REST endpoint (90% discount on cached input tokens)
- Double RAG search eliminated for team users
- Proactive monitor uses frame-diff-first (skips API call when scene unchanged)

---

## Known Bugs (from audit March 25)

### Backend (Critical)
- Dockerfile CMD now correct (`bash start.sh`) — was just `uvicorn` before
- Spatial endpoints now have JWT auth (were public)
- Spatial recorder uses service role key correctly (was using anon key)

### Frontend
- Delete account ignores HTTP error status — user signs out thinking deleted but it may not be
- Job Mode pause destroys streaming controller permanently — no resume
- Cached LiveKit session ignores mode/consent params
- No delete UI for documents in mobile app
- No team_id sent from mobile uploads

### Agent
- `list(string_content)` bug fixed — was splitting strings into characters
- Gate 5 object matching fixed — now uses word-level intersection
- Guidance brief duplicate injection removed (was 3x, now 1x — saves tokens)
- SceneMemory.last_updated added — activity freshness was always reading stale

---

## Files Quick Reference

### Backend
- `livekit_agent/agent.py` — Core voice agent (~1900 lines). ArrivalAgent class, tools, proactive monitor, guidance
- `app/config.py` — All env vars + trimmed system prompt
- `app/services/rag.py` — Pinecone RAG search (user + team + global namespaces)
- `app/services/spatial_recorder.py` — SpatialRecorder class (frame capture, ffmpeg, S3, labels, sequences)
- `app/services/s3.py` — Async S3 upload via aiobotocore
- `app/services/anthropic.py` — Claude API client with prompt caching
- `app/routers/spatial.py` — Spatial debug endpoints (authenticated)
- `app/routers/livekit_token.py` — Token generation with consent flag in metadata
- `app/routers/chat.py` — Text chat with auto-RAG (single search, not double)

### Frontend
- `app/(tabs)/home.tsx` — Main screen, all three modes, consent modal, camera
- `app/(tabs)/settings.tsx` — Settings with spatial consent toggle
- `app/(tabs)/manuals.tsx` — Document upload/management (accepts PDF, images, .docx)
- `components/LiveKitVoiceRoom.tsx` — LiveKit voice room, camera publish, flip
- `services/livekitService.ts` — Token request with consent flag
- `store/authStore.ts` — Supabase auth + spatial_capture_consent

### Infrastructure
- `Dockerfile` — python:3.13-slim + ffmpeg
- `render.yaml` — Docker runtime, all env vars including AWS
- `start.sh` — Launches LiveKit agent + uvicorn
- `migrations/009_spatial_intelligence.sql` — Spatial tables + consent column

---

## Testing Plan (NZ Beta — Sunday March 30)

### Distribution
- EAS production build → TestFlight → add tester emails in App Store Connect
- Testers install TestFlight → install Arrival → sign up → use it

### What to Test
1. Voice Q&A — ask questions, get answers, check speed and accuracy
2. Camera vision — point at things, ask "what is this"
3. Company docs — upload a manual, ask questions about it
4. Job Mode — prop up phone, ask questions while working
5. Guidance — tap "Guide Me", ask for help with a task
6. General stability — 5+ minute sessions, app switching, lock/unlock

### What to Watch
- Verbosity (still too chatty?)
- Response time (target <3s)
- Camera quality (too zoomed, blurry, frozen?)
- Does it hallucinate?
- Does proactive monitor nag or stay quiet?
- Do company docs show up in answers?
