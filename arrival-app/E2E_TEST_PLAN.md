# Arrival AI — End-to-End Test Plan

**Purpose:** Comprehensive testing checklist — app, backend, and website.
**App Device:** Physical iOS device via Expo Go (or production build)
**Website:** https://arrivalcompany.com (desktop + mobile browser)
**Backend:** https://arrival-backend-81x7.onrender.com

---

## Pre-Test Setup

1. **Wake the backend** — hit `https://arrival-backend-81x7.onrender.com/api/health` in a browser. Wait for `{"status":"healthy"}`. Render free tier may take 30-60s to spin up.
2. **Run diagnostics** — `https://arrival-backend-81x7.onrender.com/api/diagnostics?secret=<DIAGNOSTICS_SECRET>` to verify all services (Supabase, Pinecone, Claude, ElevenLabs, Mem0) are responding.
3. **Have a Supabase account ready** — either existing or create a fresh test account.
4. **Have these items on hand for testing:**
   - A HVAC unit, water heater, or electrical panel (or photos of them) for camera testing
   - A WiFi connection and a way to toggle airplane mode for offline testing
   - Headphones/earbuds for voice testing

---

## 1. Authentication & Account

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 1.1 | **Sign up** | Open app → Sign up with email/password | Account created, lands on home screen |
| 1.2 | **Sign out** | Drawer → Settings → Sign Out | Returns to login screen |
| 1.3 | **Sign in** | Enter credentials → Sign In | Lands on home screen, previous conversations visible |
| 1.4 | **Password reset** | Tap "Forgot Password" → Enter email | Reset email sent (check inbox) |
| 1.5 | **Account deletion** | Settings → Delete Account → Confirm | Account deleted, returns to login. Verify in Supabase that user data is removed |
| 1.6 | **Session persistence** | Sign in → kill app → reopen | Still signed in, no re-auth required |

---

## 2. Text Chat (Home Screen — Default Mode)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 2.1 | **Basic question** | Type "What's the superheat target on a cap tube system?" | Should answer "10-15°F" — specific, no fluff |
| 2.2 | **Error code — known** | Type "Rheem furnace 3 blinks" | Should get exact error code match: "Pressure switch fault" with causes and actions |
| 2.3 | **Error code — Navien** | Type "Navien error E003" | Should match: ignition failure with causes/actions |
| 2.4 | **Error code — appliance** | Type "LG washer OE error" | Should match: drain pump fault |
| 2.5 | **Error code — mini split** | Type "Daikin U4 error" | Should match: communication error between indoor/outdoor |
| 2.6 | **Error code — unknown** | Type "Acme furnace code 99" | Should say it doesn't have that code, ask for model # or diagnostic chart |
| 2.7 | **Diagnostic flow** | Type "My furnace won't heat" | Should walk through the no-heat diagnostic flow starting with thermostat |
| 2.8 | **Plumbing question** | Type "Toilet keeps running" | Should trigger running toilet diagnostic flow |
| 2.9 | **Electrical question** | Type "GFCI keeps tripping in bathroom" | Should trigger GFCI diagnostic flow |
| 2.10 | **Appliance question** | Type "Dryer not heating" | Should trigger dryer no-heat diagnostic flow |
| 2.11 | **NEC code question** | Type "What size wire for a 40 amp circuit?" | Should answer "8 AWG copper" — NEC reference |
| 2.12 | **Plumbing code question** | Type "What's the minimum drain slope for a 2 inch pipe?" | Should answer "1/4 inch per foot" |
| 2.13 | **Refrigerant question** | Type "R-410A pressures at 95 degrees?" | Should give ~120 PSI suction / ~350 PSI discharge |
| 2.14 | **Follow-up question** | After 2.2, type "What if the flame sensor is clean?" | Should continue the conversation contextually |
| 2.15 | **Long conversation** | Send 10+ messages in one conversation | Should maintain context, no errors |
| 2.16 | **New conversation** | Tap new conversation button | Fresh chat, no previous context |
| 2.17 | **Response time** | Time a text response | Should be under 5 seconds |

