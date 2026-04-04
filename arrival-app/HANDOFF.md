# Arrival AI — Handoff Document

**Last Updated:** April 4, 2026

---

## Company Vision

**Arrival is a spatial intelligence company.** The app is the data collection engine. Voice Mode and Job Mode get techs to use the camera 1-2 hours a day. The guidance doesn't need to be better than Gemini — it needs to be useful enough that techs open the app.

**Why we win:** Labs train on synthetic scenes and staged demos. We train on millions of hours of real techs doing real work with real outcomes. Messy, chaotic, occluded, noisy. That's the correct training distribution for spatial models that actually work in the real world.

**The finished product:** A spatial world model that predicts the next state of physical reality — giving robotic hardware the spatial foresight to simulate causal outcomes of actions (e.g. how much torque a rusted bolt takes before snapping). We become the intelligence layer for physical work.

---

## Current State (April 4, 2026)

### What's Working
- **Voice Q&A** — LiveKit full-duplex voice, Deepgram STT, Claude Sonnet LLM, ElevenLabs TTS
- **Camera vision** — WebRTC video track frames to agent, model identifies objects
- **Company docs (RAG)** — Auto-search on every query across all modes. Vision extraction for building plans (CAD PDFs). Indexing is automatic on upload, background task, polled by frontend.
- **Guidance mode** — "Guide Me" → knowledge brief → camera-guided step by step
- **Spatial data capture** — Video clips (ffmpeg MP4, CFR 2fps) → S3, with auto-labels, sequences, outcome tracking, frame timestamps
- **Camera intrinsics** — iOS version sent at session start, mapped to focal length/FOV/sensor size, saved to spatial_sessions
- **Consent flow** — Modal on first Job Mode entry, settings toggle, backend gating
- **TTS fixes** — filler stripping, dimension pronunciation ("6 by 6 metres"), mid-sentence break prevention
- **Dashboard document library** — Upload → backend auto-indexes → status polling → "Ready" when done. Retry button for failed docs. Safari popup fix for View button.
- **TestFlight** — Build #8 submitted April 3, 2026. NZ beta testers start Tuesday April 7.

### What's Partially Working
- **Verbosity** — Improved (prompt tightened, 3-sentence cap, address preamble suppressed). Still needs real-world feedback from testers.
- **Proactive monitor** — Has engineering gates. Not tested on real job site.

### What's NOT Working / Untested
- **IMU (100Hz) + ARKit 6-DOF pose** — Planned post-Tuesday. Requires `expo-sensors` + new EAS build. Without these, world model can't distinguish moving hand from moving object.
- **Lens switching detection** — If user pinches to zoom mid-session, intrinsics become invalid. Deferred until ARKit added.
- **Pinch-to-zoom in Job Mode** — LiveKit VideoTrack doesn't expose zoom API.

---

## Architecture

### Stack
- **Backend:** FastAPI (Python) on Render (Docker runtime, ffmpeg installed)
- **Frontend:** React Native + Expo (TypeScript), EAS builds, NOT Expo Go
- **Website:** Vanilla HTML/JS/CSS on Netlify (arrivalcompany.com)
- **Auth/DB:** Supabase | **Vector DB:** Pinecone | **AI:** Claude Sonnet (all modes)
- **STT:** Deepgram Nova-2 | **TTS:** ElevenLabs Flash v2.5
- **Spatial:** S3 (arrival-spatial-data) + Supabase tables + ffmpeg encoding
- **Crash reporting:** Sentry

### Critical Architecture Facts
- **Frame delivery:** LiveKit WebRTC video track via `setCameraEnabled(true)` is the ONLY working path for Job Mode. expo-camera `takePictureAsync` is DEAD when LiveKit audio active on iOS.
- **RAG is automatic in all modes:** `on_user_turn_completed` auto-searches Pinecone for every query >10 chars.
- **Three modes:** Voice (default), Text, Job — mode selector in home.tsx
- **Guidance:** User taps "Guide Me" → `start_guidance` tool → RAG search → knowledge brief → injected into system prompt → proactive monitor watches for that task
- **Proactive monitor:** Background loop, frame-diff-first, single Sonnet call when scene changes. Engineering gates prevent hallucination/repetition. Only active in Job Mode.
- **Spatial capture:** SpatialRecorder class in agent process. Clips at CFR 2fps → ffmpeg → MP4 → S3. Frame timestamps stored per clip for future IMU sync.

### Deployment
- **Render:** Docker build (python:3.13-slim + ffmpeg). `start.sh` launches LiveKit agent + uvicorn.
- **Auto-deploy:** Every push to origin/main triggers Render deploy.
- **TestFlight:** `eas build --platform ios --profile production --auto-submit` → App Store Connect ID: 6759988969

---

## Document Indexing System

### Flow
1. User uploads via dashboard → goes to backend `/upload` endpoint
2. Backend stores file in Supabase Storage, inserts doc row with `status: processing`
3. `_run_indexing_background()` fires as asyncio task — returns immediately
4. Background task downloads file, calls `index_document()`:
   - PyMuPDF text extraction
   - If <500 chars/page → vision extraction (Claude Sonnet reads each page as image)
   - Chunks text → upserts to Pinecone user namespace
5. Status → `indexed` on success, `index_failed` on error
6. Frontend polls Supabase every 8s until status flips → shows "Ready"

### Key Thresholds
- **Vision threshold:** 500 chars/page — anything below triggers vision extraction (covers building plans)
- **Startup reindex:** Picks up stuck docs older than 10 minutes on every Render boot
- **Poll timeout:** 10 minutes max frontend polling

---

## Spatial Intelligence System

