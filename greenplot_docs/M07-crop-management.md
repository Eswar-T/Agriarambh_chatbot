# M07 — Crop Management (Crops, Activities, Harvest)

| | |
|---|---|
| **Status** | ✅ Live — crop cycles, guided activity schedule, observations, free-text activity log, harvest, health, stage tracking. Create-Work is mock (see [M08](M08-labor-work.md)) |
| **Roles** | Farmer (primary), Owner (read-only progress on their lands) |
| **Code** | Tab: `src/navigation/MyCropsStack.tsx`, `src/screens/farmer/MyCropsScreen.tsx`. Crop details: `src/modules/work/screens/CropDetailsScreen.tsx`, `src/modules/work/hooks/useCropActivities.ts`. State: `src/context/CropCycleContext.tsx`. Services: `cropCycleApi, cropActivityApi, farmActivityApi, farmObservationApi, harvestApi, cropsApi, cropGuidanceApi`. Utils: `utils/{cropStages,cropHealth,monitoringTimeline}.ts`. Types: `src/modules/work/types/index.ts`. Dashboard for managed farms: see [M06](M06-farm-management.md) |
| **DB** | `crop_cycles`, `crop_activities`, `farm_activities`, `farm_observations`, `harvest_records`, `crops`, `crop_guidance` (none in repo SQL — see [02 §4](../02-database-backend.md)) |
| **Related** | [M06 Farm Management](M06-farm-management.md), [M03 Land](M03-land-listing-verification.md), [M12 Agronomy](M12-agronomy-services.md), [M08 Work](M08-labor-work.md) |

## 1. Purpose & scope
Give every farmer one place to see **what is growing where, what to do next, what was done, and what was harvested** — for their own land, for leased plots, and for Farm-Management farms.

## 2. Core concepts

| Concept | What it is | Table |
|---------|-----------|-------|
| **Crop cycle** | One crop on one plot for one season. The spine of the module | `crop_cycles` |
| **Crop plan** | The planned crop, variety, planting and harvest dates, area, irrigation (Farm Management) | fields on the cycle |
| **Farm activity** | A *scheduled* task generated from master guidance (status, priority, date) | `farm_activities` |
| **Observation** | Farmer note/photo attached to an activity, tagged with the crop stage | `farm_observations` |
| **Crop activity** | A *free-text history* entry (sowing, irrigation, fertilizer, weeding, pest, harvest, other) | `crop_activities` |
| **Harvest record** | One harvest of a cycle (a cycle can have several) | `harvest_records` |
| **Crop guidance** | Master data: for crop + stage, the recommended tasks and the day offset after planting | `crop_guidance` |
| **Crop (master)** | Directory of crops with suitable soils, duration, water need | `crops` |

`farm_activities` (plan) and `crop_activities` (history) are **separate on purpose**: completing a scheduled activity *mirrors* a lightweight entry into the history log so the old timeline still shows it.

## 3. Lifecycle and states

**Cycle status:** `active` → `harvest_ready` (when stage reaches Maturity/Harvest) → `harvested` (after recording harvest) → `completed` (explicit "Complete cycle"); `fallow` is legacy. "Current" = `active, harvest_ready, harvested`.

**Stages (10, fixed order, never backward):** Land Preparation · Seed/Seedling · Planting · Early Growth · Vegetative Growth · Flowering · Fruit Development · Maturity · Harvest · Post-Harvest. Progress % = index / 9. Early Growth onward requires a sowing date. Free-text "sowing" implies stage Planting; "harvest" implies Harvest.

**Health (derived):** `GOOD` · `ATTENTION_REQUIRED` (overdue pending activity) · `AT_RISK` (overdue HIGH-priority). Legacy manual `health_status`: `healthy | needs_water | pest_alert`.

**Activity status:** `PENDING, IN_PROGRESS, COMPLETED, SKIPPED, CANCELLED`; types `IRRIGATION, FERTILIZATION, WEED_MANAGEMENT, PEST_INSPECTION, DISEASE_INSPECTION, SPRAYING, PRUNING, EARTHING_UP, HARVESTING, OTHER`.

