# 02 — Database & Backend

**Document type:** Data & backend reference · **Last reviewed:** 2026-10-28
**Backend:** Supabase (Postgres 15+, Auth, Realtime, Storage, Edge Functions)

> ## ⚠ Schema drift — read this first
> `supabase/schema.sql` describes only the **first generation** of the database. The app code reads and writes **many more tables, views and functions** whose SQL is **not in this repository** (see §4). Several code comments reference migration files (`add_farm_management_requests.sql`, `add_farm_management_verification.sql`, `add_farm_management_farmer_view.sql`, `add_management_request_details.sql`) that do not exist here.
> **Consequence:** a new developer cannot recreate the database from the repo, and a new Supabase project would not run the app.
> **Action (task DB-1, P0):** export the live schema (`supabase db dump --schema public`) and commit it as numbered migrations. Until then, treat this document's §4 as the *inferred* contract.

---

## 1. Connection and modes

| Item | Value |
|------|-------|
| Client | `src/services/supabase.ts` — created only if `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set |
| Session storage | AsyncStorage, auto-refresh, `persistSession: true` |
| No keys | `supabase === null`; app runs in mock mode (see [01 §5](01-architecture.md)) |
| Setup guide | `supabase/README.md` (project creation, run `schema.sql`, add keys) |

## 2. Entity overview

```
auth.users ─1:1─ profiles ─┬─< lands ─┬─< lease_offers ─< lease_requests ─1:1─ lease_agreements ─> leases ─< lease_closures ─< lease_closure_history
                           │          ├─< management_requests            (Farm Management)
                           │          └─< crop_cycles ─┬─< crop_activities   (free-text log)
                           │                           ├─< farm_activities ─< farm_observations   (scheduled plan)
                           │                           └─< harvest_records
                           ├─< posts ─┬─< post_likes / post_saves / comments / poll_votes
                           ├─< stories
                           ├─< labor_jobs ─< job_applications          (defined, app uses mock)
                           ├─< notifications · rewards · soil_tests · crop_records(legacy)
                           └─< payments                                  (edge functions)