---

## 3. Voice Chat (Home Screen — Voice Mode)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 3.1 | **Activate voice** | Tap mic button | Mic activates, listening indicator shows |
| 3.2 | **Ask a question** | Say "What's a Carrier code 34?" | STT transcribes correctly, gets error code answer, TTS speaks response |
| 3.3 | **STT brand alias** | Say "My Ream furnace is blinking 3 times" (Rheem) | Should recognize "Ream" as Rheem via STT aliases |
| 3.4 | **STT brand alias 2** | Say "Rin-eye tankless error 11" (Rinnai) | Should recognize as Rinnai |
| 3.5 | **Voice response quality** | Listen to TTS response | Should be natural, clear, concise (2-4 sentences) |
| 3.6 | **Voice response time** | Time from end of speech to start of audio | Should be under 5 seconds |
| 3.7 | **Interrupt** | While AI is speaking, start talking | Should stop TTS and listen to new input |
| 3.8 | **Background noise** | Test in a noisy environment | Should still transcribe reasonably well |
| 3.9 | **Multiple voice turns** | Have a 3-4 turn voice conversation | Should maintain context between turns |

---

## 4. Camera / Frame Analysis

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 4.1 | **Camera permission** | First launch → camera access | Permission dialog appears, camera activates on grant |
| 4.2 | **Camera button in text mode** | Tap camera icon in input bar | Camera opens, can capture photo |
| 4.3 | **Photo + question** | Take photo of equipment → type "What brand is this?" | Should analyze image and attempt to identify |
| 4.4 | **Don't describe unsolicited** | Send a text question with camera running in background | Should NOT describe what the camera sees unless asked |
| 4.5 | **Explicit look request** | Say/type "What do you see?" with camera pointed at something | Should describe what's visible |
| 4.6 | **Camera in job mode** | Enter job mode → point camera at equipment | Camera eye pill should show, proactive analysis when relevant |

---

## 5. Job Mode ("Jarvis")

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 5.1 | **Enter job mode** | Switch to Job Mode via mode selector | Two glass pills appear (eye + mic/speaker) |
| 5.2 | **Set equipment** | Select equipment type/brand from chips | Equipment context set, visible in UI |
| 5.3 | **Voice interaction** | Say "What should I check first?" | Should respond in context of selected equipment |
| 5.4 | **Hands-free flow** | Have a multi-turn hands-free conversation | Should work smoothly without touching phone |
| 5.5 | **Interrupt support** | Start talking while AI is responding | Should stop and listen |
| 5.6 | **Exit job mode** | Switch back to default mode | Exits cleanly, no stuck states |
| 5.7 | **Job context persistence** | Set job context, switch modes, come back | Context should still be there (8hr TTL) |

---

## 6. Feedback System

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 6.1 | **Thumbs up** | Tap thumbs up on an AI response | Icon changes to confirmation, feedback sent |
| 6.2 | **Thumbs down** | Tap thumbs down | Comment input appears: "What was wrong?" |
| 6.3 | **Thumbs down + comment** | Enter comment → submit | Feedback submitted, confirmation shown |
| 6.4 | **Verify in admin** | `curl "https://arrival-backend-81x7.onrender.com/api/admin/feedback?secret=arr1val-admin-2026&reviewed=false"` | Should see the feedback entry with comment |
| 6.5 | **Admin correction** | POST a correction via admin endpoint with `promote=true` | Correction stored, promoted to Pinecone |
| 6.6 | **Verify correction works** | Ask the same question that was corrected (wait 5 min for cache refresh) | Should now give the corrected answer |

---

