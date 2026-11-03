# 04 — Roadmap, Risks & Known Issues

**Document type:** Delivery plan · **Last reviewed:** 2026-10-28
**How to read:** Priority **P0** = launch blocker · **P1** = soon after · **P2** = later. Size **S** ≤ 1 d · **M** 2–4 d · **L** 1–2 wk · **XL** > 2 wk (one developer). Sizes are planning estimates, to be confirmed in sprint planning.

---

## 1. Where we are

| Module | Status | One-line truth |
|--------|:------:|----------------|
| M01 Auth & Onboarding | 🟡 | Works, **insecure** (no real OTP) |
| M02 Dashboards | 🟡 | Real lease/crop data mixed with mock ticker/tasks; several tiles hidden |
| M03 Land Listing & Verification | 🟡 | Add Land + AI document check work; admin verification is external; world-readable `lands` |
| M04 Leasing & E-Agreements | 🟡 | Downstream flow complete (atomic approval, sign + deposit); **offer creation and land discovery have no entry point**; deposit not enforced server-side |
| M05 Lease Closure | ✅ | Complete 6-step workflow |
| M06 Farm Management | ✅ | Farmer side complete; depends on Admin portal |
| M07 Crop Management | ✅ | Plan → schedule → observations → harvest done |
| M08 Labor & Work | 🧪🚧 | UI done on mock data; entry points disabled; **Create Work shows "success" but saves nothing** |
| M09 Market Intelligence | 🟡 | Mandi data live; 7 screens are placeholders; cold storage mock |
| M10 Community Hub | 🟡 | Posts/likes/comments/polls/stories live; **no report/block (store risk)**; news, techniques, rewards mock |
| M11 Kisan Mitra | 🟡 | Gemini AI live with key; photo question works; key is in the app; canned replies wrongly marked "verified" |
| M12 Weather/Soil/Satellite | 🟡 | Weather & soil live; NDVI layer is a mock URL |
| M13 Payments | 🟡 | Edge functions built; wired to agreement screen + labor summary only |
| M14 Notifications | 🟡 | Read + realtime done; no push; producers not documented |
| M15 Settings / i18n / Legal | 🟡 | Works; only 32 of 244 screens/components are translated; 3 dead Settings rows |
| M16 Machinery | ⚪ | Placeholder tab |

---

## 2. Release blockers (P0) — do these before a public launch

| ID | Item | Why | Size | Module | Acceptance |
|----|------|-----|:----:|--------|-----------|
| **SEC-1** | Replace phone-derived password login with **real OTP** (Supabase phone auth + SMS provider, or email OTP for v1) | Today the password is `GreenPlot-<phone>-v1`, computed in the app. Anyone who knows a phone number can sign in as that person and see/modify their leases and land | L | M01 | Sign-in requires a one-time code; no password derivable from public data; existing users migrated |
| **DB-1** | Export live schema; commit as ordered migrations; recreate DB from scratch in staging | Repo cannot rebuild the database ([02](02-database-backend.md) warning) | M | All | Fresh Supabase project + migrations + seed runs the app end to end |
| **SEC-2** | Protect third-party keys | `react-native-dotenv` bundles every key into the app; Gemini/NewsData/YouTube/OpenWeather keys can be extracted and abused | M | M11, M12, M09 | Keys restricted by bundle id/IP where supported; Gemini moved behind an Edge Function with per-user rate limit |
| **SEC-3** | Tighten `lease_agreements` update policy | Policy lets *either* party update *any* column, so a farmer could mark `owner_signed = true` | S | M04 | Updates only through RPCs/column-restricted policy; signing sets only the caller's own flag |
| **SEC-4** | Stop exposing unapproved/private lands | `lands` is `select using (true)`; a dormant "all available lands" screen and a Security-Definer-view warning exist | M | M03, M06 | Marketplace reads come from a view/policy that returns only approved, public listings; owners still see their own |
| **SEC-5** | Audit every cross-role write | RLS silently no-ops cross-role writes (e.g. farmer updating owner rows) — features "succeed" but do nothing | M | All | Table of every write path + who performs it; each cross-role write is an RPC/trigger |
| **BUG-1** | `updateListing()` is fire-and-forget | UI says "saved" even when the write failed | S | M03 | `updateListing` returns a promise; UI awaits and shows the real error |
| **REL-1** | iOS app identity and store readiness | Bundle id is the template default; versions reset; privacy declarations unreviewed | M | — | Real bundle id, signing, `PrivacyInfo.xcprivacy` reviewed, TestFlight build installs |
| **QA-1** | Baseline automated tests | Only one smoke test exists | L | — | Unit tests for pure logic (settlement math, crop stages, area formatting, status meta); API-mapper tests; CI runs `tsc`, lint, jest on every PR |
| **LEASE-1** | Product decision: retire the lease marketplace or reconnect it | Offer creation and land discovery are unreachable; copy collides with Farm Management | S (decision) | M04, M06 | Decision recorded in [M04](modules/M04-leasing.md); dead routes removed or reconnected |
| **PAY-0** | Enforce the security deposit **server-side** and remove the mock ₹5,000 fallback | Lease can be activated by a client call without paying; fallback charges a fake amount | M | M04, M13 | Activation only through an RPC that requires a `paid` row; `securityDeposit` mandatory |
| **PAY-3** | Razorpay webhook + reconciliation | App crash after payment leaves money taken, order `created` | M | M13 | Killed-app payment still ends `paid` |
| **UGC-1** | Report / block / moderate Hub content | Store policies require it for user-generated content | L | M10 | Report from any post/comment/story; Admin queue; blocked users hidden |
| **STORE-1** | Account deletion, public policy URLs, dead Settings rows removed | Store submission requirements | M | M01, M15 | In-app deletion works; URLs live; no inert rows |
| **AI-1** | Remove misleading "verified" badge and fixed "Early Blight" answer from offline AI; proxy Gemini | Misleading agronomy advice | S + M | M11 | No canned reply claims verification; key not in bundle |
| **DOC-1** | Replace legacy docs | `README.md`, `STRUCTURE.md`, `NAVIGATION.md`, `BUILD_PLAN.md`, `Backend_API_Requirements.md` mislead new developers | S | — | Root README points to `docs/`; obsolete files deleted or archived |
| **DOC-2** | Update `.env.example` | Lists 7 of ~17 variables | S | — | Every key in `src/config/env.ts` present with comments |