## 4. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M07-F01 | **My Crops** tab with two tabs: *My Own Land* and *Managed Land* (managed farms + leased plots), counts, active crop cards | ✅ | `MyCropsScreen` (1,408 lines) |
| M07-F02 | Add own land (self-farmed) from My Crops | ✅ | `AddLand` → [M03](M03-land-listing-verification.md) |
| M07-F03 | Crop cycle per land **and per lease term** — a new lease on the same land never inherits an old cycle (`leaseId` scoping) | ✅ | commit `8d950c0` |
| M07-F04 | Select crop → crop plan → review → create cycle + generate schedule | ✅ | [M06](M06-farm-management.md) |
| M07-F05 | Activity schedule from `crop_guidance` (idempotent) | ✅ | `scheduled_date = planting + recommended_day` |
| M07-F06 | Complete an activity (date, notes, photo, observation) → stage syncs forward | ✅ | |
| M07-F07 | Free-text **Log Activity** (7 types; title required for "Other") | ✅ | `CropDetailsScreen` + `useCropActivities` (realtime) |
| M07-F08 | Observations list and **monitoring timeline** (completed activities + observations merged) | ✅ | `monitoringTimeline.ts` |
| M07-F09 | Advance stage with guards and pending-activity warning | ✅ | |
| M07-F10 | Record harvest (multi-harvest), complete cycle | ✅ | |
| M07-F11 | Derived crop health + overdue indicators | ✅ | `cropHealth.ts` |
| M07-F12 | Owner sees crop, upcoming activities, observations, activities, harvest on Land Details | ✅ | |
| M07-F13 | Crop details screen for leased/own plots without a crop yet ("View details" opens a fallback plot descriptor) | ✅ | |
| M07-F14 | Edit / delete crop cycle | 🟡 | `removeCropCycle` exists; confirm UI |
| M07-F15 | Mock mode with seeded cycles/activities | 🧪 | `MOCK_CROP_CYCLES`; activities kept in memory per cycle |
| M07-F16 | Crop-specific stage lists, cost & yield analytics, season history charts | ⚪ | |
| M07-F17 | Disease/pest diagnosis from photo (Crop Doctor) | ⚪ | Design `docs/crop_doctor_figma.html`; vision path in [M11](M11-kisan-mitra-ai.md) |
| M07-F18 | Reminders for due/overdue activities | ⚪ | Needs push ([M14](M14-notifications.md)) |

## 5. Screens and routes

| Screen | Route | Stack(s) |
|--------|-------|----------|
| `MyCropsScreen` | `MyCrops` | MyCrops (farmer tab); also registered in OwnerHome |
| `CropDetailsScreen` | `CropDetails { cropCycleId?, landId?, farmerId?, leaseId?, ownerId?, plotName?, ownerLabel?, areaAcres? }` | MyCrops, FarmerHome, OwnerHome, MyProperties |
| `ManagedFarmDashboardScreen` | `ManagedFarmDashboard { farmId }` | FarmerHome |
| `SelectCrop`, `CropPlanForm`, `CropPlanReview` | as named | FarmerHome |
| `CreateWorkScreen`, `WorkListScreen`, `WorkDetailsScreen` | `CreateWork`, `WorkList`, `WorkDetails` | MyCrops (+ others) — [M08](M08-labor-work.md) |
| `SatelliteMapScreen` | `SatelliteMap` | MyCrops — [M12](M12-agronomy-services.md) |

## 6. State and API

| Piece | Responsibility |
|-------|----------------|
| `CropCycleContext` | `cropCycles`, `getCropCycleById`, `getCropCycleByLand(landId, leaseId?)`, `saveCropCycle` (find-or-create upsert; resolves with the real id **after** the write lands), `updateCropCycle` (by-id transitions), `removeCropCycle`; dual-mode with realtime |
| `cropCycleApi` | `fetchAll, save, updateFields, remove, subscribe`; exports `CURRENT_STATUSES` |
| `farmActivityApi` | `fetchByCropCycle, generateFromGuidance, markCompleted, updateStatus, subscribe` |
| `farmObservationApi` | `add, fetch…` (+ photo) |
| `harvestApi` | `fetchByCropCycle(Ids), record` |
| `cropActivityApi` + `useCropActivities` | free-text log with realtime |
| `cropsApi`, `cropGuidanceApi` | read-only master data (with a hard-coded crop list fallback in mock mode) |

