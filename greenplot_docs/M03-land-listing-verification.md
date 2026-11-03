# M03 — Land Listing & Verification

| | |
|---|---|
| **Status** | 🟡 Partial — adding, editing, photos, plot drawing and AI document check work; admin verification happens outside the app; several form fields are not saved to the database |
| **Roles** | Owner (create/edit/view), Farmer (view approved farms) |
| **Code** | `src/screens/owner/{AddFarmScreen,MyPropertiesScreen,PropertyDetailsScreen,LandSubmittedScreen}.tsx`, `src/screens/farmer/FarmDetailScreen.tsx`, `src/context/FarmListingsContext.tsx`, `src/services/{landsApi,landVerifier,pincodeApi,storageApi}.ts`, `src/utils/farmManagementStatus.ts`, `src/utils/geo/*`, `src/data/locationHierarchy.ts`, `src/constants/indiaLocations.json`, `src/navigation/MyPropertiesStack.tsx` |
| **DB** | `lands` (+ admin columns), view `lands_available_for_management`, buckets `land-images` |
| **Related** | [M06 Farm Management](M06-farm-management.md), [M04 Leasing](M04-leasing.md), [M12 Satellite](M12-agronomy-services.md), [M07 Crops](M07-crop-management.md) |

## 1. Purpose & scope
Let an owner put a piece of land into GreenPlot with enough proof and detail that AgriArambh (Admin) can verify it and farmers can trust it.

**In scope:** add/edit land, location pickers, plot boundary, media upload, ownership document check, owner's property list and detail view, status badges.
**Out of scope:** the Admin verification UI (separate portal), lease offers ([M04](M04-leasing.md)), crop cycles ([M07](M07-crop-management.md)).

## 2. Land lifecycle (what "status" means)

There are **three overlapping status fields**. Do not mix them up.

| Field | Values | Written by | Meaning |
|-------|--------|-----------|---------|
| `lands.status` | `active`, `leased`, `inactive` | App / `approve_lease_request` | Legacy lease availability |
| `lands.verification_status` | `DRAFT`, `PENDING_VERIFICATION`, `APPROVED`, … | **Admin portal only** | Has AgriArambh verified this land? |
| `lands.management_status` | `NOT_AVAILABLE`, `AVAILABLE_FOR_MANAGEMENT`, `FARMER_ASSIGNED`, `ACTIVE_MANAGEMENT`, `COMPLETED` | **Admin portal only** | Where the land is in Farm Management |
| `lands.verified` (+ `verified_owner`) | boolean | App (from AI document check) | Document AI result — a *signal*, not the official verification |

The owner sees one friendly status, derived by `getManagementStatus()` (`utils/farmManagementStatus.ts`):

| Shown to owner | Rule |
|----------------|------|
| **Managed Farm** | `management_status` in `FARMER_ASSIGNED / ACTIVE_MANAGEMENT / COMPLETED`, or (legacy) `status = leased` |
| **Verified** | `verification_status = APPROVED`, or (legacy) `verified = true` |
| **Under Verification** | any other non-draft `verification_status`, or no data |