## 7. Error Codes Page

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 7.1 | **Browse codes** | Drawer → Error Codes | Error codes page loads, brands listed |
| 7.2 | **Built-in tab** | Tap "Built-in Codes" tab | Shows all brands with code counts |
| 7.3 | **My Docs tab** | Tap "My Docs" tab | Shows user-uploaded documents (or empty state) |
| 7.4 | **Team tab** | Tap "Team" tab | Shows team documents (if team access enabled) |
| 7.5 | **Search codes** | Search for "Rheem furnace" | Relevant codes shown |
| 7.6 | **View code detail** | Tap on a code | Shows meaning, causes, action in expandable view |
| 7.7 | **"Ask Arrival" button** | Tap "Ask Arrival about this code" | Should prefill chat with the error code question |
| 7.8 | **New brands visible** | Check that Navien, Noritz, LG, Samsung, Bosch, Whirlpool, GE, Weil-McLain are listed | All new brands show up with correct code counts |
| 7.9 | **Brand icons** | Check brand icons render for each brand | Icons display correctly, no broken images |
| 7.10 | **Pull to refresh** | Pull down on codes list | Refreshes without errors |

---

## 8. Manuals / Documents

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 8.1 | **View manuals** | Drawer → Manuals | Manuals page loads, category sections visible |
| 8.2 | **My Docs tab** | Tap "My Docs" tab | Shows personal documents |
| 8.3 | **Team tab** | Tap "Team" tab | Shows team members' shared documents |
| 8.4 | **Upload document** | Tap upload → select a PDF | Document uploads, appears in correct category |
| 8.5 | **Document categories** | Check categories display | Equipment Manuals, Spec Sheets, Training Materials, Company SOPs, Building Plans, etc. |
| 8.6 | **Search documents** | Use search bar to search by filename | Filters documents correctly |
| 8.7 | **Open document** | Tap on an uploaded document | Opens/downloads via signed URL |
| 8.8 | **Ask about uploaded doc** | After upload, ask a question about the document content in chat | RAG retrieves relevant chunks from the doc |
| 8.9 | **Delete document** | Swipe/tap delete on an uploaded doc | Document removed from list |
| 8.10 | **Pull to refresh** | Pull down on manuals list | Refreshes without errors |
| 8.11 | **File size/date display** | Check document list items | Shows file size and upload date |

---

## 9. Conversation History

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 9.1 | **View history** | Drawer → History | Past conversations listed with timestamps |
| 9.2 | **Resume conversation** | Tap on a past conversation | Loads the conversation, can continue chatting |
| 9.3 | **Search history** | Use search bar | Filters conversations by keyword |

---

## 10. Saved Answers

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 10.1 | **Save an answer** | Tap bookmark icon on an AI response | Answer saved, confirmation shown |
| 10.2 | **View saved answers** | Drawer → Saved Answers | Saved answers listed |
| 10.3 | **Search saved** | Use search bar | Filters saved answers by keyword |
| 10.4 | **Expand answer** | Tap on a saved answer | Expands to show full answer text |
| 10.5 | **Confidence colors** | Check confidence badges | High (green), Medium (yellow), Low (red) display correctly |
| 10.6 | **Trade badges** | Check trade category colors | HVAC, Electrical, Plumbing badges show correctly |
| 10.7 | **Answer count** | Check count badge at top | Shows correct number of saved answers |
| 10.8 | **Delete saved answer** | Swipe/tap delete | Answer removed from saved list |
| 10.9 | **Empty state** | Delete all saved answers | Shows empty state with how-to instructions |

---

