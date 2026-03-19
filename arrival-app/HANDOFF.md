# Arrival AI — Handoff Document
## "50-Year Veteran in Your Pocket" Upgrade

**Last Updated:** March 19, 2026
**Latest Commits:** `d6efb29` (tts_node filler strip) | `68e67fd` (few-shot + frame reorder) | `c0e5210` (camera flip + verbosity)

---

## What Was the Problem

The AI gave generic, shallow responses. System prompt was 12 lines with zero trade knowledge. Knowledge base was empty. No feedback loop. Job Mode was basic. The goal was to make it feel like talking to a veteran tradesman — direct, specific, authoritative.

---

## Current State (March 19, 2026)

### What's Working
- **Vision identifies new objects** — frames flow via LiveKit WebRTC video track (not expo-camera). Model correctly identifies different objects when camera moves.
- **Camera preview in Job Mode** — uses LiveKit VideoTrack component rendered at root level in home.tsx. Replaces expo-camera CameraView which freezes when LiveKit audio session activates on iOS.
- **Camera flip button** — top-right in Job Mode, switches front/back camera via `setCameraEnabled(false)` then `setCameraEnabled(true, { facingMode })`.
- **Few-shot examples** — 5 example exchanges in JOB_MODE_PROMPT showing ideal response patterns. Model mirrors these better than instruction paragraphs.
- **Frame reorder** — vision questions get `[image, text]`, all other questions get `[text, image]`. Stops model from describing camera before answering.
- **TTS filler stripping** — `tts_node` override strips "Great question!", "First, Second, Third", "I'd recommend", "Hope that helps" etc from audio stream before ElevenLabs speaks them.

### What's Partially Working
- **Verbosity** — improved from ~2/10 to ~4/10. Still too verbose on longer explanations. Model still sounds robotic. Few-shot + filler strip helped but not enough.
- **Humanity** — ~6/10. Needs more natural conversational patterns. Consider OpenAI Realtime API for audio-native conversation.
- **Camera flip** — code is in place but untested after latest push. Uses `setCameraEnabled(false)` then re-enable with new facing mode.

### What's NOT Working
- **Guidance mode** — may not speak. Data channel messages (`guidance_request`, `guidance_stop`) may not be reaching backend. Untested since vision fixes.
- **Pinch-to-zoom** — not implemented. Requires gesture handler integration with LiveKit camera capture options.
- **Proactive vision** — hallucinated previously. Proactive monitor exists but needs tuning — currently may speak up about irrelevant things.

### Critical Architecture Facts
- **Frame delivery:** LiveKit WebRTC video track is the ONLY working path. expo-camera `takePictureAsync` is completely dead when LiveKit audio is active on iOS. HTTP frame upload sends identical frozen frames.
- **`update_instructions()` bug (FIXED):** Was async but called without `await` — silently failed for weeks. Fixed March 19.
- **Frame staleness window:** 4 seconds. If `_latest_frame` is older than 4s, falls back to HTTP store (which has stale data).
- **LiveKit Agents SDK:** v1.4. Has `llm_node`, `tts_node`, `stt_node` pipeline nodes for intercepting/modifying data between stages.

---

## March 19, 2026 Session — Vision Fix, Camera, Verbosity

### Vision: Model Now Sees New Objects
**Root cause found:** expo-camera's `takePictureAsync` returns identical frozen frames when LiveKit's audio session is active on iOS. Camera session conflict — only one module can access the camera at a time.

**Fix:** Publish camera as a LiveKit video track via `room.localParticipant.setCameraEnabled(true, { facingMode: 'environment' })`. Backend subscribes to the video track in `on_track_subscribed`, converts frames to JPEG, stores in `agent._latest_frame`. No more HTTP upload loop.

**Files changed:**
- `frontend/components/LiveKitVoiceRoom.tsx` — `setCameraEnabled(true)` in useEffect after connection, `useTracks([Track.Source.Camera])` to get local track ref, callbacks to pass track and flip function to parent
- `frontend/app/(tabs)/home.tsx` — Renders `LKVideoTrack` at root level for Job Mode camera preview, hides expo-camera CameraView in Job Mode, camera flip button in top bar
- `backend/livekit_agent/agent.py` — `on_track_subscribed` handler processes WebRTC video frames, stores as base64 JPEG in `_latest_frame`