---

## 3. Phased plan (suggested sequencing)

### Phase 1 — Harden (≈ 5–7 weeks with 2–3 developers; sizes are planning estimates)
Goal: safe to put in front of real users.
`SEC-1`, `DB-1`, `LEASE-1`, `PAY-0`, `PAY-3`, `SEC-3`, `SEC-4`, `SEC-5`, `BUG-1`, `SEC-2` / `AI-1`, `UGC-1`, `STORE-1`, `REL-1`, `QA-1` (CI + first tests), `DOC-1`, `DOC-2`.
*Exit criteria:* a stranger who knows only your phone number cannot see or change your data; the DB can be rebuilt from the repo; Android and iOS release builds pass the smoke test (§6).

### Phase 2 — Finish the core promise (≈ 4–6 weeks)
Goal: every visible button works.

| ID | Item | Priority | Size | Module |
|----|------|:--------:|:----:|--------|
| NOT-1 | Push notifications (FCM + APNs) with DB-trigger producers documented and committed | P1 | L | M14 |
| PAY-1 | Wire Razorpay to lease rent due dates (`leases.rent`, `next_payment`) with receipt and history | P1 | L | M13, M04 |
| LAB-1 | Decide Labor scope; if yes, move Labor Connect + Work Jobs from mock to Supabase tables (`labor_jobs`, `job_applications`, attendance) and re-enable entry points | P1 | XL | M08 |
| MKT-1 | Replace placeholder Market screens in priority order: Price Forecast, Find Buyers, MSP/FRP, Oversupply alert | P1 | XL | M09 |
| MKT-2 | Cold-storage booking backed by real `cold_storages` / `storage_bookings` tables | P2 | L | M09 |
| SEC-6 | Move signatures, closure-handover photos and ownership documents to **private** buckets with signed URLs | P1 | M | M04, M05, M03 |
| DASH-1 | Remove or wire the remaining mock tiles on dashboards (tasks due, market ticker fallback, crop-health sample) | P1 | M | M02 |
| I18N-1 | Translation sprint: key all visible strings, translate hi + kn first, CI check; align AI language list with UI list | P1 | XL | M15, M11 |
| OWN-1 | Re-enable Owner "Budget & Approvals" and "Work Report" on real data | P2 | L | M08 |
| HUB-1 | Move Hub News/Techniques/Questions/Rewards from mock to real sources | P2 | L | M10 |