## 11. Settings

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 11.1 | **Profile display** | Settings → check top section | Shows avatar with initials, display name, email, plan badge (Free/Pro), usage stats (Queries/Documents) |
| 11.2 | **Voice output toggle** | Settings → Voice & Input → Voice Output | Toggle on/off, TTS responds accordingly |
| 11.3 | **Voice speed** | Settings → Voice Speed (Slow/Normal/Fast) | Changes TTS playback speed |
| 11.4 | **Text size** | Settings → Text Size (Small/Medium/Large) | Chat text size changes |
| 11.5 | **Units toggle** | Settings → toggle Imperial/Metric | Subsequent answers use the selected unit system |
| 11.6 | **Demo mode** | Settings → Demo Mode toggle | Toggle works, hint text shown |
| 11.7 | **Notifications** | Settings → Notifications | Links to device settings |
| 11.8 | **Microphone permission** | Settings → Permissions → Microphone | Shows current permission state, can toggle |
| 11.9 | **Camera permission** | Settings → Permissions → Camera | Shows current permission state, can toggle |
| 11.10 | **Subscription** | Settings → Account → Subscription | Links to billing |
| 11.11 | **Help & Support** | Settings → Help & Support | Opens email link |
| 11.12 | **Terms & Privacy** | Settings → Terms & Privacy | Opens arrivalcompany.com/privacy |
| 11.13 | **Upgrade banner** | Check for upgrade banner (free users) | Shows upgrade CTA linking to pricing |
| 11.14 | **Sign out** | Settings → Sign Out | Returns to login screen |
| 11.15 | **Delete account** | Settings → Delete Account → Confirm | Account deleted, returns to login |
| 11.16 | **Version display** | Settings → scroll to bottom | Shows version 1.0.0 |

---

## 12. Navigation & Drawer

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 12.1 | **Drawer open** | Swipe right or tap hamburger | Drawer opens smoothly |
| 12.2 | **Drawer items** | Check all menu items present | New Chat, Saved Answers, Manuals, Quick Tools, History, Settings — all present |
| 12.3 | **New Chat button** | Tap "New Chat" in drawer | Starts fresh conversation, drawer closes |
| 12.4 | **Recent conversations** | Check recent conversations section in drawer | Shows up to 20 recent conversations |
| 12.5 | **Delete from drawer** | Tap delete on a recent conversation in drawer | Conversation removed |
| 12.6 | **Profile section** | Check bottom of drawer | Shows avatar, display name, plan label, settings gear |
| 12.7 | **Navigate to each page** | Tap each drawer item | Each page loads without crash |
| 12.8 | **Back navigation** | Navigate to any page → press back | Returns to previous screen correctly |
| 12.9 | **Mode selector** | On home screen, switch between Voice/Text/Job modes | Mode changes, UI updates correctly |
| 12.10 | **Deep link handling** | If applicable, test any deep links | Opens correct screen |

---

## 13. Offline Behavior

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 13.1 | **Offline banner** | Toggle airplane mode ON | Offline banner appears at top |
| 13.2 | **Offline chat attempt** | Try sending a message while offline | Graceful error, not a crash |
| 13.3 | **Reconnect** | Toggle airplane mode OFF | Banner disappears, app resumes normally |
| 13.4 | **Backend cold start** | Let backend sleep (~15 min idle), then send request | Auto-retry handles cold start, response arrives |

---

## 14. Performance & Stability

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 14.1 | **Memory usage** | Use app for 15+ minutes with voice/camera | No memory warnings, no slowdown |
| 14.2 | **Background/foreground** | Send app to background → return | Resumes cleanly, no stuck states |
| 14.3 | **Rapid mode switching** | Switch between text/voice/job modes quickly | No crashes or stuck UI |
| 14.4 | **Kill and restart** | Force kill app → reopen | Launches cleanly, auth preserved |
| 14.5 | **Sentry integration** | Check Sentry dashboard for any crashes | No unresolved crashes |

---

## 15. Knowledge Base Verification (NEW — Post-Expansion)