### Camera Preview: LiveKit VideoTrack Replaces expo-camera
**Problem:** expo-camera CameraView freezes (black screen) in Job Mode because LiveKit's audio session steals the iOS camera.

**Fix:** Three-layer approach in home.tsx:
1. Voice/Text mode: expo-camera CameraView (works because no LiveKit)
2. Job Mode (before LiveKit connects): expo-camera CameraView as fallback
3. Job Mode (after LiveKit connects): LiveKit VideoTrack component at root level

**Key constraint:** VideoTrack must be rendered OUTSIDE LiveKitRoom context (at root level of home.tsx) because LiveKitVoiceRoom is nested inside the Job Mode container. Track reference is passed up via `onLocalVideoTrack` callback. VideoTrack works outside LiveKitRoom because it just wraps RTCView with a stream URL.

**React hooks ordering:** All hooks (`useTracks`, `useEffect` for `onLocalVideoTrack`, `useEffect` for `onFlipCameraReady`) MUST be before any early returns in RoomContent. Previous attempts crashed with "Rendered fewer hooks than expected" because hooks were after conditional returns.

### Verbosity Reduction

**1. Few-shot examples in JOB_MODE_PROMPT:**
```
Tech: 'How do I turn this on?'
You: 'Switch on the side of the unit, flip it up.'

Tech: 'What size wire for a 40 amp circuit?'
You: '8 AWG copper.'
```
Models follow examples more reliably than instructions for format/length control.

**2. Frame injection reorder:**
- Vision questions ("what do you see", "what is this"): `[image, user_text]`
- All other questions: `[user_text, image]`
- Removed `[CURRENT CAMERA FEED]` label that drew attention to the image
- Detection via `_VISION_QUESTIONS` keyword list in `on_user_turn_completed`

**3. `tts_node` override (engineering fix, not prompt fix):**
- Intercepts text stream between LLM and ElevenLabs
- Strips filler openers: "Sure!", "Great question!", "Okay, so..."
- Strips robotic transitions: "First, " "Second, " "Third, "
- Strips AI-assistant phrases: "It's important to note", "I'd recommend", "Hope that helps", "Feel free to"
- Strips closing pleasantries: "Let me know if you need anything", "If you have any questions"
- Cleans double spaces from removal

**4. Prompt tightening:**
- SEE section: reduced from 8 lines to 4. Explicitly says "ONLY describe what you see when they ask"
- HOW TO TALK section: reduced from 12 lines to 5. "Match length to the question"
- Added: "NEVER start by describing what you see unless they asked"

### Bug Fixes
- `update_instructions()` — was `async` but called without `await` throughout codebase. Every dynamic prompt update silently failed. Fixed all call sites.
- Camera facing — `setCameraEnabled(true)` defaults to front camera. Fixed with `facingMode: 'environment'`.
- Camera flip — disables then re-enables to force restart with new facing mode.

---

## Research: Making AI Voice More Human (March 19)

### Tools Evaluated
1. **LiveKit Agents 1.4 pipeline nodes** — `llm_node`, `tts_node`, `stt_node` allow intercepting/modifying data between pipeline stages. Currently using `tts_node` for filler stripping.
2. **Anthropic prefilling** — DEAD on Claude Sonnet 4.5+. Trailing assistant messages rejected with 400 error.
3. **OpenAI Realtime API** — Audio-to-audio, no STT/LLM/TTS chain. Natural response length because trained on conversational audio. Doesn't support vision in realtime API yet.
4. **Cartesia Sonic 3 TTS** — 40ms TTFA vs ElevenLabs 832ms. LiveKit has first-class plugin. Would save ~600ms per utterance.
5. **Hume AI EVI** — Emotion-aware turn detection. Replaces entire pipeline — too invasive for now.
6. **Model routing** — Haiku for simple questions (naturally terse), Sonnet for complex. Implementable in `llm_node`.
7. **Few-shot prompting** — Proven: examples beat instructions for format/length control. Implemented.