### Data Collection (what's being captured now)
| Item | Status | Notes |
|------|--------|-------|
| Video clips (MP4, CFR 2fps) | ✅ S3 | 60s intervals in Job Mode |
| Frame timestamps (ms) | ✅ Supabase | Per-frame device monotonic time |
| Camera intrinsics | ✅ Supabase | Focal length, FOV, sensor size via iOS version lookup |
| Sequences (task grouping) | ✅ Supabase | Start/end times, task description, outcome |
| Auto-labels | ✅ Supabase | Semantic, equipment, workflow, action, state, outcome |
| Outcome labels | ✅ Supabase | Explicit ("fixed") + inferred (10min silence, confidence 0.4) |
| State change detection | ✅ Supabase | Perceptual hash, 15% threshold |
| Environment tags | ✅ Supabase | Attic/basement/rooftop/crawlspace |
| IMU 100Hz | ❌ Pending | Needs expo-sensors + new EAS build |
| ARKit 6-DOF pose | ❌ Pending | Needs expo-sensors + new EAS build |

### Data Structure
- **`spatial_sessions`** — one per LiveKit room connection. Has `camera_intrinsics` (jsonb), `ios_version`.
- **`spatial_clips`** — one per recorded video. Has `frame_timestamps_ms` (jsonb array), `s3_key`, `frame_count`, `duration_seconds`.
- **`spatial_labels`** — many per clip (semantic, equipment, action, object, workflow, state, outcome, meta)
- **`spatial_sequences`** — groups clips into workflows

### Cost Estimate
| Scale | Monthly cost |
|-------|-------------|
| Testing (10 users) | <$1 |
| 100 users | ~$30 |
| 1,000 users | ~$75 |
| 10,000 users | ~$500 |

### Post-Tuesday: Adding IMU + ARKit Pose
Install `expo-sensors` (requires new EAS build), add sensor hook in home.tsx (isolated useEffect, starts after LiveKit connects), batch IMU + pose data to new backend endpoints, store in `spatial_imu` and `spatial_pose` Supabase tables.

---

## Pending Supabase Migrations
Run these in SQL Editor if not already done:
```sql
-- Camera intrinsics on sessions
ALTER TABLE spatial_sessions
ADD COLUMN IF NOT EXISTS camera_intrinsics jsonb,
ADD COLUMN IF NOT EXISTS ios_version text;

-- Frame timestamps on clips
ALTER TABLE spatial_clips
ADD COLUMN IF NOT EXISTS frame_timestamps_ms jsonb;
```

---

## Pricing & Margins

| Plan | Price | Daily Limit | Est. Cost/Month | Margin |
|------|-------|-------------|-----------------|--------|
| Free | $0 | 8 questions | ~$3.60 | Loss leader |
| Pro | $20 | 40 questions | ~$12 (with caching) | ~$8 |
| Business | $200/seat | 250 questions + Job Mode | ~$30-50 | ~$150-170 |

---

## Known Bugs

### Frontend
- Delete account ignores HTTP error status — user signs out thinking deleted but it may not be
- Job Mode pause destroys streaming controller permanently — no resume
- No delete UI for documents in mobile app

### Data Collection
- Lens switching mid-session invalidates intrinsics — not detected or logged. Deferred to ARKit.
- `inferred_fixed` confidence is 0.4 without IMU — can't distinguish "working quietly" from "moved on"

---

## Files Quick Reference

### Backend
- `livekit_agent/agent.py` — Core voice agent. ArrivalAgent class, tools, proactive monitor, guidance, spatial recording hooks
- `app/config.py` — All env vars
- `app/services/rag.py` — Pinecone RAG, vision extraction for sparse PDFs (500 char threshold)
- `app/services/spatial_recorder.py` — SpatialRecorder class (sequences, labels, outcomes, state change)
- `app/services/s3.py` — Async S3 upload via aiobotocore
- `app/services/supabase.py` — Document upload, background indexing trigger
- `app/routers/spatial.py` — Spatial endpoints, ffmpeg stitching (CFR), frame timestamp storage
- `app/routers/livekit_token.py` — Token generation, camera intrinsics lookup, consent flag
- `app/routers/documents.py` — Document indexing background task
- `app/routers/chat.py` — Text chat with auto-RAG
- `app/main.py` — Lifespan, startup reindex task (skips docs <10 min old)

### Frontend
- `app/(tabs)/home.tsx` — Main screen, all three modes, consent modal, frame + timestamp capture
- `app/(tabs)/settings.tsx` — Settings with spatial consent toggle
- `services/livekitService.ts` — Token request with consent flag + ios_version
- `store/authStore.ts` — Supabase auth + spatial_capture_consent

### Infrastructure
- `Dockerfile` — python:3.13-slim + ffmpeg
- `render.yaml` — Docker runtime, all env vars including AWS
- `start.sh` — Launches LiveKit agent + uvicorn
- `frontend/eas.json` — Production build profile, ASC App ID: 6759988969

---

## NZ Beta Testing (Tuesday April 7)

### Build
- Build #8 (version 1.0.0), submitted to TestFlight April 3
- Testers already added — they get auto-notified by Apple

### What to Test
1. Voice Q&A — ask questions, check speed and accuracy
2. Camera vision — point at things, ask "what is this"
3. Company docs — upload a building plan, ask specific questions about it
4. Job Mode — prop up phone, ask questions while working
5. Guidance — tap "Guide Me", ask for help with a task
6. General stability — 5+ minute sessions

### What to Watch
- Verbosity (still too chatty?)
- Response time (target <3s)
- Camera vision quality
- Building plan accuracy (Villa 87/88 test questions as benchmark)
- Does proactive monitor nag or stay quiet?