These tests verify the expanded knowledge base is working correctly.

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 15.1 | **Navien tankless** | "Navien error E003" | Ignition failure — check gas supply, check igniter, purge air from line |
| 15.2 | **Noritz tankless** | "Noritz error 11" | Ignition failure |
| 15.3 | **LG mini split** | "LG mini split CH05" | Indoor/outdoor communication error |
| 15.4 | **Samsung mini split** | "Samsung mini split E101" | Communication error |
| 15.5 | **Weil-McLain boiler** | "Weil-McLain boiler E01" | Ignition failure |
| 15.6 | **LG washer** | "LG washer LE error" | Motor overload |
| 15.7 | **Samsung dryer** | "Samsung dryer HE error" | Heater circuit error |
| 15.8 | **Whirlpool washer** | "Whirlpool washer F9E1" | Drain pump error |
| 15.9 | **Bosch dishwasher** | "Bosch dishwasher E15" | Leak protection (Aquastop) |
| 15.10 | **GE oven** | "GE oven F3 code" | Open oven temp sensor |
| 15.11 | **Mini-split diagnostic** | "My mini split isn't cooling" | Should trigger mini-split diagnostic flow |
| 15.12 | **Tankless diagnostic** | "Tankless water heater won't ignite" | Should trigger tankless diagnostic flow |
| 15.13 | **Washer diagnostic** | "My washer won't drain" | Should trigger washer not draining flow |
| 15.14 | **Refrigerator diagnostic** | "Fridge not cooling" | Should trigger refrigerator diagnostic flow |
| 15.15 | **Boiler diagnostic** | "Boiler won't fire" | Should trigger boiler no heat flow |
| 15.16 | **Running toilet** | "Toilet keeps running" | Should trigger running toilet flow |
| 15.17 | **Pressure-temp chart** | "What's the R-404A pressure at 40 degrees?" | Should pull from quick reference tables |
| 15.18 | **Box fill calc** | "How do I calculate box fill for 12 AWG?" | Should answer: 2.25 cu in per conductor |
| 15.19 | **Gas pipe sizing** | "What size gas pipe for 200,000 BTU at 50 feet?" | Should give practical answer from reference tables |
| 15.20 | **Voice — new brand** | Say "Navien error E zero zero three" via voice | STT should recognize Navien, lookup should work |

---

## 16. Quick Tools

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 16.1 | **Page loads** | Drawer → Quick Tools | Quick Tools page loads, 5 calculator cards visible |
| 16.2 | **Wire Gauge calculator** | Tap Wire Gauge → enter 40A load | Recommends 8 AWG copper (NEC 310.16, 75°C) |
| 16.3 | **Wire Gauge — edge cases** | Try 15A, 100A | 14 AWG for 15A, 3 AWG for 100A |
| 16.4 | **Voltage Drop calculator** | Enter voltage=240, current=30, distance=100ft, wire=10 AWG | Shows voltage drop and percentage, flags if >3% NEC limit |
| 16.5 | **Ohm's Law calculator** | Enter Voltage=120, Current=15 | Calculates Resistance=8Ω and Power=1800W |
| 16.6 | **Ohm's Law — 2 values** | Enter only 2 of V/I/R | Calculates remaining values correctly |
| 16.7 | **Pipe Sizing calculator** | Enter flow rate in GPM | Recommends nominal pipe diameter |
| 16.8 | **P/T Chart** | Select R-410A → check pressures | Shows correct pressure-temperature chart |
| 16.9 | **P/T Chart — all refrigerants** | Select R-22, R-134a, R-407C | Each shows different pressure values |
| 16.10 | **Reset buttons** | Use each calculator, then tap Reset | All inputs clear, results reset |
| 16.11 | **Modal dismiss** | Open a calculator → tap outside or X | Modal closes cleanly |
| 16.12 | **AI tip card** | Check for AI tip card | Shows card directing user to chat for more help |

---

## 17. LiveKit Voice Agent (If Enabled)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 17.1 | **Token generation** | Verify LiveKit token endpoint works | Token returned with proper room/participant |
| 17.2 | **Connection** | Connect to LiveKit voice session | Voice agent connects, ready for interaction |
| 17.3 | **Knowledge search** | Ask voice agent a technical question | Uses `search_knowledge` tool to query Pinecone |
| 17.4 | **Error code lookup** | Ask voice agent about an error code | Uses `lookup_error_code` function tool |
| 17.5 | **Camera vision** | Ask "what do you see?" in LiveKit session | Uses `look_at_camera` tool |