## 3. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M03-F01 | Add land: title, acres, soil type, description | ✅ | Required: Title, Acres, State, District, Soil type |
| M03-F02 | Location pickers State → District → Taluk → Hobli → Village (offline, 35 states / ~10.8k taluks) | ✅ | Prefilled from profile; **PIN-code auto-fill** via India Post API |
| M03-F03 | Draw plot boundary on satellite map; area computed | ✅ | `SatelliteMapScreen` returns `plotGeoJSON`; `utils/geo/polygonArea.ts` |
| M03-F04 | Photos and video upload with per-file retry and progress | ✅ | `land-images` bucket; first photo = cover; blocks submit while uploading or failed |
| M03-F05 | Govt. survey number + **land-record document check** (AI reads RoR / Pahani / 7-12, compares owner name and survey number) | ✅ | `landVerifier` → Gemini Vision. Result badges: verified / mismatch / unreadable / unconfigured |
| M03-F06 | Best crops to grow (multi-select), water sources (multi-select), current crop | ✅ | Water source saved as comma string |
| M03-F07 | Irrigation schedule, pesticide schedule, expected harvest | 🟡 | Collected and shown in mock mode; **not persisted in live mode** (see §8) |
| M03-F08 | **Submit for verification** (non-self-farmed land) → "Land Submitted" screen | ✅ | No lease terms collected; placeholders `tenure 'Not specified'`, `pricePerYear '0'` |
| M03-F09 | **Self-farmed land** (a farmer adds land they own and cultivate, from My Crops → My Own Land) | ✅ | Created directly (route `AddLand`, `selfFarmed: true`, `ownerId` = the farmer); never in marketplace; no verification step |
| M03-F10 | Edit land | 🟡 | Works, but write is fire-and-forget (BUG-1) |
| M03-F11 | Owner "My Properties" list with filters All / Pending / Verified / Managed / Completed | ✅ | "Completed" = lands whose lease closed |
| M03-F12 | Property (Land) Details: status, crop, upcoming activities, observations, activities, harvest, satellite shortcut, share | ✅ | Reads crop data of the managing farmer ([M07](M07-crop-management.md)) |
| M03-F13 | Delete land | 🟡 | `deleteListing` exists; fire-and-forget; verify UI exposure |
| M03-F14 | Farmer "Farm Detail" screen; **Request Management** button only for approved + available farms | ✅ | Legacy farms show Lease Options instead |
| M03-F15 | "All available lands" browse screen for farmers | 🚧 | `AllAvailableLandsScreen` exists; no entry point (action `allLands` unused) |
| M03-F16 | Admin verification (approve/reject land, request more documents) | ⚪ outside app | Admin portal; app only reads the result |
| M03-F17 | Land-records API verification (APISetu / aggregator) | ⚪ | Plug-in slot exists (`LandVerifier` interface) |

## 4. Flows

### 4.1 Owner submits a new land
1. Home → **Add land** (or Properties tab) → `AddFarm`.
2. Fill details; optionally tap **Draw plot on satellite map** (leaves and returns with the polygon); upload photos/video.
3. Optional: enter survey number + upload land record → AI check → badge.
4. Tap **Submit for verification** → `addListing()` (awaited; errors shown) → `navigation.replace('LandSubmitted')` so Back cannot reopen the form (this prevents duplicate lands — fixed bug).
5. Land appears in **Properties → Pending**. When Admin approves, it becomes **Verified**; when Admin makes it available and assigns a farmer it becomes **Managed**.

### 4.2 Self-farmed land
`AddLand` (the same `AddFarmScreen`) with `selfFarmed: true`, reached from the **farmer's My Crops tab → My Own Land** → one button → land created with `ownerId` = that farmer → they add a crop on it in [M07](M07-crop-management.md). Lease/verification fields are skipped.

### 4.3 Document check
Pick image → base64 → `landVerifier.verify({ base64, claimedSurveyNumber, claimedOwnerName, state })` → provider "document" (Gemini) returns `{ ownerName, surveyNumber, area, village, … }`. Status `mismatch` only if the typed survey number clearly differs; otherwise `verified`. Never throws to the UI.

## 5. Screens and routes

| Screen | Route (stack) | Params |
|--------|---------------|--------|
| `AddFarmScreen` | `AddFarm` (OwnerHome, MyProperties), `AddLand` (MyCrops) | `acres, plotGeoJSON, location, district, state, editListingId, selfFarmed` |
| `LandSubmittedScreen` | `LandSubmitted` | `propertyId` |
| `MyPropertiesScreen` | `MyPropertiesList` | — |
| `PropertyDetailsScreen` | `PropertyDetails` | `propertyId, viewHistory?` |
| `FarmDetailScreen` | `FarmDetail` (FarmerHome) | `farmId` |
| `SatelliteMapScreen` | `SatelliteMap` | `farmId?, returnTo?` |

## 6. Data model
`FarmListing` (in `FarmListingsContext.tsx`) ↔ `lands` row, mapped in `landsApi.landToApp / toRow`.

Persisted in live mode: `title, soil_type, acres, location, district, state, tenure, price_per_year, lease_type, description, image_url, status, self_farmed, geo, last_year_crop, last_year_earnings, current_crop, crops, water_source, survey_number, verified, verified_owner, media` (+ `owner_id`, `owner_name` on insert). Read-only from admin: `verification_status, management_status, assigned_farmer_id`.