### Recommended Next Steps (Priority Order)
1. **OpenAI Realtime for Job Mode voice** — biggest impact on naturalness, but no vision support means separate camera path needed
2. **Cartesia Sonic 3** — drop-in LiveKit plugin, saves 600ms/utterance
3. **Model routing in `llm_node`** — Haiku for simple, Sonnet for complex
4. **More few-shot examples** — add examples of longer explanations done naturally

---

## What Was Built (Complete 2-Week Plan)

### Day 1: Expert System Prompt
- **File:** `backend/app/config.py` — `SYSTEM_PROMPT` rewritten from 12 lines to ~100 lines
- Covers: diagnostic methodology, error code response format, brand knowledge (9 brands), NEC wire sizing, refrigerant reference, plumbing reference
- **File:** `backend/app/routers/chat.py` — `max_tokens` raised from 300 to 1024

### Day 1-2: Knowledge Base Seeding
- **File:** `backend/app/services/rag.py` — Added `global_knowledge` namespace search (always searched alongside user/team docs)
- **New file:** `backend/scripts/download_manuals.py` — Downloads manufacturer PDFs (Rinnai, AO Smith, Lennox, Goodman, Square D, Trane, NEC)
- **New file:** `backend/scripts/seed_knowledge_base.py` — Indexes PDFs into Pinecone `global_knowledge` namespace
- **Result:** 519 chunks from 8 PDFs indexed. 2 PDFs 403'd (AO Smith Maintenance, NEC Ampacity) but that info is covered by system prompt and static error codes

### Day 2-3: Feedback System (Thumbs Up/Down)
- **New file:** `backend/app/routers/feedback.py` — `POST /api/feedback`
- **New file:** `backend/migrations/003_create_feedback_table.sql` — Supabase table + RLS policies
- **Modified:** `backend/app/main.py` — Router registered
- **Modified:** `frontend/components/ChatBubble.tsx` — Thumbs up/down buttons below AI messages, thumbs-down shows "What was wrong?" text input
- **Modified:** `frontend/services/api.ts` — `feedbackAPI.submit()`
- **Modified:** `frontend/app/(tabs)/home.tsx` — Wired feedback callback
- **Supabase migration:** RUN MANUALLY — Done (March 2, 2026)

### Day 3-5: 100-Question Quality Test
- **New file:** `backend/scripts/quality_test.py` — Sends questions to Claude, scores answers 0-3, outputs CSV
- **New file:** `backend/scripts/quality_test_questions.csv` — 100 questions across 18 categories with expected answers and must-contain keywords
- **First run result (10 questions):** 2.20/3.00 average — beats 2.0 target

### Day 6-7: Structure-Aware Chunking
- **File:** `backend/app/services/rag.py` — Added `chunk_text_smart()` function
- Keeps tables, numbered steps, and error code blocks as single chunks instead of splitting at arbitrary character boundaries
- Used by `seed_knowledge_base.py` for PDFs/docx files

### Day 7-8: Static Error Code Lookup
- **New file:** `backend/app/services/error_codes.py` (~1900 lines, expanded)
- Hardcoded dictionary: **11 brands** (Rheem, Carrier, Goodman, Lennox, Trane, Rinnai, AO Smith, Daikin, Mitsubishi, **Bradford White**, **Fujitsu**), **421 error codes**
- `lookup_error_code(query)` — regex parses natural language ("Rheem furnace blinking 3 times") to extract brand + code
- `format_error_code_context(result)` — formats as prompt prefix injected before Claude call
- **Modified:** `backend/app/routers/chat.py` — Error code + diagnostic flow lookup before Claude call in text chat
- **Modified:** `backend/app/routers/voice_chat.py` — Error code + diagnostic flow lookup before Claude call in voice chat
- Brand aliases (Ruud→Rheem, Bryant→Carrier, Amana→Goodman, Bradford→Bradford White)