Reference data: crops, crop_guidance
View: lands_available_for_management
```

## 3. Tables defined in `supabase/schema.sql` and `add_*.sql` (in repo)

| Table | Purpose | Key columns | RLS summary |
|-------|---------|-------------|-------------|
| `profiles` | 1:1 with `auth.users`; app identity | `id`, `name`, `phone`, `role` (`farmer`/`owner`), `location`, `district`, `state`, `has_whatsapp`, `avatar_url`, `accepted_terms_and_policies` (from `add_terms_acceptance.sql`) | read: anyone; insert/update: own row only. Written through RPC `save_own_profile` |
| `lands` | A property listing | `owner_id`, `title`, `soil_type`, `acres`, `location/district/state`, `tenure`, `price_per_year`, `lease_type`, `status` (`active/leased/inactive`), `geo` (GeoJSON), `survey_number`, `verified`, `verified_owner`, `water_source` (`add_water_source.sql`) | **read: everyone (`using (true)`)**; write: owner only |
| `lease_offers` | One or more offers per land | `land_id`, `owner_id`, `type_id` (enum), `terms` jsonb, `tenure`, `available_from` | read: everyone; write: owner |
| `lease_requests` | Farmer applies to an offer | `land_id`, `offer_id`, `farmer_id`, `owner_id`, `type_id`, `terms_summary`, names, `status` (`pending/accepted/rejected`) | read/update: the two parties; insert: farmer |
| `lease_agreements` | Created on approval; two-party e-sign | `request_id`, `full_terms` jsonb, `owner_signed`, `farmer_signed`, `status` (`awaiting/active/cancelled`), `farmer_signature_url`, `farmer_signed_at` (`add_lease_signatures.sql`) | read/write: the two parties (**either party can update any column — hardening item, see [04](04-roadmap-known-issues.md)**) |
| `leases` | Active lease record | `land_id`, `farmer_id`, `owner_id`, `status` (`pending/active/expired/cancelled`), `start_date`, `end_date`, `rent`, `next_payment`, denormalised titles/names | read/write: the two parties |
| `posts` | Community posts | `author_id`, `category`, `title`, `text`, `media_type` (incl. `audio`, `blog`), `media_urls[]`, `likes_count`, `comments_count`, `earned_label` | read: all; write: author |
| `post_likes`, `post_saves` | Reactions | `(post_id, user_id)` | read: all; write: own |
| `comments` | Post comments | `post_id`, `author_id`, `text` | read: all; insert: own. Trigger keeps `posts.comments_count` in sync |
| `stories` | 24-hour media | `author_id`, `media_type`, `media_url`, `media_path`, `expires_at` | read: unexpired; insert/delete: own |
| `labor_jobs`, `job_applications` | Labor marketplace | see schema | read: all; write: owner of the row. **App does not use these yet (mock)** |
| `crop_records` | Legacy crop table | `farmer_id`, `land_id`, `crop`, `stage`, `health_pct` | own — superseded by `crop_cycles` |
| `soil_tests` | Saved soil lookups | `user_id`, `lat`, `lon`, `result` jsonb | own — not wired in app |
| `notifications` | In-app notifications | `user_id`, `type`, `title`, `body`, `read` | own |
| `rewards` | Hub gamification | `coins`, `streak_days`, `level` | own — UI uses mock data |

**Functions and triggers in repo**

| Name | Type | Purpose |
|------|------|---------|
| `handle_new_user()` + trigger `on_auth_user_created` | trigger on `auth.users` | Auto-creates the `profiles` row from signup metadata |
| `save_own_profile(...)` | RPC (security definer) | Upserts the caller's own profile (updated by `add_avatar_url_to_save_profile.sql`, `add_terms_acceptance.sql`) |
| `toggle_post_like(p_post_id)` | RPC (security definer) | Atomic like/unlike + counter |
| `handle_comment_count()` + 2 triggers | trigger | Keeps `comments_count` correct |
| `repair_missing_profiles.sql` | one-off script | Backfills profiles for orphan auth users |

**Realtime publication:** `lease_offers`, `lease_requests`, `lease_agreements`, `leases` are added in `schema.sql`. `lands`, closures, crop and notification tables are subscribed to by the app, so they must also be in the publication on the live DB.

## 4. Objects used by the app but **not defined in the repo** (inferred contract)

| Object | Used by | Inferred columns / behaviour |
|--------|---------|------------------------------|
| `lands` extra columns | `landsApi` | `owner_name`, `self_farmed`, `crops` (text[]), `media` (text[]), `current_crop`, `last_year_*`, **`verification_status`**, **`management_status`**, **`assigned_farmer_id`** (admin-written only) |
| View `lands_available_for_management` | `landsApi.fetchAvailableForManagement` | `lands` where `verification_status = 'APPROVED'` and `management_status = 'AVAILABLE_FOR_MANAGEMENT'` |
| `management_requests` | `managementRequestsApi` | `land_id`, `farmer_id`, `owner_id`, `status` (`PENDING_REVIEW/UNDER_REVIEW/SHORTLISTED/APPROVED/REJECTED/WITHDRAWN/CANCELLED`), `preferred_crop`, `farming_experience`, `previous_crops`, `preferred_start_date`, `expected_duration`, `farmer_notes`, `reviewed_at`, `reviewed_by`, `admin_notes` |
| RPC `withdraw_own_management_request` | same | Only way a farmer can change a request's status (to `WITHDRAWN`) |
| `crops` | `cropsApi` | `id`, `name`, `description`, `suitable_soils`, `typical_duration_days`, `water_requirement` (public read) |
| `crop_guidance` | `cropGuidanceApi` | Per crop+stage master tasks: `crop_id`, `crop_stage`, `activity_type`, `title`, `description`, `priority`, `recommended_day` |
| `crop_cycles` | `cropCycleApi` | `farmer_id`, `owner_id`, `land_id`, `lease_id`, `crop_id`, `crop_name`, `variety`, `plot_name`, `area_acres`, `landlord`, `status` (`active/harvest_ready/harvested/completed/fallow`), `current_stage`, `sown_date`, `planned_planting_date`, `expected_harvest_date`, `health_status`, `health_note` |
| `crop_activities` | `cropActivityApi` | Free-text log: `crop_cycle_id`, `type`, `title`, `note`, `activity_date` |
| `farm_activities` | `farmActivityApi` | Scheduled tasks generated from `crop_guidance`: `activity_type`, `title`, `description`, `priority`, `scheduled_date`, `status` (`PENDING/IN_PROGRESS/COMPLETED/SKIPPED/CANCELLED`), `completed_date`, `farmer_notes`, `input` |
| `farm_observations` | `farmObservationApi` | `activity_id`, `crop_stage`, `observation`, `photo_url` |
| `harvest_records` | `harvestApi` | `crop_cycle_id`, `harvest_date`, `quantity`, `unit`, `harvested_area`, `quality_grade`, `photo_urls`, `notes` (append-only) |
| `lease_closures` | `leaseClosureApi` | All columns of the `LeaseClosure` type in `src/types/lease.ts` (see [M05](modules/M05-lease-closure.md)) |
| `lease_closure_history` | same | Audit trail: `closure_id`, `action`, `performed_by`, `user_role`, `details` |
| `poll_votes` + RPC `cast_poll_vote` | `communityApi` | One vote per user per poll post |
| RPC `approve_lease_request` | `leaseApi.approveRequest` | **Atomic:** lock the land, approve one request, auto-reject other pending requests on the same land, create the agreement. Fails if the land was already taken |
| `payments` | Edge functions | `razorpay_order_id`, `razorpay_payment_id`, `status` (`created`→`paid`), `paid_at`, payer, `context`, `context_id`, `payee_id`, amount |
| Notification producers | `notifications` rows | The app **reads** this table (`notificationsApi`) and only `leaseClosureApi` **inserts** rows (for the *other* party, result unchecked). With the repo's `notif own` policy that insert is blocked by RLS. Check the live DB for triggers/policies that make it work, and move producers to DB triggers (task NOT-1) |

## 5. Row Level Security principles

1. **Every table has RLS on.** Policies are the security boundary because the anon key is public.
2. **Own-row pattern:** `auth.uid() = <owner column>`.
3. **Two-party pattern:** `auth.uid() in (farmer_id, owner_id)` for leases, requests, agreements, closures.
4. **RLS fails silently.** A blocked update returns 0 rows and *no error*. Symptoms: "saved" message but nothing changed. Root causes seen: farmer updating an owner's row, owner updating a farmer's row. **Fix pattern:** a `SECURITY DEFINER` RPC or trigger (as done for `toggle_post_like`, `approve_lease_request`, `handle_comment_count`).
5. **Admin writes** use the service role from the Admin portal and bypass RLS. The mobile client must never be able to write `verification_status`, `management_status`, `assigned_farmer_id`, or set a management request to anything except `PENDING_REVIEW` (create) / `WITHDRAWN` (RPC).
6. **Open issue:** `lands` is world-readable (`using (true)`), so unapproved or private listings are visible to all signed-in users and the client filters on top. Move filtering into views/policies (see [04](04-roadmap-known-issues.md), item SEC-4).

## 6. Storage

| Bucket | Public read | Used for | Path convention |
|--------|:-----------:|----------|-----------------|
| `land-images` | ✔ | Land photos/videos (Add Land) | `<userId>/…` |
| `farm-media` | ✔ | Crop observation / harvest / closure-handover photos | `<userId>/…` |
| `post-media` | ✔ | Hub post media (image, video, audio) | `<userId>/…` |
| `avatars` | ✔ | Profile photos | `<userId>/…` |
| `stories` | ✔ | 24-hour stories | `<userId>/…` |
| `signatures` | ✔ | Farmer's drawn agreement signature (`add_lease_signatures.sql`) | `<userId>/…` |

Storage RLS (`add_stories_feature.sql`, `add_lease_signatures.sql`): select allowed for listed buckets; **insert/delete only when the first folder segment equals the caller's uid**. Code that uploads must follow `<userId>/<file>` or the upload is silently denied. `storageApi` defaults to `farm-media` when no bucket is passed (crop observations, harvest photos).
Signatures are stored as image URLs (`lease_agreements.farmer_signature_url`). Note the buckets are **public-read**, so signature, land and handover photo URLs are reachable by anyone who has the link — acceptable for land photos, review for signatures and handover photos (item SEC-6 in [04](04-roadmap-known-issues.md)).

## 7. Edge Functions (`supabase/functions`)

| Function | Input | Behaviour | Secrets |
|----------|-------|-----------|---------|
| `create-razorpay-order` | `{ amountPaise, context ('lease_rent'\|'labor_wage'), contextId?, payeeId? }` + user JWT | Identifies payer from JWT, creates a Razorpay order, inserts a `payments` row (`created`), returns `{ orderId, amount, currency, keyId }` | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` |
| `verify-razorpay-payment` | `{ razorpay_order_id, razorpay_payment_id, razorpay_signature }` | Verifies HMAC signature server-side, marks the `payments` row `paid` | same |
| `_shared/cors.ts` | — | CORS headers | — |

