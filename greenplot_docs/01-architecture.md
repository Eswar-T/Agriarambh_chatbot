# 01 — Architecture

**Document type:** Technical architecture · **Last reviewed:** 2026-10-28

## 1. Technology stack

| Layer | Choice | Notes |
|-------|--------|-------|
| App framework | **React Native 0.82.1**, React 19.1.1, TypeScript 5.8 | New Architecture enabled (voice library is a TurboModule-compatible fork) |
| Navigation | React Navigation 7 (native-stack + bottom-tabs) | Role-based tab bars, many nested stacks |
| Server state | **React Context** providers | Auth, Land listings, Leases, Crop cycles, Satellite map |
| Redux | Redux Toolkit — **only** for Labor + Work mock modules | One store (`laborStore`) wrapped in `App.tsx` |
| Backend | **Supabase** — Postgres, Auth, Realtime, Storage, Edge Functions (Deno) | Client in `src/services/supabase.ts` |
| Maps | `@rnmapbox/maps` (Mapbox) | Satellite view, NDVI overlay, plot drawing |
| Payments | Razorpay via two Supabase Edge Functions | Key secret never ships in the app |
| AI | Google Gemini (text + vision) with offline fallback engine | `geminiService.ts`, `aiAssistantService.ts` |
| Voice | `react-native-tts` (patched), `@dev-amirzubair/react-native-voice` | STT/TTS, guarded so a missing native module never crashes |
| i18n | i18next + react-i18next | 6 languages, lazy-loaded bundles |
| OTA updates | Hot Updater (`@hot-updater/*`) on Supabase | Active only when `HOT_UPDATER_BASE_URL` is set |
| Media | `react-native-image-picker`, `react-native-video`, `react-native-nitro-sound` | Uploaded to Supabase Storage |
| Signatures | `react-native-signature-canvas` | Drawn farmer signature on agreements |
| Env config | `react-native-dotenv` (babel plugin) | Values are **inlined into the JS bundle** — see security note in §9 |
| Tests | Jest 29 + react-test-renderer | One smoke test today |

## 2. Repository layout

```
new-Greenplot/
├── App.tsx                  Provider tree + Hot Updater wrap
├── index.js                 RN entry
├── src/
│   ├── navigation/          AppNavigator, tab navigators, one Stack per tab/area
│   ├── screens/             Screen-level UI (feature folders + top-level legacy screens)
│   │   ├── farmerHome/ ownerHome/ hub/ settings/ profileSetup/ satelliteMap/
│   │   ├── farmer/ owner/ leaseClosure/ leases/ aiAssistant/
│   │   └── *.tsx            Lease, auth, soil, weather, mandi etc. (flat legacy files)
│   ├── modules/             Self-contained feature modules (own screens, types, mock data)
│   │   ├── labor/  work/  market/  payments/  attendance/
│   ├── components/          Shared UI: atoms → molecules → organisms, plus feature widgets
│   ├── context/             AuthContext, FarmListingsContext, LeaseContext, CropCycleContext, SatelliteMapContext
│   ├── services/            One *Api.ts per backend resource + external API clients
│   ├── utils/               Pure helpers (geo, cropStages, cropHealth, statusColors, validation…)
│   ├── constants/           leaseTypes, leaseClosure, legalContent, location JSON, hub mock data
│   ├── localization/        i18n.ts + resources/{en,hi,kn,mr,te,ta}.json
│   ├── config/              env.ts (typed ENV + feature flags), mapbox.ts
│   ├── theme/               tokens.ts (colors/spacing/radius/shadow), commonStyles.ts
│   ├── middleware/          permissions/ (role→permission map, used by Labor)
│   ├── hooks/ types/ data/  Small shared hooks, types, location hierarchy
├── supabase/                schema.sql, add_*.sql migrations, functions/ (edge functions)
├── android/ ios/            Native projects (bundle id com.greenplot)
├── scripts/                 backfillProfilesFromAuth.js
├── docs/                    ← you are here
└── .hot-updater/, hot-updater.config.ts   OTA configuration
```

### Screen folder convention (follow this for new screens)

Newer, well-structured features use this shape — copy it:

```
screens/<feature>/
├── <Feature>Screen.tsx          Thin: wires hook → content
├── components/<Feature>Content.tsx   Pure presentational view
├── hooks/use<Feature>.ts        View-model: state, derived data, handlers, navigation
├── styles/<feature>.styles.ts
├── constants/                   Static data and view config
└── index.ts
```
Examples: `farmerHome/`, `ownerHome/`, `hub/`, `settings/`, `profileSetup/`, `satelliteMap/`, `leases/myActiveLeases/`.
Older screens (`LeaseApplicationScreen`, `AgreementDetailsScreen`, …) are single large files; refactor them only when you are already changing them.

## 3. Layering rules