### Day 7-8 (Expanded): Diagnostic Flow Lookup
- **New file:** `backend/app/services/diagnostic_flows.py` (~700 lines)
- 10 complete diagnostic scenarios with step-by-step troubleshooting
- `lookup_diagnostic_flow(query)` — scores symptom keyword matches to find best diagnostic flow
- `format_diagnostic_context(result)` — formats as prompt prefix (used when no error code match)
- Wired into `chat.py`, `voice_chat.py`, and `quality_test.py` — error code takes priority, diagnostic flow is fallback

### Day 7-8 (Expanded): Expert Knowledge Base for RAG
- **New directory:** `backend/knowledge/` — 3 comprehensive expert knowledge files for Pinecone seeding
  - `hvac_expert_knowledge.md` (~4000 words) — Furnace diagnostics, AC diagnostics, heat pump specifics, mini-split/ductless
  - `plumbing_expert_knowledge.md` (~4500 words) — Water heater troubleshooting, drain/waste, supply side, gas piping
  - `electrical_expert_knowledge.md` (~5000 words) — Panel/breaker diagnostics, circuit diagnostics, motor circuits, safety/code
- Written from veteran tradesman perspective with specific readings, values, and brand-specific tips

### Day 8: Confidence Scoring
- **File:** `backend/app/services/anthropic.py` — Added `_score_confidence()` function
- Replaces hardcoded "high" with real scoring: checks RAG match quality, hedging language, evidence availability

### Day 9-12: Job Mode "Jarvis"
- **New file:** `backend/app/services/job_context.py` — In-memory context store with 8hr TTL
- **New file:** `backend/app/routers/job_context.py` — REST endpoints for job context CRUD
- **Modified:** `backend/app/routers/voice_chat.py` — Gets job context, injects into voice prompt
- **Modified:** `frontend/components/JobModeView.tsx` — Equipment picker UI with chips

---

## March 6, 2026 Session — Voice Intelligence + Feedback Flywheel

### Voice Agent RAG Access (commit `a93a695`)

**Problem:** Voice agent (LiveKit) had ZERO access to the knowledge base. When asked "Rheem water heater blinking 7 times" it said "I don't have access to that manual." Also lacked Rheem water heater codes entirely — only furnace codes existed.

**Fixes:**

#### 1. `search_knowledge` Function Tool — `backend/livekit_agent/agent.py`
- NEW function tool added to voice agent: `search_knowledge(query: str)`
- Queries Pinecone `global_knowledge` namespace via `retrieve_context()` from `app.services.rag`
- Returns formatted reference material for agent to use in answers
- Now the voice agent can answer questions about manuals, codes, specs, building codes

#### 2. Rheem Water Heater Blink Codes — `backend/app/services/error_codes.py`
- Added `RHEEM_WATER_HEATER_BLINKS` dictionary with codes 1-8 (meanings, causes, actions)
- Registered in `ERROR_CODE_DB` under `"rheem": {"furnace": ..., "water heater": ...}`
- Added equipment aliases: "hot water heater", "hot water tank", "water tank", "boiler", "air handler"

#### 3. Improved Voice Prompts — `backend/livekit_agent/agent.py`
- `JOB_MODE_PROMPT` updated with:
  - **TOOLS section** — explicit instructions to USE `lookup_error_code`, `search_knowledge`, `look_at_camera`
  - **CRITICAL TRADE KNOWLEDGE** — superheat targets (cap tube 10-15F, TXV 5-10F), refrigerant pressures, wire sizing, clearances
- `DEFAULT_MODE_PROMPT` updated with same tools section
- Fixed wrong cap tube answer: "Superheat target on a cap tube? -> '10 to 15 degrees on a cap tube.'"

#### 4. HVAC Refrigerant Technical Reference — `backend/knowledge/building_codes/HVAC_Refrigerant_Technical_Reference.md`
- NEW comprehensive reference document for Pinecone RAG
- Superheat/subcooling targets for cap tube, TXV, EEV systems
- R-410A, R-22, R-454B, R-134a pressure charts
- Common diagnostic checks, temperature splits, airflow requirements
- Water heater quick reference (gas status lights, electric troubleshooting, tankless)

---

### Feedback Data Flywheel (commit `2b3d157`)

**Goal:** User thumbs up/down + comments that actually teaches the AI and surfaces to Christian for review.

