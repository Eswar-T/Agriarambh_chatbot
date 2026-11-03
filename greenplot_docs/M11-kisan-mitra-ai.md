# M11 — Kisan Mitra (AI Assistant)

| | |
|---|---|
| **Status** | 🟡 Partial — chat with voice in/out, photo question, suggestions and in-app actions work. Real AI needs a Gemini key (shipped inside the app); without it a small **offline rule engine** answers in English/Hindi/Kannada |
| **Roles** | Farmer, Owner (route `AIAssistant` in both Home stacks; mic shortcut on both homes) |
| **Code** | `src/screens/AIAssistantScreen.tsx`, `src/screens/aiAssistant/{useKisanMitra.ts,constants.ts,kisanMitra.styles.ts,components/*}`, `src/services/{aiAssistantService,geminiService,voiceService}.ts`, `src/config/env.ts` (`GEMINI_API_KEY`, `GEMINI_MODEL`) |
| **External** | Google Gemini `generateContent` (text + inline-image), model default `gemini-2.5-flash-lite` |
| **Related** | [M07 Crops](M07-crop-management.md) (crop doctor), [M12 Agronomy](M12-agronomy-services.md), [M09 Market](M09-market-intelligence.md) |

## 1. Purpose & scope
A friendly, **voice-first, local-language agriculture helper**: ask about disease, irrigation, fertiliser, mandi prices, schemes, weather, harvest; get a short answer, three follow-up questions, and a button that opens the right tool in the app.

## 2. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M11-F01 | Chat UI: bubbles, typing indicator, welcome state with quick-starts (Diagnose crop, Irrigation, …) | ✅ | `components/*` |
| M11-F02 | **Gemini replies** as compact JSON `{reply, replyEnglish, suggestions[3]}` in the chosen language, last 6 messages as context | ✅ | `geminiService.generateGeminiReply`; robust JSON extraction with regex fallback |
| M11-F03 | **Offline engine**: intent detection (disease, irrigation, fertilizer, market, scheme, harvest, weather, image, generic) with canned answers | ✅ | `aiAssistantService`; used when no key or on API failure |
| M11-F04 | **Photo question**: pick/take a photo → Gemini Vision reply | ✅ | `generateGeminiVisionReply`; offline fallback = generic "image" intent |
| M11-F05 | **Voice input** (speech-to-text, 8 s listen timeout, mic permission handling) | ✅ | `voiceService` |
| M11-F06 | **Voice output** (TTS per reply, reads English or chosen language) | ✅ | `react-native-tts` (patched in `patches/`) |
| M11-F07 | Language picker: **Kannada (default), Hindi, English** | 🟡 | The `Language` type also lists mr, te, bn but those fall back to English; app UI has ta not bn |
| M11-F08 | One-tap **Translate toggle** (show English version of a reply) | ✅ | `textEn` |
| M11-F09 | Thumbs up/down feedback per reply | 🟡 | stored in component state only — not sent anywhere |
| M11-F10 | In-app **action chips**: Buy, Scan leaf, Community, Soil, Market → navigate/open picker | ✅ | `buy` opens Market, `scan` opens picker |
| M11-F11 | Follow-up suggestion chips | ✅ | |
| M11-F12 | Chat history persistence | ⚪ | Cleared on leave |
| M11-F13 | Personalisation from the user's crops, soil, weather, location | ⚪ | Prompt contains none of it |
| M11-F14 | Server-side proxy, rate limiting, usage cost tracking | ⚪ | Key is in the app bundle |
| M11-F15 | Safety layer for pesticide/medical-like advice, disclaimers, human-expert escalation | ⚪ | See §6 |

## 3. How a message is answered
```
user text/voice/photo
  └─ useKisanMitra.send()
       ├─ isGeminiConfigured? ── yes ─► geminiService (text or vision) ─┐
       │                                                 on error/empty ─┤
       └─ no ───────────────────────────────────────────────────────────┴─► aiAssistantService.generateAssistantReply (offline)
  └─ append ChatMessage { text, textEn, suggestions, actions?, verified? } ─► optional TTS
```
System prompt (summary): Indian-agriculture advisor; 2–4 sentences or bullets; specific quantities; avoid jargon; schemes such as PM-KISAN, PMFBY, soil health card; **respond only as JSON**.