```
Screen / Content component      (renders UI, no data fetching)
        │ uses
Hook  use<Feature>()            (view-model: combines contexts + local state)
        │ uses
Context  (Auth / Lease / FarmListings / CropCycle …)   ← shared, cached, realtime-synced
        │ calls
services/<resource>Api.ts       (snake_case ↔ camelCase mapping, Supabase queries, subscribe())
        │ calls
services/supabase.ts  →  Supabase (Postgres + RLS)
```

**Rules**
1. Screens do not import `supabase` directly. (Existing exceptions are tech debt; do not add more.)
2. Each `*Api.ts` exports an object (`leaseApi`, `landsApi`, …) with async methods and, where it matters, `subscribe(onChange)` returning an unsubscribe function.
3. DB columns are `snake_case`; app types are `camelCase`. Mapping lives in the `*Api.ts` file (`rowToApp`, `toRow`).
4. Pure logic (status labels, stage math, settlement math, area conversion) lives in `utils/` or `constants/` with no React imports, so it is unit-testable.
5. Shared domain types live in `src/types/` (auth, lease, soil) or the module's `types/`.

## 4. Provider tree (`App.tsx`)

```
SafeAreaProvider
 └ I18nextProvider
    └ Redux Provider (laborStore: labor, job, application, attendance, work)
       └ AuthProvider
          └ FarmListingsProvider
             └ LeaseProvider
                └ CropCycleProvider
                   └ SatelliteMapProvider
                      └ AppNavigator
```
Order matters: `LeaseProvider` calls `useAuth()` and `useFarmListings()`. Do not reorder.

`export default` wraps `App` with `HotUpdater.wrap(...)` only when `isHotUpdaterConfigured` is true.

## 5. Dual-mode data (mock vs live) — the most important pattern

`src/config/env.ts` exports `isSupabaseConfigured` (true when `SUPABASE_URL` and `SUPABASE_ANON_KEY` exist). `src/services/supabase.ts` exports `supabase` (a client) or **`null`**.

| Mode | Trigger | Behaviour |
|------|---------|-----------|
| **Mock** | No Supabase keys | Contexts seed in-memory data (e.g. `INITIAL_LISTINGS`), mutate local state, nothing persists; auth uses the in-memory `authService` |
| **Live** | Keys present | Contexts hydrate from Supabase, then **refetch on every Realtime change** so all phones stay in sync |

**How to add a feature in this pattern**
1. Write `services/xApi.ts` (live path, uses `supabase`).
2. In the context/hook: `if (isSupabaseConfigured) { await xApi… } else { /* mutate local state */ }`.
3. Subscribe in a `useEffect`, return the unsubscribe.
4. Never assume `supabase` is non-null outside code gated by `isSupabaseConfigured` (several APIs use a `db()` helper that throws "Supabase not configured").

Other feature flags in `env.ts`: `isNewsConfigured`, `isYoutubeConfigured`, `isWeatherConfigured`, `isGeminiConfigured`, `isRazorpayConfigured`, `isHotUpdaterConfigured`. Each one degrades gracefully (mock news, RSS-only video, offline AI engine, disabled Pay button, no OTA).

## 6. Navigation architecture

```
AppNavigator (RootStack)
 ├─ splash (≥1.2 s, and until saved session restored in live mode)
 ├─ not authenticated → ProfileOnboardingScreen   (one-screen sign-up/login)
 └─ authenticated → MainNavigator, by user.role
       ├─ 'farmer' → FarmerTabNavigator
       │     Home → FarmerHomeStack     My Crops → MyCropsStack     Machinery → MachineryStack
       │     Market → MarketStack       Hub → HubStack
       └─ 'owner'  → OwnerTabNavigator
             Home → OwnerHomeStack      Properties → MyPropertiesStack   Machinery → MachineryStack
             Market → MarketStack       Hub → HubStack
```

* Every stack also hosts `NotificationsCenter` and `Settings` (a nested `SettingsStack`) so the header bell/avatar work from any tab.
* The same screen is registered in several stacks (e.g. `CropDetails`, `CreateWork`, the three lease-closure screens, `SatelliteMap`). Param types are repeated per stack — keep them identical when you change one.
* Cross-tab navigation from a home screen uses `navigation.getParent()?.navigate('<Tab>', params)`.
* **Legacy:** `navigation/AuthStack.tsx` (Splash, LanguageSelection, Welcome, Onboarding, RoleSelection, Login, Register, Otp, ProfileSetup) is **not mounted** by `AppNavigator`. The screens still exist and import its types. See [M01](modules/M01-auth-onboarding.md).

### Back-stack rule for multi-step flows
The lease-closure flow deliberately splits into `ClosureRequested` (step 1) and `LeaseClosure` (step 2 onward) so Back from step 2 returns to step 1 regardless of entry point. Post-submit screens (`LandSubmitted`, `ManagementRequestSubmitted`) must reset the stack so Back does not return to the form. Keep this in any new multi-step flow.