### Phase 3 — Grow (after launch stabilises)
| ID | Item | Priority | Size |
|----|------|:--------:|:----:|
| MCH-1 | Machinery rental (list, request, approve — mirror of land leasing) | P2 | XL |
| CRD-1 | Crop Doctor (photo disease diagnosis) — design exists in `docs/crop_doctor_figma.html`; Gemini vision path exists in M11 | P2 | L |
| SAT-1 | Real NDVI (Sentinel Hub / Planet) instead of mock tile URL; per-farm time-lapse | P2 | XL |
| LAND-1 | Replace document-AI verification with a land-records provider (APISetu / aggregator) behind the existing `LandVerifier` interface | P2 | L |
| ROLE-1 | Add Laborer role (schema + onboarding + permissions) | P2 | L |
| ANL-1 | Analytics + crash reporting (none today) | P1 | M |
| PERF-1 | Pagination for `lands` (currently capped at 500 rows) and lease lists | P2 | M |

---

## 4. Known issues register

| ID | Area | Issue | Impact | Planned fix |
|----|------|-------|--------|-------------|
| KI-1 | M01 | Deterministic password; no OTP | Account takeover | SEC-1 |
| KI-2 | DB | RLS silently blocks cross-role writes | "Saved" but nothing happens | SEC-5 (use SECURITY DEFINER RPC/trigger) |
| KI-3 | M03 | `updateListing()` does not await or report failure | False success message | BUG-1 |
| KI-4 | M03/M06 | `lands` readable by all; dormant `AllAvailableLandsScreen`; Security Definer View advisory | Unapproved lands may be visible | SEC-4 |
| KI-5 | M04 | `lease_agreements` update policy too broad | Signature flags can be forged | SEC-3 |
| KI-6 | DB | Many tables/RPCs/views not in repo; referenced migration files missing | Cannot rebuild DB | DB-1 |
| KI-7 | M08 | `WorkListScreen` hard-codes farmer id `'F001'`; Labor/Work use Redux mock APIs with `setTimeout` delays | Not real data | LAB-1 |
| KI-8 | M08 | Owner Home "Labor" and "Work report" show a "coming soon" alert; Farmer Home Hire Labor / Create Work shortcuts commented out | Dead ends | LAB-1 / OWN-1 |
| KI-9 | M09 | `FindBuyers`, `PriceForecast`, `MspFrp`, `OversupplyAlert`, `AIInsight`, `FilterSearch`, `EmptyState` render a "feature unavailable" screen | Visible tabs with no content | MKT-1 |
| KI-10 | M09 | Cold-storage list/booking uses `MOCK_COLD_STORAGES`; booking is not persisted | Fake confirmation | MKT-2 |
| KI-11 | M12 | `satelliteMapService` NDVI URL is a mock WMS endpoint | Overlay shows nothing real | SAT-1 |
| KI-12 | M02 | Farmer Home "Tasks due" tile shows "Soon" (disabled); tasks, crop-health and browse-by-crop sections commented out | Incomplete dashboard | DASH-1 |
| KI-13 | M15/M11 | Translation resources hold ~59 strings (en, kn) / ~40 (hi, mr, ta, te); AI assistant languages (en, hi, kn + type allows mr, te, **bn**) differ from UI languages (en, hi, kn, mr, te, **ta**) | Untranslated text; mismatch | I18N-1 |
| KI-14 | M14 | The only code that creates `notifications` rows is `leaseClosureApi` (client inserts a row **for the other party**), and it ignores the result. The repo's policy `notif own` only allows `user_id = auth.uid()`, so this is a cross-role write that RLS will silently block unless the live DB differs. Lease request/approval/sign events create no notification in the repo. Rows are never marked read. No push | Users may miss closure notices; cannot reproduce or extend events | NOT-1, SEC-5 |
| KI-15 | M13 | `payments` table and `supabase/functions/README.md` are missing from the repo | Hard to deploy payments | DB-1, PAY-1 |
| KI-16 | Build | iOS bundle id is the RN template default | Cannot ship to App Store | REL-1 |
| KI-17 | Auth | `navigation/AuthStack.tsx` and its screens (Login, Otp, Register, Welcome, Onboarding, RoleSelection, ProfileSetup) are unused at runtime; `authService` is a mock registry | Dead code confuses new developers; will be reused by SEC-1 | SEC-1 |
| KI-18 | Tests | One smoke test; no CI workflows (`.github/workflows` is empty) | Regressions undetected | QA-1 |
| KI-19 | Perf | `lands`/`lease_offers` fetched with `limit(500)` and filtered on the device | Slow and incomplete at scale | PERF-1 |
| KI-20 | Docs | Legacy docs are wrong ([README](README.md) §3) | New-developer confusion | DOC-1 |
| KI-21 | M04/M05/M03 | Most live writes in `LeaseContext` and `FarmListingsContext` are `.then(refetch).catch(() => {})`; Supabase returns `{ error }` rather than throwing, so failures are invisible | False success, lost data | Definition of Done rule "writes are awaited" + SEC-5 |
| KI-22 | M08 | Create Work stores the job in an in-memory array and shows "Job created successfully!" | Data loss, misleading | LAB-1 or hide the entry |
| KI-23 | M05 | `leases.status = 'closed'` but the repo enum `lease_status` has no `closed` | Finalise may fail silently | M05-T1 |
| KI-24 | M04/M13 | Mock deposit ₹5,000 fallback; deposit not enforced server-side | Money / integrity | PAY-0 |
| KI-25 | M03 | Taluk, hobli, village, irrigation/pesticide schedule, expected harvest are collected but not persisted | Data vanishes after restart | M03-T2 |
| KI-26 | M11 | Canned AI replies carry a "verified" badge; disease answer is always "Early Blight" | Misleading | AI-1 |
| KI-27 | M10 | No report/block/moderation of user content | Store rejection risk | UGC-1 |
| KI-28 | M09 | `console.log` of full API response in `mandiApi.fetchPrices` | Log noise, perf | M09-T0 |
| KI-29 | M14 | Notification cards have no tap action; read state never updated; no badge | Dead UI | M14-T3 |
| KI-30 | M15 | Only 32 of 244 UI files use translations; Settings rows Notifications / Help & Support / Consent logs inert | Mostly-English app | I18N-1, STORE-1 |
| KI-31 | M04 | Lease education screens duplicate lease-type content with different ids | Inconsistent copy | M04-T6 |
| KI-32 | Auth | Temporary `[LOGIN]` debug logging in onboarding | Log noise | M01-T5 |

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|-----------|
| Auth weakness exploited after launch | High | Severe | Treat SEC-1 as the first Phase-1 task; do not market publicly before it ships |
| Admin portal and app drift (shared tables) | Medium | High | Put the shared contract (statuses, RPC names, view) in [02](02-database-backend.md) and review both repos on any change |
| Third-party API limits (data.gov.in sample key, free NewsData 200/day, Gemini free tier) | High | Medium | Server-side caching in Edge Functions; paid tiers when traffic grows |
| Store review failures (permissions, privacy, account deletion, UGC moderation) | Medium | High | Add account-deletion flow and Hub content reporting/moderation before submission; complete privacy forms |
| One-person knowledge silos (large screens: `ManagedFarmDashboardScreen` 1,991 lines, `AddFarmScreen` 1,650, `MyCropsScreen` 1,408) | High | Medium | Split into hook + content components when next touched (see [01 §2](01-architecture.md)) |
| Data loss from fire-and-forget writes | Medium | Medium | Definition of Done requires awaited writes ([05 §5](05-documentation-standards.md)) |