## 7. Business rules
1. **Cycle identity** = land + lease (if any). Self-farmed land and Farm-Management farms have no `leaseId`.
2. Work can only be created against a cycle whose lease is still `active` (closed leases are excluded).
3. Stage never decreases; completing any activity may only move the stage **forward**; manual advance requires sowing for growth stages.
4. A cycle stays visible on dashboards until explicitly **completed**.
5. Activity generation happens once per cycle; changing the plan later does not regenerate.
6. The farmer owns write access to their cycle data; the owner has read-only visibility.
7. Photos upload to `farm-media` under `<userId>/…`; failures must not lose typed text.

## 8. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| M07-D1 | All crop tables/RPCs missing from repo SQL; policies for owner read access unverified | DB-1 |
| M07-D2 | `MyCropsScreen` (1,408) and `ManagedFarmDashboardScreen` (1,991) are monolithic | Refactor into hook + sections |
| M07-D3 | `fetchByCropCycle` returns `[]` on error → looks like "no activities" | Return error state and show retry |
| M07-D4 | `cropActivityApi.add(...).catch(() => {})` in the complete flow hides failures; sequence is non-atomic | RPC (M06-T4) |
| M07-D5 | Single global stage list; guidance depends on well-populated `crop_guidance` per crop | Master-data work (M07-T4) |
| M07-D6 | Closing a lease does not close or hand over the cycle | M05-T4 |
| M07-D7 | No offline queue; field use with poor signal loses entries | M07-T7 |
| M07-D8 | `deriveCropHealth` ignores weather/satellite signals | M07-T6 |

## 9. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Add SQL for all crop tables + owner-read policies to repo; negative tests | M07-T1 | P0 | M | Fresh DB works; owner A cannot read owner B's cycles |
| 1 | Error states instead of silent `[]` for activity/observation/harvest loads | M07-T2 | P1 | S | Network failure shows retry banner |
| 2 | Home "Tasks due" tile and overdue badge on My Crops cards | M07-T3 | P1 | M | Counts equal DB; link to the activity |
| 2 | Seed and QA the `crops` + `crop_guidance` master data for the top 20 crops in each launch state (owner: agronomy lead) | M07-T4 | P1 | L | Every listed crop generates a sensible schedule |
| 2 | Edit crop plan (dates/area) with schedule shift option | M07-T5 | P2 | M | Updating planting date offsets pending activities |
| 2 | Feed weather + satellite NDVI into health (`AT_RISK` hints) | M07-T6 | P2 | L | Health explanation lists reasons |
| 2 | Offline queue for activity completion and observations | M07-T7 | P1 | L | Entries created offline sync when online, with conflict-free ordering |
| 3 | Cost & income per cycle; season comparison charts | M07-T8 | P2 | L | Farmer sees profit per acre per cycle |
| 3 | Crop Doctor integration (photo → diagnosis → observation) | M07-T9 | P2 | L | Diagnosis saved as an observation with photo |
| 3 | Per-crop stage definitions | M07-T10 | P2 | M | Stage list comes from DB per crop |

## 10. Test checklist
- [ ] New lease on a land that had a cycle: new lease shows an empty crop state, old cycle remains attached to the old lease
- [ ] Generate schedule twice → no duplicates
- [ ] Complete "Harvesting" activity → stage Harvest, status `harvest_ready`
- [ ] Complete an early-stage activity after a later one → stage unchanged
- [ ] Log "Other" without title → blocked
- [ ] Owner opens Land Details of a managed farm → sees same activities (read-only, no edit buttons)
- [ ] Complete a cycle → disappears from "current", appears under Crop History
- [ ] Mock mode: add activity, switch tabs, still there; restart → gone (documented)

## 11. Definition of Done
Standard DoD plus: new crop master data reviewed by an agronomy owner, and date arithmetic checked across month/year boundaries and time zones (`addDays` uses local dates).