## 7. UI system

| Concern | Location |
|---------|----------|
| Colors, spacing, radius, shadow | `src/theme/tokens.ts` (`colors`, `spacing`, `radius`, `shadow`) — **use tokens, not hex codes** |
| Lease-flow secondary palette | `colors.deepGreen` (`g1…`, `a2…`, `r2…`, `n1…`) in the same file |
| Market module theme | `modules/market/theme/marketTokens.ts` (own tokens) |
| Atoms | `components/atoms` — Button, Text, Card, Badge, Chip, Loader, IconCircle, AppImage |
| Molecules | `components/molecules` — AppHeader, ScreenHeader, SearchBar, EmptyState, FilterChipRow, LabeledTextInput, PhoneNumberInput, StatusActionCard… |
| Organisms | `components/organisms` — AuthLayout, HomeHeader, MapSection, PickerBottomSheet, SignaturePadModal |
| Status colors | `utils/statusColors.ts`, plus `managementRequestStatusMeta.ts` |
| Icons | `react-native-vector-icons` (Ionicons; MaterialCommunityIcons for the tractor) |

`AppHeader` (variant `home` or `default`) is the common top bar: avatar → Settings, bell → Notifications, language button → `LanguagePickerModal`.

## 8. Cross-cutting capabilities

| Capability | Implementation |
|------------|----------------|
| Realtime sync | Supabase Realtime `postgres_changes` channels in `landsApi`, `leaseApi`, `leaseClosureApi`, `cropCycleApi`, `cropActivityApi`, `farmActivityApi`, `notificationsApi`. Channel names must be unique per mount (see the comment in `notificationsApi.subscribe`) |
| File uploads | `services/storageApi.ts` — images via base64 → bytes, video via blob; path convention `<userId>/…`; returns a public URL or `null` |
| Buckets | `land-images`, `post-media`, `avatars`, `stories`, `farm-media` (storage RLS requires first path segment = caller uid) |
| Geo | `utils/geo/*` — polygon area, centroid, acre+gunta formatting, geocoding, location permission; `services/pincodeApi.ts` for PIN → State/District/Taluk |
| Location data | `constants/indiaLocations.json` + `data/locationHierarchy.ts` (35 states, ~10.8k taluks, offline) |
| Role guard | Navigator chooses stack by `user.role`; `middleware/permissions` is a Labor-module permission map only |
| Error handling | Services throw; contexts surface errors. Known weak spots: fire-and-forget writes (see [04](04-roadmap-known-issues.md)) |

## 9. Security architecture — what exists and what is missing

| Area | Today | Required before public launch |
|------|-------|-------------------------------|
| Row Level Security | Enabled on every table; policies in `schema.sql` and later SQL | Re-audit all policies; tighten `lands` read (see [02](02-database-backend.md)) |
| Cross-role writes | RLS silently no-ops a farmer writing to an owner's rows (and vice versa) | Use `SECURITY DEFINER` RPCs/triggers (pattern already used for `toggle_post_like`, `approve_lease_request`) |
| Authentication | Phone-derived synthetic email + **deterministic password** from the phone number, no OTP | Real OTP (Supabase phone auth / MSG91) — see [M01](modules/M01-auth-onboarding.md) |
| API keys in client | `react-native-dotenv` inlines **all** `.env` values into the bundle: Mapbox, Gemini, NewsData, YouTube, OpenWeather, data.gov.in, Razorpay *key id*, Supabase anon key | Restrict keys by app/bundle id; move Gemini (and other paid/quota keys) behind an Edge Function proxy |
| Payment secrets | Razorpay *secret* only in Edge Function env | Keep it that way |
| Signing files | `RELEASE_SIGNING_CREDENTIALS.txt`, `.env.hotupdater`, `*.keystore` are git-ignored | Keep ignored; store in a secret manager |

## 10. Decisions already made (do not reverse without discussion)

| Decision | Reason |
|----------|--------|
| Supabase directly from the app, no custom REST backend | Faster to ship; RLS + RPC give enough control. `Backend_API_Requirements.md` is therefore obsolete |
| Admin actions (verify land, assign farmer, review management requests) live in a separate Admin portal using the service role | A farmer/owner client must never be able to approve itself. Client can only create or withdraw requests |
| Atomic multi-row business actions are RPCs (`approve_lease_request`, `toggle_post_like`, `cast_poll_vote`, `withdraw_own_management_request`, `save_own_profile`) | Avoids race conditions (e.g. two farmers approved for one land) and RLS blocks |
| Payments go through Edge Functions | Key secret and signature verification stay server-side |
| Mock mode is a supported mode, not a hack | Demos and offline development |