#### The Flywheel Loop
```
User thumbs-down + "cap tubes DO have a superheat target of 10-15F"
  -> POST /api/feedback -> Supabase
  -> Background: Mem0 stores correction for this user

Christian reviews: GET /api/admin/feedback
  -> POST /api/admin/feedback/{id}/correct?promote=true
  -> Supabase: correction + reviewed=true
  -> Pinecone global_knowledge: correction chunk upserted
  -> In-memory cache refreshes within 5 min

Next question about cap tube superheat:
  -> chat.py: cached correction -> system prompt prefix
  -> chat.py: Pinecone correction -> RAG context
  -> Voice agent: search_knowledge -> Pinecone correction
  -> Corrected answer
```

#### Frontend — Feedback UI
- **`frontend/components/ChatBubble.tsx`** — Thumbs up/down icons below assistant messages
  - Thumbs-up: immediate positive feedback
  - Thumbs-down: shows optional comment input ("What was wrong?") then submits
  - After rating: shows confirmation icon, buttons disappear
- **`frontend/app/(tabs)/home.tsx`** — Wired `onFeedback` callback to `feedbackAPI.submit()` (fire-and-forget)
- **`frontend/store/conversationStore.ts`** — Added `feedbackRating` to Message interface

#### Backend — Learning Pipeline
- **`backend/app/services/feedback_learning.py`** (NEW)
  - **Correction cache:** In-memory cache of admin-reviewed corrections, refreshed every 5 min from Supabase
  - **`get_feedback_context(question)`** — keyword-matches incoming question against cached corrections, returns system prompt prefix
  - **`process_negative_feedback()`** — background task stores correction as Mem0 memory for user-specific learning
- **`backend/app/routers/feedback.py`** — Enhanced: after storing negative feedback, fires `process_negative_feedback()` background task
- **`backend/app/routers/chat.py`** — `get_feedback_context()` added to parallel gather + system prompt prefix chain
- **`backend/app/routers/voice_chat.py`** — Same feedback_context injection

#### Backend — Admin Endpoints
- **`backend/app/routers/admin_feedback.py`** (NEW)
  - `GET /api/admin/feedback?secret=X&reviewed=false` — List unreviewed negative feedback
  - `POST /api/admin/feedback/{id}/correct?secret=X&promote=true` — Write correction + optionally push to Pinecone `global_knowledge`
  - `GET /api/admin/feedback/stats?secret=X` — Positive/negative counts, approval rate
  - Auth: `ADMIN_SECRET` env var (set on Render: `arr1val-admin-2026`)

#### Database Migration
- **`backend/migrations/004_enhance_feedback_table.sql`** — ALREADY RUN (March 6, 2026)
  ```sql
  ALTER TABLE feedback ADD COLUMN mode TEXT;
  ALTER TABLE feedback ADD COLUMN reviewed BOOLEAN DEFAULT FALSE;
  ALTER TABLE feedback ADD COLUMN correction TEXT;
  ALTER TABLE feedback ADD COLUMN promoted_to_knowledge BOOLEAN DEFAULT FALSE;
  CREATE INDEX idx_feedback_unreviewed ON feedback(reviewed, created_at DESC) WHERE reviewed = FALSE;
  CREATE INDEX idx_feedback_corrections ON feedback(rating, created_at DESC) WHERE rating = 'negative' AND correction IS NOT NULL;
  ```

---

## March 7, 2026 Session — Knowledge Base Expansion

### Error Codes: 11 → 19 Brands, ~240 → 418 Codes

**File:** `backend/app/services/error_codes.py` (2033 → 4677 lines)

**New brands added:**
- **Navien** — 25 tankless codes (E003–E610) + 9 boiler codes
- **Noritz** — 20 tankless codes (10–99)
- **LG** — 23 mini-split codes (CH01–CH67) + 13 washer + 11 dryer + 12 refrigerator + 9 dishwasher
- **Samsung** — 16 mini-split codes (E101–E464) + 23 washer + 14 dryer + 17 refrigerator + 6 oven
- **Weil-McLain** — 12 boiler codes (E01–E31)
- **Whirlpool** — 10 washer + 6 dryer + 10 oven codes (includes Maytag/KitchenAid aliases)
- **GE** — 10 oven + 3 dishwasher + 5 refrigerator codes
- **Bosch** — 10 dishwasher codes (E01–E25)