## 7. Business rules
1. A new non-self-farmed land always starts as a **verification request**; the owner cannot publish it directly to farmers.
2. Only `verification_status = APPROVED` **and** `management_status = AVAILABLE_FOR_MANAGEMENT` lands appear to farmers — enforced by the DB view, not the client.
3. Editing must **never** change `status` or ownership (`updates.status/ownerId/ownerName` are deleted before the update).
4. A form cannot be submitted while any photo is uploading or has failed.
5. The cover image is the first successfully uploaded photo.
6. Area is shown as **acres + guntas** (`formatArea`; 1 acre = 40 guntas).
7. A self-farmed land is only shown to its own creator (My Crops → My Own Land) and is excluded from every marketplace/available list (`!l.selfFarmed`).
8. The AI document check supports the review; it never replaces Admin approval.

## 8. Known issues & tech debt

| ID | Issue | Impact | Fix |
|----|-------|--------|-----|
| BUG-1 / KI-3 | `updateListing()` and `deleteListing()` do not await and swallow errors; `landsApi.updateLand` ignores the `{ error }` Supabase returns, so even `.catch` never fires | "Changes saved ✓" shown when nothing saved | Return the promise, check `error`, show failure |
| M03-D1 | `toRow` does not map `taluk`, `hobli`, `village`, `irrigationSchedule`, `pesticideSchedule`, `expectedHarvest` | These inputs vanish after restart in live mode; edit screen cannot prefill taluk | Add columns + mapping (migration) |
| KI-4 | `lands` readable by all; client filters | Unapproved lands leak | SEC-4 |
| M03-D2 | `fetchLands` loads up to 500 rows for every user | Slow at scale | PERF-1 |
| M03-D3 | `AddFarmScreen.tsx` is 1,650 lines | Hard to maintain | Split into hook + sections (follow the folder convention in [01 §2](../01-architecture.md)) |
| M03-D4 | Land Verifier needs a Gemini key shipped in the app | Key exposure | SEC-2 (proxy) |
| M03-D5 | Uploaded land documents: where are they stored/retained? Document image is sent to Gemini and not stored | Privacy/compliance undefined | Decide retention; add to privacy policy |
| M03-D6 | `LeaseLandScreen` shows hard-coded demo lands and has no entry point | Dead code | Delete or replace |

## 9. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Make `updateLand/deleteLand/updateListing/deleteListing` return promises, check `error`, surface failure; UI awaits | M03-T1 | P0 | S | Forced RLS failure shows an error; success shows saved |
| 1 | Migration: add `taluk, hobli, village, irrigation_schedule, pesticide_schedule, expected_harvest` to `lands`; map in `landsApi` | M03-T2 | P1 | S | Values survive app restart and prefill Edit |
| 1 | Replace `select using (true)` with policy/view: owners read their own lands; others read only approved + available | M03-T3 | P0 | M | Farmer account cannot `select` a pending land (test with raw query) |
| 2 | Show verification timeline to owner (Submitted → Under review → Verified → Available → Assigned) using real timestamps | M03-T4 | P1 | M | Each step has date; matches Admin portal events |
| 2 | Admin feedback to owner: rejection reason / "documents needed" shown on Land Details + notification | M03-T5 | P1 | M | Owner sees reason; can resubmit |
| 2 | Document upload for ownership proof stored privately (private bucket, signed URLs) and linked to the land for Admin review | M03-T6 | P1 | M | Admin can open the document; owner only | 
| 2 | Refactor `AddFarmScreen` into `screens/owner/addFarm/` (hook + sections + styles) | M03-T7 | P2 | L | Behaviour unchanged; file < 400 lines each |
| 3 | Plug a land-records provider behind `LandVerifier` | M03-T8 | P2 | L | Provider flag; document path remains fallback |
| 3 | Duplicate-land detection (same survey number + village) | M03-T9 | P2 | M | Warns owner before submit |

## 10. Test checklist
- [ ] Add land with no photo → cover empty state; with photos → first is cover
- [ ] Airplane mode while uploading → file shows retry, submit blocked
- [ ] Submit twice rapidly → exactly one land created
- [ ] After submit, tap Back → does not return to the form
- [ ] PIN 560001 fills state/district/taluk; invalid PIN shows message
- [ ] Wrong survey number vs document → `mismatch` badge
- [ ] Edit a leased land → status stays `leased`
- [ ] Owner A cannot edit Owner B's land (negative test, also via raw API)
- [ ] Farmer cannot see a `PENDING_VERIFICATION` land
- [ ] Filters on Properties match status rules in §2

## 11. Definition of Done
Standard DoD plus: negative RLS tests for every `lands` policy, and the status shown to the owner matches the Admin portal for the same land.