## 4. Business rules
1. The assistant must always answer: any AI/network failure falls back to the offline engine (never an empty bubble).
2. Replies are short and actionable; every reply carries three follow-up suggestions.
3. Voice features must never crash the app if a native module is missing; every `voiceService` call is guarded and fails soft with a message.
4. Default language is Kannada (Karnataka-first); the user's choice applies to text, suggestions, STT locale and TTS.
5. Image questions send the picture to Google; the user must be told (privacy text).

## 5. Known issues & tech debt

| ID | Issue | Impact | Fix |
|----|-------|--------|-----|
| SEC-2 | `GEMINI_API_KEY` is inlined in the JS bundle | Key theft, quota abuse | Edge Function proxy with per-user rate limit |
| M11-D1 | Offline replies carry `verified: true` ("verified" badge) although they are canned text; the disease answer always says "Early Blight" | **Misleading** advice | Remove badge from canned replies; make offline disease answer generic ("send a photo / describe symptoms") |
| M11-D2 | No grounding: prompt has no location, crop, soil or weather | Generic advice | Context injection (M11-T3) |
| M11-D3 | No guardrails for pesticide names/doses | Safety/legal | Policy + prompt rules + disclaimer (M11-T4) |
| M11-D4 | Feedback buttons not persisted | No quality signal | `ai_feedback` table |
| M11-D5 | `Language` type and UI language list disagree with the app (mr/te/bn/ta) | Confusing | Align with [M15](M15-settings-localization-legal.md) |
| M11-D6 | `generateGeminiReply` swallows errors silently (returns null) | Hard to debug | Log to analytics |
| M11-D7 | Land-record verification ([M03](M03-land-listing-verification.md)) reuses the same key and endpoint | Same risk | Same proxy |

## 6. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Remove misleading `verified` badge and fix the canned disease answer | M11-T1 | P0 | S | No canned reply claims to be verified |
| 1 | **Edge Function `ai-chat`** (JWT-protected): calls Gemini server-side, applies per-user daily limit, logs token usage; app no longer holds the key | M11-T2 | P0 | M | Key absent from bundle; limit enforced; offline fallback still works |
| 2 | Context injection: user's state/district, active crops and stage, today's weather, soil summary (opt-in) | M11-T3 | P1 | M | Replies mention the user's crop/stage when relevant |
| 2 | Safety prompt + disclaimers: no chemical dosing without label guidance; "consult KVK/agri officer" for severe cases; block non-agri topics politely | M11-T4 | P1 | M | Red-team list of 30 prompts reviewed by an agronomist |
| 2 | Persist chats (`ai_conversations`, `ai_messages`) with delete option; thumbs feedback table | M11-T5 | P1 | M | History survives restart; user can clear it |
| 2 | Language parity: add Marathi, Telugu, Tamil to picker and offline fallbacks (or use Gemini only for those) | M11-T6 | P1 | M | Picker matches UI languages |
| 2 | **Crop Doctor** mode: guided photo capture (leaf, close-up), structured result (likely issue, confidence, safe steps), "Save to observations" ([M07](M07-crop-management.md)) | M11-T7 | P1 | L | Result stored with photo and stage |
| 3 | Voice-only hands-free mode with auto-read of replies | M11-T8 | P2 | M | |
| 3 | Retrieval over a curated knowledge base (KVK advisories, scheme PDFs) with citations | M11-T9 | P2 | XL | Answers show source |
| 3 | Proactive tips on Home from weather + crop stage | M11-T10 | P2 | M | [M02](M02-dashboards.md) M02-T6 |

## 7. Test checklist
- [ ] No key: ask in each of 3 languages → offline answer, suggestions, actions
- [ ] Key present: answer in Kannada; Translate toggle shows English
- [ ] Airplane mode mid-request → offline fallback, no crash
- [ ] Photo of a leaf → vision reply or friendly fallback; photo of a non-plant → polite response
- [ ] Mic denied → clear message; STT unavailable device → message, typing still works
- [ ] TTS on/off; switching language changes voice
- [ ] Action chips open the correct screens for both roles

## 8. Definition of Done
Standard DoD plus: agronomist review of prompts/answers, abuse/rate-limit test, and cost per conversation estimated.