**New equipment types:** washer, dryer, refrigerator, dishwasher, oven (+ aliases: fridge, range, stove, clothes washer, etc.)

**Regex updates:** New code format patterns for CH01, F0E2, 5E, D80, ERIF, H2O, SUD, LE1. Pre-normalization for hyphenated codes (E-08→E08) and LG "Er IF" format.

**STT aliases:** 61 total (up from ~30). New: navien, noritz, lg, samsung, weil-mclain, whirlpool, maytag, kitchenaid, ge, bosch.

### Diagnostic Flows: 10 → 22 Scenarios

**File:** `backend/app/services/diagnostic_flows.py` (648 → ~1400 lines)

**12 new flows:**
1. Mini-split not heating/cooling
2. Heat pump not defrosting
3. Tankless water heater won't ignite
4. Slow/clogged drain
5. Running toilet
6. No water pressure
7. GFCI keeps tripping
8. Washer not draining
9. Refrigerator not cooling
10. Dryer not heating
11. Water leak from ceiling
12. Boiler no heat

### Knowledge Base: 3 → 7 Expert Documents

**New files in `backend/knowledge/`:**
- `appliance_expert_knowledge.md` (~5,300 words) — Washer, dryer, refrigerator, dishwasher, oven diagnostics with diagnostic mode entry procedures
- `commercial_refrigeration_knowledge.md` (~4,300 words) — Walk-in coolers/freezers, compressors, ice machines, HACCP compliance

**New files in `backend/knowledge/building_codes/`:**
- `building_codes_reference.md` (~4,100 words) — NEC (GFCI/AFCI/receptacle spacing/wire sizing/box fill), IPC/UPC (drainage/venting/DFU), IMC/IFGC
- `quick_reference_tables.md` (~4,100 words) — 10 structured reference tables: P-T charts, wire ampacity, pipe sizing, BTU calcs, electrical formulas, superheat/subcooling, gas pipe sizing, torque specs

### Auto-Seed Updated

**File:** `backend/app/main.py` — `_seed_building_codes()` renamed to `_seed_knowledge_base()`, now scans ALL `.md` files recursively under `knowledge/` (root + subdirectories) instead of only `knowledge/building_codes/`.

### E2E Test Plan

**New file:** `E2E_TEST_PLAN.md` — 17-section comprehensive test plan covering auth, text chat, voice chat, camera, job mode, feedback, error codes, manuals, history, saved answers, settings, navigation, offline, performance, knowledge base verification (20 test cases for new brands/flows), LiveKit, and admin endpoints.

---

## Architecture Quick Reference

- **Backend:** FastAPI (Python), hosted on Render (`arrival-backend-81x7.onrender.com`)
- **Frontend:** React Native + Expo, TypeScript
- **Auth:** Supabase (JWT)
- **Vector DB:** Pinecone (integrated inference, multilingual-e5-large)
- **RAG namespaces:** `{user_id}` (user docs), `team_{team_id}` (team docs), `global_knowledge` (manufacturer manuals + verified corrections)
- **AI:** Anthropic Claude Sonnet for ALL modes (text, voice, job) — upgraded from Haiku for voice on March 4
- **STT:** Deepgram Nova-2
- **TTS:** ElevenLabs Flash v2.5
- **Voice agent (LiveKit 1.4):** `backend/livekit_agent/agent.py` — proactive camera vision, function tools (`lookup_error_code`, `search_knowledge`), `tts_node` filler stripping, few-shot examples, frame reorder
- **Frame delivery:** LiveKit WebRTC video track (ONLY working path). expo-camera `takePictureAsync` is dead when LiveKit audio active on iOS.
- **Voice pipeline:** Deepgram STT (61 brand aliases) -> error code lookup -> diagnostic flow lookup -> Claude Sonnet (with RAG + job context + camera frame) -> `tts_node` filler strip -> ElevenLabs TTS
- **Instant lookup chain:** Error codes (418 codes, 19 brands, 13 equipment types) -> Diagnostic flows (22 scenarios) -> RAG (Pinecone)
- **Feedback flywheel:** User feedback -> Mem0 (user-specific) + Supabase -> Admin review -> Pinecone (global) -> correction cache (per-request)
- **Crash Reporting:** Sentry (@sentry/react-native)