Deploy: `supabase functions deploy <name>` and `supabase secrets set …`. The client must attach the **user's JWT** explicitly (`paymentsApi.authHeader`) — `functions.invoke` does not do it automatically. `supabase/functions/README.md` is referenced by code but missing.

## 8. External APIs (no backend of ours)

| API | Client | Key | Used for |
|-----|--------|-----|----------|
| data.gov.in Agmarknet (resource `9ef84268-…`) | `mandiApi.ts` | `DATA_GOV_API_KEY` | Mandi prices |
| OpenWeather (current + forecast) | `weatherApi.ts` | `WEATHER_API_KEY` | Weather |
| NewsData.io | `newsApi.ts` | `NEWS_API_KEY` | News & schemes (falls back to mock) |
| YouTube RSS + Data API v3 | `videosApi.ts` | `YOUTUBE_API_KEY` (optional) | Videos |
| SoilGrids (ISRIC) | `soilAdvisoryApi.ts` | none | Soil fertility advice |
| Kaegro soil API | `soilService.ts` | base URL | Soil test |
| geocode.maps.co | `utils/geo/geocoding.ts` | `GEOCODE_API_KEY` | Address ↔ coordinates |
| India Post PIN API | `pincodeApi.ts` | none | PIN → state/district/taluk |
| Google Gemini | `geminiService.ts`, `landVerifier.ts` | `GEMINI_API_KEY` | Kisan Mitra + land-record reading |
| Mapbox | `@rnmapbox/maps` | `MAPBOX_ACCESS_TOKEN` | Maps |
| Sentinel Hub / ISRO Bhuvan (mock URLs) | `satelliteMapService.ts` | — | NDVI overlay (placeholder) |

## 9. Database change process (until DB-1 is done)

1. Write the change as a new file `supabase/NN_description.sql` (idempotent: `if not exists`, `create or replace`, `do $$ … exception when duplicate_object`).
2. Run it in a staging Supabase project first.
3. Add RLS policies in the same file; test as a farmer **and** as an owner (silent failures!).
4. If the table needs live updates, `alter publication supabase_realtime add table …`.
5. Document the table in this file and the owning module doc.
6. Never edit the live DB through the dashboard without committing the SQL the same day.
