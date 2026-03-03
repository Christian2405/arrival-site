# Arrival AI — Handoff Document
## "50-Year Veteran in Your Pocket" Upgrade

**Last Updated:** March 3, 2026 (Evening — Knowledge Expansion)
**Previous Commit:** `10cefc3` | **Latest:** see git log

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
- **Supabase migration:** RUN MANUALLY — ✅ Done (March 2, 2026)

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
- 10 complete diagnostic scenarios with step-by-step troubleshooting:
  1. No Heat — Gas Furnace
  2. No Cool — Air Conditioning
  3. No Hot Water — Gas Water Heater
  4. No Hot Water — Electric Water Heater
  5. Furnace Short Cycling
  6. AC Freezing Up / Icing
  7. Weak Airflow from Vents
  8. Breaker Keeps Tripping
  9. Not Enough Hot Water / Runs Out Fast
  10. Thermostat Not Responding / Blank Screen
- `lookup_diagnostic_flow(query)` — scores symptom keyword matches to find best diagnostic flow
- `format_diagnostic_context(result)` — formats as prompt prefix (used when no error code match)
- Wired into `chat.py`, `voice_chat.py`, and `quality_test.py` — error code takes priority, diagnostic flow is fallback

### Day 7-8 (Expanded): Expert Knowledge Base for RAG
- **New directory:** `backend/knowledge/` — 3 comprehensive expert knowledge files for Pinecone seeding
  - `hvac_expert_knowledge.md` (~4000 words) — Furnace diagnostics, AC diagnostics, heat pump specifics, mini-split/ductless
  - `plumbing_expert_knowledge.md` (~4500 words) — Water heater troubleshooting, drain/waste, supply side, gas piping
  - `electrical_expert_knowledge.md` (~5000 words) — Panel/breaker diagnostics, circuit diagnostics, motor circuits, safety/code
- Written from veteran tradesman perspective with specific readings, values, and brand-specific tips
- **To seed into Pinecone:** `cd backend && python -m scripts.seed_knowledge_base ../knowledge/` (or `./knowledge/`)

### Day 8: Confidence Scoring
- **File:** `backend/app/services/anthropic.py` — Added `_score_confidence()` function
- Replaces hardcoded "high" with real scoring: checks RAG match quality, hedging language, evidence availability
- Returns "high" / "medium" / "low"

### Day 9-12: Job Mode "Jarvis"
- **New file:** `backend/app/services/job_context.py` — In-memory context store with 8hr TTL
  - `set_job_context()`, `get_job_context()`, `clear_job_context()`, `format_job_context_prompt()`
  - Equipment types list, common brands list
- **New file:** `backend/app/routers/job_context.py` — REST endpoints:
  - `POST /api/job-context` — set equipment context
  - `GET /api/job-context` — get current context
  - `DELETE /api/job-context` — clear context
  - `GET /api/job-context/options` — get equipment types + brands for UI
- **Modified:** `backend/app/main.py` — Router registered
- **Modified:** `backend/app/routers/voice_chat.py` — Gets job context, injects into voice prompt
- **Modified:** `frontend/components/JobModeView.tsx` — Equipment picker UI with chips (equipment type → brand → model input)
- **Modified:** `frontend/services/api.ts` — `jobContextAPI` with `set()`, `get()`, `clear()`, `getOptions()`

---

## Architecture Quick Reference

- **Backend:** FastAPI (Python), hosted on Render
- **Frontend:** React Native + Expo, TypeScript
- **Auth:** Supabase (JWT)
- **Vector DB:** Pinecone (integrated inference, multilingual-e5-large)
- **RAG namespaces:** `{user_id}` (user docs), `team_{team_id}` (team docs), `global_knowledge` (manufacturer manuals)
- **AI:** Anthropic Claude (Sonnet for text chat, Haiku for voice)
- **STT:** Deepgram Nova-2
- **TTS:** ElevenLabs Flash v2.5
- **Voice pipeline:** Record → STT → error code lookup → diagnostic flow lookup → Claude (with RAG + job context) → TTS
- **Instant lookup chain:** Error codes (421 codes, 11 brands) → Diagnostic flows (10 scenarios) → RAG (Pinecone)

---

## Environment Variables (Render)

- `ANTHROPIC_API_KEY` — Claude API
- `PINECONE_API_KEY` — `pcsk_5HP5pb_...` (rotate this — it was shared in chat)
- `PINECONE_INDEX_NAME` — Pinecone index name
- `SUPABASE_URL`, `SUPABASE_KEY` — Supabase connection
- `DEEPGRAM_API_KEY` — STT
- `ELEVENLABS_API_KEY` — TTS