---

## 18. Admin Endpoints (curl from terminal)

```bash
# Health check
curl https://arrival-backend-81x7.onrender.com/api/health

# Feedback stats
curl "https://arrival-backend-81x7.onrender.com/api/admin/feedback/stats?secret=arr1val-admin-2026"

# List unreviewed feedback
curl "https://arrival-backend-81x7.onrender.com/api/admin/feedback?secret=arr1val-admin-2026&reviewed=false"

# Error codes API
curl "https://arrival-backend-81x7.onrender.com/api/error-codes?brand=rheem&equipment=furnace"

# Test new brands
curl "https://arrival-backend-81x7.onrender.com/api/error-codes?brand=navien&equipment=tankless"
curl "https://arrival-backend-81x7.onrender.com/api/error-codes?brand=lg&equipment=washer"
```

---

# PART 2 — WEBSITE TESTING (arrivalcompany.com)

Test on both desktop browser and mobile browser (Safari on iPhone).

---

## 19. Website — Landing Pages

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 19.1 | **Home page loads** | Visit arrivalcompany.com | Hero section, stats (<3s response, trades, 24/7), feature highlights all render |
| 19.2 | **Navigation links** | Click each nav item (Product, Pricing, For Businesses, Contact, Help) | Each page loads correctly |
| 19.3 | **Product page** | Click Product in nav | Feature showcase loads — voice Q&A, camera analysis, code compliance |
| 19.4 | **Pricing page** | Click Pricing in nav | Individual plans (Free $0, Pro $20) and Business plans ($200/seat, Enterprise) display |
| 19.5 | **Plan toggle** | Toggle between Individual and Business plans on pricing | Cards switch correctly |
| 19.6 | **FAQ section** | Scroll to FAQ on pricing page | 7 FAQ categories expand/collapse correctly |
| 19.7 | **For Businesses page** | Click For Businesses | Hero, Problem/Solution sections, Job Mode, Getting Started render |
| 19.8 | **Contact page** | Click Contact | Form with first name, last name, email displays |
| 19.9 | **Contact form submit** | Fill in contact form → submit | Form submits without errors |
| 19.10 | **Help Center** | Click Help | 6 help article categories display |
| 19.11 | **Help subcategories** | Click each help category (Getting Started, Voice & Camera, Billing, Teams, Job Mode, Troubleshooting) | Each subcategory page loads with articles |
| 19.12 | **Privacy Policy** | Navigate to Privacy Policy | Full privacy policy text renders |
| 19.13 | **Terms of Service** | Navigate to Terms of Service | Full terms text renders |
| 19.14 | **Mobile responsiveness** | View all pages on mobile browser | Hamburger menu works, layouts adapt, no horizontal scroll |
| 19.15 | **Mobile hamburger menu** | Tap hamburger menu on mobile | Menu opens, all nav links work |

---

## 20. Website — Authentication

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 20.1 | **Login page** | Navigate to Login | Email/password form, "Remember me" checkbox, password reset link |
| 20.2 | **Login** | Enter valid credentials → Sign In | Redirects to appropriate dashboard |
| 20.3 | **Login — bad credentials** | Enter wrong password | Shows error message, doesn't crash |
| 20.4 | **Signup page** | Navigate to Sign Up | Form: first name, last name, email, password, plan selection (Pro/Business), terms checkbox |
| 20.5 | **Signup** | Fill in all fields → Sign Up | Account created, confirmation email sent |
| 20.6 | **Password reset request** | Login page → Forgot Password → enter email | Reset email sent (check inbox) |
| 20.7 | **Password reset complete** | Click link in email → enter new password → confirm | Password updated, can login with new password |
| 20.8 | **Auth callback** | Complete OAuth flow | Redirects correctly, session established |

---

