# Arrival — AI Assistant for Trade Workers

## What This Project Is

Arrival is a mobile-first AI assistant for trade workers (HVAC, plumbing, electrical, general contractors). The app uses the phone camera + voice to help technicians diagnose problems, answer technical questions, and get step-by-step guidance on job sites.

**Website:** https://arrivalcompany.com (deployed on Netlify)
**Mobile App:** React Native / Expo Go (development)
**Backend API:** Python FastAPI (deployment files ready — needs Railway/Render deploy)

## Project Structure

```
/Video/
├── arrival-app/
│   ├── backend/              # Python FastAPI — AI endpoints (STT, Chat, TTS, Documents)
│   │   ├── app/
│   │   │   ├── main.py       # FastAPI app, CORS, router includes
│   │   │   ├── config.py     # All settings from env vars + Claude system prompt
│   │   │   ├── routers/      # stt.py, chat.py, tts.py, documents.py
│   │   │   ├── services/     # deepgram.py, anthropic.py, elevenlabs.py, supabase.py, demo.py
│   │   │   └── middleware/   # auth.py (Supabase JWT validation)
│   │   ├── requirements.txt
│   │   ├── Procfile          # For Railway/Render deployment
│   │   ├── Dockerfile        # For containerized deployment
│   │   ├── runtime.txt       # Python 3.13
│   │   ├── render.yaml       # Render Blueprint (one-click deploy)
│   │   └── .env              # All API keys (Anthropic, Deepgram, ElevenLabs, Supabase)
│   └── frontend/             # React Native Expo SDK 54 + TypeScript
│       ├── app/
│       │   ├── _layout.tsx   # Root layout — auth gate, initializes stores (settings, conversations, savedAnswers)
│       │   ├── index.tsx     # Redirects to /(tabs)/home
│       │   ├── login.tsx     # Email/password + Google OAuth
│       │   ├── signup.tsx    # Full signup with trade/experience pickers
│       │   └── (tabs)/
│       │       ├── _layout.tsx       # Tab navigator (Home, History, Settings visible; rest in drawer)
│       │       ├── home.tsx          # Main screen — camera background, chat, voice PTT, drawer, save answers
│       │       ├── history.tsx       # Conversation history with search
│       │       ├── settings.tsx      # Voice, units, demo mode, plan display
│       │       ├── codes.tsx         # Document viewer filtered by code categories
│       │       ├── manuals.tsx       # Document viewer filtered by manual categories
│       │       ├── quick-tools.tsx   # 5 working trade calculators (Wire Gauge, Voltage Drop, Ohm's Law, Pipe Sizing, P/T Chart)
│       │       └── saved-answers.tsx # Bookmarked AI answers — real store, search, delete, expand
│       ├── components/       # ChatBubble.tsx (with long-press save), ArrivalLogo.tsx
│       ├── constants/        # Colors.ts (brand), Tiers.ts (free/pro/business limits)
│       ├── services/         # api.ts (axios + JWT), supabase.ts (client)
│       ├── store/            # authStore.ts, conversationStore.ts, settingsStore.ts, documentsStore.ts, savedAnswersStore.ts
│       └── .env              # EXPO_PUBLIC_BACKEND_URL, EXPO_PUBLIC_SUPABASE_URL/KEY
├── arrival-site/             # Static HTML/CSS/JS + Netlify Functions
│   ├── index.html            # Landing page + login/signup/pricing (single HTML SPA)
│   ├── auth.js               # Supabase auth (signup, login, logout, password reset, dev bypass)
│   ├── dashboard-individual.html  # Free/Pro user dashboard
│   ├── dashboard-business.html    # Business/team dashboard
│   ├── dashboard.js          # Dashboard logic (loads profile, docs, billing)
│   ├── dashboard-business.js # Business dashboard (team members, docs, seat management)
│   ├── styles.css            # Main site styles
│   ├── dashboard.css         # Dashboard styles
│   ├── netlify.toml          # Netlify config
│   ├── netlify/functions/    # Serverless functions
│   │   ├── create-checkout.js    # Stripe Checkout (Pro $25/mo, Business $250/mo)
│   │   ├── stripe-webhook.js     # Handles checkout, sub updates, cancellation, payment failures
│   │   ├── create-portal.js      # Stripe Customer Portal
│   │   ├── get-billing.js        # Fetch billing info
│   │   ├── cancel-subscription.js
│   │   ├── update-payment.js
│   │   ├── update-seats.js       # Add/remove business seats
│   │   └── send-email.js         # Resend email API
│   └── email-templates/      # confirm-signup, magic-link, password-reset, change-email
├── supabase/migrations/
│   └── 001_initial_schema.sql    # Full DB schema (users, teams, team_members, documents, subscriptions)
├── lib/supabase.js           # Shared Supabase client helper (for Netlify functions)
└── trade-ai-video/           # Old Remotion video project — NOT part of the app
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Mobile App | React Native 0.81 + Expo SDK 54 + expo-router + TypeScript |
| State Management | Zustand (auth, conversations, settings, documents, savedAnswers stores) |
| Backend API | Python 3.13 + FastAPI 0.115 + uvicorn |
| AI Chat | Anthropic Claude Sonnet (with vision support) |
| Speech-to-Text | Deepgram Nova-2 |
| Text-to-Speech | ElevenLabs Turbo v2.5 |
| Database | Supabase (PostgreSQL + Auth + Storage + RLS) |
| Website | Static HTML/CSS/JS on Netlify |
| Payments | Stripe (Checkout, Webhooks, Customer Portal) |
| Email | Resend (transactional emails) |
| Auth | Supabase Auth (email/password + Google OAuth) |

## API Endpoints (Backend)

| Method | Path | Description | Demo Mode |
|--------|------|-------------|-----------|
| POST | `/api/stt` | Speech-to-Text via Deepgram | ?demo=true |
| POST | `/api/chat` | AI Chat with vision via Claude | ?demo=true |
| POST | `/api/tts` | Text-to-Speech via ElevenLabs | ?demo=true |
| POST | `/api/upload` | Upload document to Supabase Storage | No |
| GET | `/api/documents` | List user documents (RLS-scoped) | No |
| DELETE | `/api/documents/{id}` | Delete document | No |
| GET | `/api/health` | Health check | N/A |

All AI endpoints accept `?demo=true` for canned trade responses without needing API keys.

## Database Schema (Supabase)

**Tables:** users, teams, team_members, documents, subscriptions
**RLS:** Enabled on all tables. Users see own data. Team members see team data. Admins manage team members.
**RPC:** `create_team_with_owner` — bootstraps team + admin member (bypasses RLS chicken-egg problem)

## Subscription Tiers

| Feature | Free | Pro ($25/mo) | Business ($250/mo) |
|---------|------|-------------|-------------------|
| Max Documents | 10 | 50 | Unlimited |
| Job Mode | No | No | Yes |
| Proactive Alerts | No | No | Yes |
| Team Documents | No | No | Yes |
| Voice Output | Yes | Yes | Yes |

## Brand / Design

- **Primary background:** `#FFFFF5` (warm off-white)
- **Accent color:** `#D4842A` (warm orange)
- **Text:** `#1A1A1A` (near-black)
- **Font feel:** SF Pro / system font, tight letter-spacing (-0.2 to -0.5), 600-800 weight
- **Design language:** Clean, minimal, iOS-native feel with glass effects on camera overlay
- **Camera home screen:** Full-screen camera background, glass input bar, animated drawer