---

## Quality Test Results

### Run 1 — March 2 (10 questions, before fixes)
- **Average: 2.20/3.00** (target was 2.0+)
- 5 Correct, 3 Partial, 1 Wrong, 1 Dangerous (false positive — scoring bug)

### Run 2 — March 3 (100 questions, after scoring fix)
- **Average: 2.59/3.00** (target was 2.5+) ✅
- 67 Correct, 25 Partial, 8 Wrong, 0 Dangerous
- Perfect categories: Electrical Wire Sizing (3.0), Plumbing General (3.0)
- Weakest categories: Building (2.2), Safety (2.2), Scenarios (2.2)
- 8 WRONG answers mostly from: error code definitions (Carrier 34, Lennox E228 — test wasn't using static lookup), heating/cooling confusion (Q11), and being too cautious (Q97)

### Fixes Applied After Run 2 (March 3)
- Quality test now uses `lookup_error_code()` same as production — should fix Carrier 34, Lennox E228
- Error code context moved to TOP of system prompt (was at bottom, Claude sometimes ignored it)
- Error code context language strengthened: "VERIFIED" + "Do NOT substitute"
- Frame analysis prompt completely rewritten — much more conservative, explicit "say OK" rules
- System prompt image section expanded — "never overstate severity", "stain is not water damage"

---

## Known Issues / Next Steps

1. **Rotate Pinecone API key:** It was shared in chat. Generate a new one at Pinecone console and update on Render.

2. **Rotate Anthropic API key:** Also shared in chat. Regenerate at console.anthropic.com and update on Render.

3. ~~**Seed knowledge base files into Pinecone:**~~ ✅ **DONE** (March 3, 2026) — 51 chunks indexed from 3 expert knowledge files (19 HVAC + 15 plumbing + 17 electrical). Total `global_knowledge` namespace: ~692 chunks.

4. **Re-run 100-question test** after deploying all fixes + knowledge expansion to see if score improves above 2.7+

5. **Nice-to-haves (not critical):**
   - Tier 2 sources (Gray Furnaceman scraping) — already covered by static error code dict (now 421 codes)
   - Tier 3 ManualsLib — grab specific model manuals as needed
   - 2 failed PDF downloads (AO Smith Maintenance, NEC Ampacity) — info already covered by knowledge base files

6. **Local dev dependencies:** If running scripts locally, you need:
   ```bash
   pip3 install anthropic httpx pinecone
   ```

---

## File Map (All Changes)

```
backend/
  app/
    config.py                    — Expert system prompt (100 lines), image analysis rules
    main.py                      — Registered feedback + job_context routers
    routers/
      chat.py                    — max_tokens 1024, error code + diagnostic flow lookup
      voice_chat.py              — Error code + diagnostic flow lookup + job context injection
      feedback.py                — NEW: POST /api/feedback
      job_context.py             — NEW: Job context CRUD endpoints
    services/
      anthropic.py               — _score_confidence(), frame analysis (strict), error code prefix ordering
      rag.py                     — global_knowledge namespace, chunk_text_smart()
      error_codes.py             — NEW: Static lookup, 11 brands, 421 codes (expanded)
      diagnostic_flows.py        — NEW: 10 diagnostic scenarios, symptom matching, context formatting
      job_context.py             — NEW: In-memory store with 8hr TTL
  knowledge/                     — NEW: Expert knowledge files for Pinecone RAG seeding
    hvac_expert_knowledge.md     — Furnace, AC, heat pump, mini-split diagnostics (~4000 words)
    plumbing_expert_knowledge.md — Water heaters, drains, supply, gas piping (~4500 words)
    electrical_expert_knowledge.md — Panels, circuits, motors, safety/code (~5000 words)
  migrations/
    003_create_feedback_table.sql — NEW: Supabase migration (ALREADY RUN)
  scripts/
    download_manuals.py          — NEW: Downloads manufacturer PDFs
    seed_knowledge_base.py       — NEW: Indexes PDFs/md files to Pinecone
    quality_test.py              — NEW: 100-question quality test (uses error code + diagnostic flow lookup)
    quality_test_questions.csv   — NEW: Questions + expected answers

frontend/
  components/
    ChatBubble.tsx               — Thumbs up/down feedback buttons
    JobModeView.tsx              — Equipment picker UI (chips)
  services/
    api.ts                       — feedbackAPI, jobContextAPI
  app/(tabs)/
    home.tsx                     — Feedback callback wired
```