> **Compliance gaps to plan for (searched the code; none found):** account/data deletion, content reporting & moderation for Hub posts and stories, consent log for terms version changes, handling of Aadhaar-like or land-record documents uploaded for verification (retention and access).

---

## 6. Release smoke test

Run on a real device, once as **Farmer** and once as **Owner** (use two phones if possible).

| # | Step | Expected |
|---|------|----------|
| 1 | Fresh install, choose language, sign up | Lands on the correct role dashboard |
| 2 | Kill and reopen app | Still signed in; no flash of onboarding |
| 3 | Owner: add land with photo, drawn plot, PIN auto-fill | "Land submitted"; back does not return to the form |
| 4 | Owner: add a lease offer | Offer visible to the farmer within seconds |
| 5 | Farmer: apply for lease | Owner sees the request live |
| 6 | Owner: approve | Farmer sees "sign agreement"; second applicant is auto-rejected; land locked |
| 7 | Farmer: sign with drawn signature | Agreement active; lease appears in both apps |
| 8 | Farmer: select crop → crop plan → confirm | Activities generated; stage shown |
| 9 | Farmer: complete an activity with a photo, record harvest | Timeline updated; owner can see progress |
| 10 | Farmer: request lease closure → owner responds → settlement → handover | Status follows the 6 steps; both see the same state |
| 11 | Switch language to Kannada/Hindi | Visible screens translate |
| 12 | Kisan Mitra: ask a question by text and voice | Reply in the chosen language |
| 13 | Mandi prices for a crop in the user's state | Real rows or a clear empty state |
| 14 | Hub: post a photo, like, comment, vote in a poll | Persists after restart |
| 15 | Logout | Returns to onboarding quickly (never hangs) |