---

## Environment Variables (Render)

- `ANTHROPIC_API_KEY` — Claude API
- `PINECONE_API_KEY` — Pinecone vector DB
- `PINECONE_INDEX_NAME` — Pinecone index name
- `SUPABASE_URL`, `SUPABASE_KEY` — Supabase connection
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role (for admin endpoints bypassing RLS)
- `DEEPGRAM_API_KEY` — STT
- `ELEVENLABS_API_KEY` — TTS
- `ADMIN_SECRET` — Admin feedback review endpoints (`arr1val-admin-2026`)
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` — LiveKit voice agent
- `MEM0_API_KEY` — Mem0 memory service

---

## Quality Test Results

### Run 1 — March 2 (10 questions, before fixes)
- **Average: 2.20/3.00** (target was 2.0+)

### Run 2 — March 3 (100 questions, after scoring fix)
- **Average: 2.59/3.00** (target was 2.5+)
- 67 Correct, 25 Partial, 8 Wrong, 0 Dangerous

---

## What Was Built After March 3 (March 3-4 Session)

### Apple Developer & App Store Setup
- Enrolled in Apple Developer (Organization: **Spheree.com INC**, Team ID: **95SQ2P2CLS**)
- Bundle ID: `com.arrivalcompany.arrival`
- App name: **"Arrival AI"** (Arrival was taken)
- EAS CLI configured, project linked to `@christianfladgate/arrival`
- First production iOS build done
- Privacy policy URL: `arrivalcompany.com/privacy`
- **App Store NOT submitted yet** — deadline: **March 10th**

### 15-Item Audit (All Implemented)
1. **Account deletion** — `backend/app/routers/account.py` DELETE /api/account (Apple requirement)
2. **Free tier unlocked** — all features enabled on free (no IAP yet)
3. **Version unified** — all three places now say 1.0.0
4. **Dark Mode toggle** — changed from broken switch to "Coming Soon" badge
5. **Error code -> chat wiring** — "Ask Arrival about this code" prefills chat
6. **Camera button in text mode** — camera capture button added to input bar
7. **Offline banner** — `frontend/components/OfflineBanner.tsx`
8. **Frame analysis** — started Haiku, later upgraded to Sonnet
9. **Sentry crash reporting** — installed and configured
10. **Cold start** — existing auto-retry handles it
11. **Document upload in Manuals** — `expo-document-picker`
12. **Navigation** — already clean (drawer + tabs)
13. **Conversation search** — already existed
14. **Units toggle** — wired through to system prompt
15. **home.tsx refactor** — deferred

### UI Redesign — Navigation & Design System
- Tab bar killed globally, drawer is primary navigation
- Design tokens in `Colors.ts`: Spacing, Radius, FontSize, IconSize, Shadow
- `Colors.background` changed from `#FFFFF5` to `#F3F0EB`
- Camera/black screen fix: `CameraView` only mounts when permission granted
- All pages redesigned with flat borders, neutral colors

### Job Mode — Major Overhaul
- Two minimal glass pill indicators (eye for camera, mic/speaker for voice)
- Interrupt support, VAD dead zone fix, operationLock 30s watchdog
- iOS audio volume fix, frame analysis balanced, "OK OK OK" bug fixed

### Intelligence Upgrade
- Voice model: Haiku -> Sonnet for all modes
- Camera quality 0.3 -> 0.5, frame batcher tuned
- Parallel TTS attempted and reverted

### AI Quality Fixes (Error Code Hallucination)
- 40+ STT brand aliases, number word conversion
- "NEVER guess error codes" in system prompt + voice prompts
- Error code context injection strengthened

---

## March 8, 2026 Session — Voice Agent Fix + Mic Icon

### LiveKit Agent Not Starting — Root Cause Found & Fixed