## Development Commands

### Backend
```bash
cd arrival-app/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Mobile)
```bash
cd arrival-app/frontend
npm install
npx expo start --clear
# Scan QR with Expo Go on phone
```

### Important: Backend URL
The mobile app connects to the backend via `EXPO_PUBLIC_BACKEND_URL` in `arrival-app/frontend/.env`.
Currently set to `http://192.168.1.151:8000` (local IP). Update this when:
- Your Mac's IP changes
- Backend is deployed to Railway/Render

## Deploying the Backend

### Option A: Render (recommended — has free tier)
1. Push `arrival-app/backend/` to a GitHub repo (or connect the monorepo)
2. Go to https://render.com → New → Web Service
3. Connect your repo, set root directory to `arrival-app/backend`
4. Render will auto-detect `render.yaml` blueprint
5. Add all env vars from `.env` in the Render dashboard
6. After deploy, update `EXPO_PUBLIC_BACKEND_URL` in `arrival-app/frontend/.env`

### Option B: Railway
1. Install Railway CLI: `npm i -g @railway/cli`
2. `cd arrival-app/backend && railway login && railway init`
3. `railway up` — auto-detects Procfile
4. Add env vars: `railway variables set ANTHROPIC_API_KEY=... DEEPGRAM_API_KEY=...` etc.
5. Get deploy URL and update `EXPO_PUBLIC_BACKEND_URL`

### Required Env Vars for Deployment
```
ANTHROPIC_API_KEY
DEEPGRAM_API_KEY
ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
PORT (usually auto-set by platform)
```

## Current Status (Feb 2026)

### Working
- Full voice pipeline: Record → STT (Deepgram) → Claude → TTS (ElevenLabs) → Playback
- Camera vision: Snap photo → Claude analyzes equipment
- Text chat with conversation history
- Auth: Email/password + Google OAuth (mobile + website)
- User profiles, subscriptions, team memberships
- Document upload/list/delete (Codes + Manuals screens)
- Stripe billing (checkout, webhooks, portal, seat management)
- Demo mode (works without API keys)
- All database RLS policies
- **Quick Tools** — 5 working calculators: Wire Gauge, Voltage Drop, Ohm's Law, Pipe Sizing, P/T Chart
- **Saved Answers** — Long-press assistant messages to bookmark. Persisted via AsyncStorage. Search, expand, delete.
- **Manuals screen** — filters documents by manual categories from Supabase

### Incomplete / Not Yet Built
- Dark Mode — "Coming Soon" badge in settings
- Notifications — settings row exists but no push notification setup
- Backend runs on localhost only — deployment files ready but NOT deployed yet
- No tests anywhere
- No CI/CD

### Known Issues
- Backend URL in frontend .env is hardcoded to local IP — fragile until deployed
- `profile?.trade` may be undefined if user profile doesn't have a trade field — saved answers fall back to "General"

## Supabase Project
- **URL:** https://nmmmrujtfrxrmajuggki.supabase.co
- **Stripe Price IDs:** Pro: `price_1T2wkcAO3BMpwX672CsLrhdQ`, Business Base: `price_1T2wlnAO3BMpwX67HZQKSk6R`, Business Seat: `price_1T2wmDAO3BMpwX67JSkM2fkF`