## 21. Website — Individual Dashboard

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 21.1 | **Dashboard loads** | Login with individual account | Dashboard page loads with sidebar |
| 21.2 | **Sidebar navigation** | Click each sidebar item | My Documents, Chat History, Saved Answers, Subscription & Billing, Account Settings — all load |
| 21.3 | **My Documents** | Click My Documents | Document list with upload zone, search bar, filter tabs |
| 21.4 | **Upload document** | Drag/drop or click to upload a PDF | Document uploads, appears in list with correct category |
| 21.5 | **Document filters** | Click filter tabs (All, Manufacturer Manuals, Equipment Spec Sheets, Company SOPs, etc.) | Filters work correctly |
| 21.6 | **Document search** | Search by filename | Results filter correctly |
| 21.7 | **Storage indicator** | Check document count | Shows "X / 50 documents used" with plan badge |
| 21.8 | **Chat History** | Click Chat History | Shows table of past conversations |
| 21.9 | **Saved Answers** | Click Saved Answers | Shows table of saved answers |
| 21.10 | **Subscription & Billing** | Click Subscription & Billing | Shows current plan, pricing cards for upgrade, payment method |
| 21.11 | **Update payment** | Click update payment method | Stripe card form appears, can update |
| 21.12 | **Invoice history** | Check invoices section | Shows past invoices |
| 21.13 | **Account Settings** | Click Account Settings | Shows name fields, logout link |
| 21.14 | **Logout** | Click Log Out in sidebar | Returns to login page |

---

## 22. Website — Business Dashboard

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 22.1 | **Dashboard loads** | Login with business account | Business dashboard loads with sidebar |
| 22.2 | **Dashboard home** | Check dashboard home | Welcome message, 4 stats cards (Team members, Documents, Queries this week, Unanswered queries) |
| 22.3 | **Quick actions** | Check quick action buttons | Upload Documents, Invite Team Member buttons present |
| 22.4 | **Top questions** | Check "Top 5 Questions This Week" table | Shows questions, times asked, topics |
| 22.5 | **Recent activity** | Check activity feed | Shows recent team activity |
| 22.6 | **Document Library** | Click Document Library | Shared document library with upload, search, filters |
| 22.7 | **Upload to library** | Upload a document to team library | Document appears in shared library |
| 22.8 | **Team Activity** | Click Team Activity | Activity log showing team member queries and actions |
| 22.9 | **Subscription & Billing** | Click Subscription & Billing | Current plan, seat count, billing info |
| 22.10 | **Manage seats** | Add/remove team seats | Seat count updates, billing adjusts |
| 22.11 | **Account Settings** | Click Account Settings | Admin profile settings |
| 22.12 | **Logout** | Click Log Out | Returns to login page |

---

## Test Execution Tips

### App Testing Order
1. **Start with Section 1 (Auth)** — everything else depends on being signed in
2. **Do Section 2 (Text Chat) thoroughly** — this is the core product
3. **Section 15 is critical** — verifies all the new error codes and diagnostic flows
4. **Section 16 (Quick Tools)** — test each calculator, these are self-contained
5. **Test voice in a quiet room first** (Section 3), then in a noisy environment
6. **Walk through every drawer item** — Saved Answers, Manuals, Quick Tools, History, Settings, Error Codes
7. **Test on cellular data too** — not just WiFi

### Website Testing Order
8. **Section 19 (Landing Pages)** — test on desktop first, then mobile Safari
9. **Section 20 (Auth)** — login, signup, password reset on website
10. **Section 21 (Individual Dashboard)** — documents, history, billing
11. **Section 22 (Business Dashboard)** — if you have a business account to test with

### General
- **Keep Sentry open** in a browser tab during testing — catch any crashes in real time
- **Check backend logs on Render** dashboard for any 500 errors during testing
- **Time responses** — text should be <5s, voice should be <5s end-to-end

---

## Bug Reporting Template

If you find a bug, note:
- **What you did** (exact steps)
- **What happened** (exact error or behavior)
- **What should have happened**
- **Screenshot or screen recording** if possible
- **Check Sentry** for crash reports
- **Check Render logs** for backend errors