**Problem:** Job mode voice stopped working. Agent process was never running on Render. Multiple debugging attempts (lazy imports, SDK extras removal, AgentServer params) didn't help because the root cause was elsewhere.

**Root Cause:** Render's **Start Command** was set to `uvicorn app.main:app --host 0.0.0.0 --port $PORT` — this only starts the web server. The `start.sh` script (which launches the LiveKit agent process in the background before starting uvicorn) was never executed.

**Fix:** Changed Render Start Command from `uvicorn app.main:app ...` → `bash start.sh` via Render Dashboard > Settings > Build & Deploy > Start Command.

**Result:** Agent process starts, registers with LiveKit Cloud (worker ID, region US West B), and marks itself available for sessions.

**Debug infrastructure added:**
- `GET /api/agent-log` — reads agent stdout/stderr from `/tmp/agent_output.log`
- `GET /api/livekit-debug` — checks agent process (pgrep), SDK import, memory, LiveKit Cloud rooms/participants
- `start.sh` — writes agent output to log file with unbuffered Python (`python -u`)

### Mic Icon Color Indicator

**File:** `frontend/components/JobModeView.tsx`
- Mic icon turns green (`#34C759`) when voice agent is connected
- Transparent (`rgba(255,255,255,0.25)`) when not connected

**File:** `frontend/components/LiveKitVoiceRoom.tsx`
- `onVoiceConnected` callback fires when `agentConnected` state changes
- 20-second agent timeout with "Voice agent unavailable" + Retry button
- Status text: "Connecting...", "Waiting for voice agent..."

**File:** `frontend/app/(tabs)/home.tsx`
- Passes `onVoiceConnected` / `voiceConnected` props between LiveKitVoiceRoom and JobModeView
- Resets `voiceConnected` to false when leaving job mode

---

## Known Issues / Next Steps

1. **Guidance mode untested** — data channel messages may not reach backend. Needs testing.
2. **Pinch-to-zoom** — not implemented. Needs gesture handler + LiveKit camera zoom options.
3. **Proactive vision tuning** — hallucinated earlier, needs grounding to current task context.
4. **Verbosity still ~4/10 on explanations** — `tts_node` helps but model still generates verbose text. Consider model routing (Haiku for simple) or Cartesia Sonic 3 for faster TTS.
5. **OpenAI Realtime API for Job Mode** — best path to natural conversation. No vision support yet means separate camera path.
6. **Cartesia Sonic 3 TTS** — would save ~600ms/utterance vs ElevenLabs. LiveKit plugin exists.
7. **Job Mode memory** — needs persistent memory across sessions (Supabase). Currently no memory of 3 hours ago.
8. **Re-run 100-question test** after all fixes
9. **home.tsx refactor** (deferred)
10. **Demo mode REMOVED** (was in settings, store, home.tsx — all cleaned out)

---

## File Map (Key Changes March 19)

```
backend/livekit_agent/
  agent.py                     — tts_node filler strip, few-shot examples, frame reorder,
                                  setCameraEnabled video track, on_track_subscribed frame processing,
                                  update_instructions await fix, vision question detection

frontend/
  app/(tabs)/home.tsx          — LiveKit VideoTrack preview at root level, camera flip button,
                                  conditional CameraView (hidden in Job Mode), localVideoTrackRef state
  components/LiveKitVoiceRoom.tsx — setCameraEnabled(true, {facingMode}), useTracks for local camera,
                                    onLocalVideoTrack/onFlipCameraReady callbacks, camera facing state
```

---

## Admin Feedback Review — Quick Reference

```bash
# List unreviewed negative feedback
curl "https://arrival-backend-81x7.onrender.com/api/admin/feedback?secret=arr1val-admin-2026&reviewed=false"

# Write a correction and promote to knowledge base
curl -X POST "https://arrival-backend-81x7.onrender.com/api/admin/feedback/{FEEDBACK_ID}/correct?secret=arr1val-admin-2026&promote=true" \
  -H "Content-Type: application/json" \
  -d '{"correction": "Cap tube systems DO have a superheat target of 10-15F"}'

# Get feedback stats
curl "https://arrival-backend-81x7.onrender.com/api/admin/feedback/stats?secret=arr1val-admin-2026"
```
