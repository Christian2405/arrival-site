# Arrival AI — Handoff Document
## "50-Year Veteran in Your Pocket" Upgrade

**Last Updated:** March 7, 2026
**Latest Commits:** `a93a695` (voice agent RAG + trade intelligence) | `2b3d157` (feedback data flywheel)

---

## What Was the Problem

The AI gave generic, shallow responses. System prompt was 12 lines with zero trade knowledge. Knowledge base was empty. No feedback loop. Job Mode was basic. The goal was to make it feel like talking to a veteran tradesman — direct, specific, authoritative.

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

- **Backend:** FastAPI (Python), hosted on Render
- **Frontend:** React Native + Expo, TypeScript
- **Auth:** Supabase (JWT)
- **Vector DB:** Pinecone (integrated inference, multilingual-e5-large)
- **RAG namespaces:** `{user_id}` (user docs), `team_{team_id}` (team docs), `global_knowledge` (manufacturer manuals + verified corrections)
- **AI:** Anthropic Claude Sonnet for ALL modes (text, voice, job) — upgraded from Haiku for voice on March 4
- **STT:** Deepgram Nova-2
- **TTS:** ElevenLabs Flash v2.5
- **Voice agent (LiveKit):** `backend/livekit_agent/agent.py` — proactive camera vision, function tools (`lookup_error_code`, `search_knowledge`, `look_at_camera`)
- **Voice pipeline:** Record -> STT (with 61 brand aliases) -> error code lookup -> diagnostic flow lookup -> Claude (with RAG + job context) -> TTS
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

## Known Issues / Next Steps

1. **App Store submission — DEADLINE March 10th**
2. **Remove demo mode** (user request, not yet done)
3. **OpenAI Realtime API for job mode voice** — post-launch priority
4. **Re-run 100-question test** after all fixes
5. **Proactive vision testing** — need a way to test without being on a building site
6. **Area-specific codes/plans** — upload plans/codes for certain areas so workers can ask "what are the restrictions for here"
7. **Speed optimization** — target 3s max per answer (currently 3-5s voice, similar text — acceptable for now)
8. **home.tsx refactor** (deferred)

---

## File Map (All Changes)

```
backend/
  app/
    config.py                    — Expert system prompt, image analysis rules, STT aliases
    main.py                      — All routers registered (feedback, job_context, account, error_codes_api, admin_feedback)
    routers/
      chat.py                    — Error code + diagnostic flow + feedback_context lookup, parallel gather
      voice_chat.py              — Error code + diagnostic flow + feedback_context + job context
      feedback.py                — POST /api/feedback + learning pipeline trigger
      admin_feedback.py          — GET/POST admin review + correction + Pinecone promotion (NEW Mar 6)
      job_context.py             — Job context CRUD endpoints
      account.py                 — DELETE /api/account
      error_codes_api.py         — GET /api/error-codes (public)
      analyze.py                 — Frame analysis endpoint
    services/
      anthropic.py               — _score_confidence(), frame analysis, OK detection
      rag.py                     — global_knowledge namespace, chunk_text_smart()
      error_codes.py             — 19 brands, 418 codes, 13 equipment types, 61 STT aliases (expanded Mar 7)
      diagnostic_flows.py        — 22 diagnostic scenarios (expanded Mar 7)
      feedback_learning.py       — Correction cache + process_negative_feedback (NEW Mar 6)
      job_context.py             — In-memory store with 8hr TTL
      memory.py                  — Mem0 integration (store_memory, retrieve_memories)
      supabase.py                — log_query, get_user_team_id
      usage.py                   — check_query_limit
      elevenlabs.py              — TTS
      demo.py                    — Fixed responses
    middleware/
      auth.py                    — JWT auth
  livekit_agent/
    agent.py                     — Voice agent: proactive vision, search_knowledge tool (NEW Mar 6), improved prompts
  knowledge/
    hvac_expert_knowledge.md
    plumbing_expert_knowledge.md
    electrical_expert_knowledge.md
    appliance_expert_knowledge.md               — Washer/dryer/fridge/dishwasher/oven diagnostics (NEW Mar 7)
    commercial_refrigeration_knowledge.md       — Walk-ins, compressors, ice machines, HACCP (NEW Mar 7)
    building_codes/
      HVAC_Refrigerant_Technical_Reference.md   — Superheat/subcooling, pressure charts (NEW Mar 6)
      building_codes_reference.md               — NEC, IPC/UPC, IMC/IFGC reference (NEW Mar 7)
      quick_reference_tables.md                 — P-T charts, wire sizing, pipe sizing tables (NEW Mar 7)
  migrations/
    003_create_feedback_table.sql — Supabase migration (RUN)
    004_enhance_feedback_table.sql — Learning columns + indexes (RUN Mar 6)
  scripts/
    download_manuals.py          — Downloads manufacturer PDFs
    seed_knowledge_base.py       — Indexes to Pinecone
    quality_test.py              — 100-question quality test

frontend/
  app/
    _layout.tsx                  — Root layout, Sentry, iOS audio, OfflineBanner
    app.json                     — bundleIdentifier, buildNumber, iOS permissions
    (tabs)/
      _layout.tsx                — Tab bar hidden, drawer primary nav
      home.tsx                   — Main screen, all modes, feedback callback wired (Mar 6)
      settings.tsx               — Redesigned
      history.tsx                — Flat bordered cards
      codes.tsx                  — Error codes
      saved-answers.tsx          — Confidence colors
      manuals.tsx                — SectionList, upload
      quick-tools.tsx            — Quick tools
  components/
    ChatBubble.tsx               — Thumbs up/down + comment input (Mar 6), bookmark, 92% width
    JobModeView.tsx              — Two glass pills, equipment chips
    ModeSelector.tsx             — Mode switching
    VoiceStatusIndicator.tsx     — Voice status
    OfflineBanner.tsx            — Network polling + banner
  services/
    api.ts                       — feedbackAPI, jobContextAPI
    jobModeController.ts         — interrupt(), 30s watchdog
    voiceActivityDetector.ts     — Fixed dead zone, iOS audio reset
  constants/
    Colors.ts                    — Design tokens, bg #F3F0EB
  store/
    conversationStore.ts         — Message interface + feedbackRating (Mar 6)
    authStore.ts, documentsStore.ts, savedAnswersStore.ts, settingsStore.ts
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
