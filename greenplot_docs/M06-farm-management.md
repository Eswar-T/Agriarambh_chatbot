# M06 — Farm Management Program

| | |
|---|---|
| **Status** | ✅ Live (farmer + owner sides). The **review / assign / stage-change side runs in the separate Admin portal** — not in this repo |
| **Roles** | Owner (submits land, watches progress), Farmer (requests, manages assigned farm), **Admin (external)** |
| **Code** | `src/screens/farmer/{FarmsAvailableForManagement,ManagementRequestForm,ManagementRequestReview,ManagementRequestSubmitted,MyManagementRequests,ManagementRequestDetails,MyManagedFarms,ManagedFarmDashboard,SelectCrop,CropPlanForm,CropPlanReview}Screen.tsx`, `managementRequestDraft.ts`, `managementRequestStatusMeta.ts`, `cropPlanDraft.ts`, `src/services/{managementRequestsApi,landsApi,farmActivityApi,farmObservationApi,harvestApi,cropsApi,cropGuidanceApi}.ts`, `src/utils/{farmManagementStatus,cropStages,cropHealth,monitoringTimeline}.ts` |
| **DB** | `lands.verification_status / management_status / assigned_farmer_id`, view `lands_available_for_management`, `management_requests`, RPC `withdraw_own_management_request` (+ crop tables, see [M07](M07-crop-management.md)) |
| **Related** | [M03 Land](M03-land-listing-verification.md), [M07 Crops](M07-crop-management.md), [M05 Closure](M05-lease-closure.md) |

## 1. Purpose & scope
A **managed-farming program**: AgriArambh verifies an owner's land, offers it to farmers, selects one, and then the assigned farmer runs the crop with a guided plan while the owner and Admin watch progress. This replaces the "owner picks a tenant" marketplace as the main path ([M04](M04-leasing.md) decision LEASE-1).

**In scope (this app):** farmers browse approved farms, submit/withdraw requests, see status; assigned farmers run the farm dashboard (crop plan, activities, observations, harvest); owners see status and progress.
**Out of scope (Admin portal):** verifying lands, reviewing/shortlisting/approving requests, assigning a farmer, changing `management_status`.

> **Hard rule:** the mobile client can never set `verification_status`, `management_status`, `assigned_farmer_id`, or a request status other than `PENDING_REVIEW` (create) / `WITHDRAWN` (RPC). Keep it that way.

## 2. End-to-end lifecycle

```
OWNER                         ADMIN PORTAL (external)                 FARMER
 add land ───────────────────► verification_status: PENDING_VERIFICATION
                               ├─ APPROVED  ──► management_status: AVAILABLE_FOR_MANAGEMENT
                               │                                       │ appears in "Farms Available for Management"
                               │                                       ▼
                               │                        request (PENDING_REVIEW) ──► can WITHDRAW
                               ├─ UNDER_REVIEW / SHORTLISTED  ◄────────┘
                               ├─ APPROVED request ─► assigned_farmer_id set, management_status: FARMER_ASSIGNED
                               │                                       │ "My Managed Farms" → dashboard
                               │                                       ▼
                               │                     select crop → crop plan → activities generated
                               ├─ ACTIVE_MANAGEMENT ◄── farmer logs activities, observations, advances stages
                               └─ COMPLETED  ◄──────── harvest recorded, cycle completed
```

Request statuses: `PENDING_REVIEW` (shown "Request Submitted") → `UNDER_REVIEW` → `SHORTLISTED` → `APPROVED` ("Management Approved") / `REJECTED` ("Request Not Approved"); farmer-driven `WITHDRAWN`; system `CANCELLED`. "Active" (blocks a duplicate) = `PENDING_REVIEW, UNDER_REVIEW, SHORTLISTED`.

Stage labels for managed farms: `FARMER_ASSIGNED` "Farm Assigned" · `ACTIVE_MANAGEMENT` "Active Management" · `COMPLETED` "Management Completed".

## 3. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M06-F01 | **Farms Available for Management** list with a soil-type filter (All, Black, Alluvial, Red, Clay, Sandy — same set as the old lease filters) | ✅ | Reads the DB view — server-side scope, not a client filter |
| M06-F02 | Farm detail with **Request Management** (or "View my request" if one exists) | ✅ | `FarmDetailScreen` |
| M06-F03 | Request form: preferred crop, farming experience, previous crops, preferred start date, expected duration, notes | ✅ | Draft carried as serialisable route param |
| M06-F04 | Review screen then submit; **re-checks availability** and **blocks duplicates** (error codes `UNAVAILABLE`, `DUPLICATE`; DB partial unique index as backstop) | ✅ | `managementRequestsApi.submitRequest` |
| M06-F05 | Submitted confirmation (stack reset so Back doesn't return to the form) | ✅ | |
| M06-F06 | **My Management Requests** list with colour-coded status chips | ✅ | `managementRequestStatusMeta.ts` |
| M06-F07 | Request details and **withdraw** (only while `PENDING_REVIEW` or `UNDER_REVIEW`) | ✅ | RPC `withdraw_own_management_request`. `admin_notes` is in the data type; confirm it is displayed |
| M06-F08 | **My Managed Farms** (assigned farms) and Home snapshot counts | ✅ | `FarmListingsContext.myManagedFarms` |
| M06-F09 | **Managed Farm Dashboard** — overview, crop plan, today's guidance, upcoming, crop health, harvest readiness, performance, crop history | ✅ | 1,991-line screen |
| M06-F10 | Select crop (from `crops` master) → Crop plan form (variety, planting date, expected harvest, area, irrigation, notes) → Review → creates crop cycle + **auto-generated activity schedule** | ✅ | `farmActivityApi.generateFromGuidance` |
| M06-F11 | Complete an activity (date, notes, optional photo + observation); stage auto-advances to the activity's stage (never backward) | ✅ | |
| M06-F12 | Add free observation (text/photo) | ✅ | `farm_observations` |
| M06-F13 | **Advance stage** manually (guards: sowing must be logged before growth stages; warns about pending activities) | ✅ | |
| M06-F14 | **Record harvest** (date, area, quantity, unit, grade, photos, notes) and **Complete crop cycle** | ✅ | append-only `harvest_records` |
| M06-F15 | Monitoring tab: overall health, satellite shortcut, soil health, soil+crop context, weather, observations, **timeline** | ✅ | Soil and weather via [M12](M12-agronomy-services.md) |
| M06-F16 | Owner view of managed lands: status badge (Under Verification / Verified / Managed Farm) and live crop progress in Land Details | ✅ | [M03](M03-land-listing-verification.md) |
| M06-F17 | Admin review UI, assignment, stage changes | ⚪ external | |
| M06-F18 | Notifications to farmer/owner on request status changes | ⚪ | No producer in repo ([M14](M14-notifications.md)) |
| M06-F19 | Budget requests / approvals by owner | 🧪 | `BudgetApprovalsScreen`, no table ([M08](M08-labor-work.md)) |
| M06-F20 | Earnings / revenue sharing between owner, farmer and AgriArambh | ⚪ | Not defined in code — business rules needed |

## 4. Screens and routes (FarmerHomeStack unless noted)

| Screen | Route | Params |
|--------|-------|--------|
| `FarmsAvailableForManagementScreen` | `FarmsAvailableForManagement` | — |
| `FarmDetailScreen` | `FarmDetail` | `farmId` |
| `ManagementRequestFormScreen` | `ManagementRequestForm` | `farmId` |
| `ManagementRequestReviewScreen` | `ManagementRequestReview` | `farmId, draft` |
| `ManagementRequestSubmittedScreen` | `ManagementRequestSubmitted` | `requestId` |
| `MyManagementRequestsScreen` / `ManagementRequestDetailsScreen` | `MyManagementRequests` / `ManagementRequestDetails` | `requestId` |
| `MyManagedFarmsScreen` | `MyManagedFarms` | — |
| `ManagedFarmDashboardScreen` | `ManagedFarmDashboard` | `farmId` (also opened from the My Crops tab) |
| `SelectCropScreen` → `CropPlanFormScreen` → `CropPlanReviewScreen` | `SelectCrop` → `CropPlanForm` → `CropPlanReview` | `farmId`, `cropId/cropName`, `draft` |

## 5. Business rules
1. Only lands with `verification_status = APPROVED` **and** `management_status = AVAILABLE_FOR_MANAGEMENT` are requestable (view-enforced).
2. One **active** request per farmer per farm. Re-submit after `REJECTED`/`WITHDRAWN` is allowed.
3. A farmer can only create (`PENDING_REVIEW`) or withdraw their own request, and withdraw is offered only in `PENDING_REVIEW` / `UNDER_REVIEW`.
4. A farm shows "Managed" to the owner once `management_status ∈ {FARMER_ASSIGNED, ACTIVE_MANAGEMENT, COMPLETED}`.
5. A crop plan creates one `crop_cycles` row (scoped to the land and, when relevant, the lease) and **idempotently** generates activities: `scheduled_date = planned planting date + crop_guidance.recommended_day`. A custom "Other" crop (no `crop_id`) generates none.
6. Crop **stages** form one fixed ordered list for every crop (10 stages: Land Preparation → … → Post-Harvest); a stage **never moves backward**; Early Growth onward needs a sowing date.
7. Crop **health** is derived, not diagnosed: `GOOD` (nothing overdue) / `ATTENTION_REQUIRED` (any overdue pending activity) / `AT_RISK` (overdue HIGH-priority activity). Source: `utils/cropHealth.ts`.
8. A cycle stays "current" through `active`, `harvest_ready`, `harvested`; only `completed` retires it.
9. Multi-harvest is supported: harvest records are append-only; completing the cycle is a separate action.

## 6. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| M06-D1 | Admin side and its SQL are outside the repo; four referenced SQL files are missing | DB-1; write an **Admin contract** section (statuses, who may change what) in [02](../02-database-backend.md) |
| M06-D2 | `ManagedFarmDashboardScreen.tsx` is 1,991 lines | Split into `managedFarm/` (hook + Overview, Crop, Monitoring, Harvest sections + sheets) |
| M06-D3 | Several writes happen in sequence without a transaction (complete activity → add observation → add activity log → sync stage) and the log insert is `.catch(() => {})` | Edge/RPC `complete_farm_activity` |
| M06-D4 | Request status changes do not notify the farmer/owner | NOT-1 |
| M06-D5 | No owner view of *who* requested/was assigned, or ability to comment | M06-T6 |
| M06-D6 | Farm Management business model (fees, revenue split, liabilities) not captured in the product | Product decision |
| M06-D7 | Terminology collision with leasing ("Management request" copy in lease activity) | LEASE-1 |
| M06-D8 | Closing a managed farm: stage `COMPLETED` set by Admin; farmer-initiated end uses the lease closure flow ([M05](M05-lease-closure.md)) — the link between the two is not defined | Define the end-of-management rule |

## 7. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Commit the four missing migrations and the Admin contract table | M06-T1 | P0 | M | New environment gets the whole Farm Management schema from the repo |
| 1 | Notifications for request status changes (DB trigger → `notifications` + push) | M06-T2 | P1 | M | Farmer is told within seconds of Admin changing status |
| 2 | Split `ManagedFarmDashboardScreen` | M06-T3 | P2 | L | No file > 500 lines; behaviour unchanged (manual regression pass) |
| 2 | `complete_farm_activity` RPC that does all writes atomically and returns the updated cycle | M06-T4 | P1 | M | No partial state on failure |
| 2 | Ask-for-info loop: Admin can request more details on a request; farmer replies in-app | M06-T5 | P2 | L | Thread stored; notifications both ways |
| 2 | Owner visibility: assigned farmer card (name, phone, rating), request count, progress summary | M06-T6 | P1 | M | Owner sees who manages the land and latest activity date |
| 3 | Farmer reputation (completed cycles, on-time activity %, harvest quality) | M06-T7 | P2 | L | Visible on request review in Admin portal |
| 3 | Revenue/expense ledger per farm cycle (inputs, labor, sales) and owner/AgriArambh share | M06-T8 | P2 | XL | Needs product rules first |
| 3 | Per-crop stage tables (`crop_stages`) replacing the single global list | M06-T9 | P2 | M | Different stage lists per crop |

## 8. Test checklist
- [ ] Farmer sees only approved + available farms; a pending land never appears (check with a fresh account)
- [ ] Submit twice quickly → exactly one request; second shows the existing one
- [ ] Admin flips farm to unavailable while form is open → submit shows "no longer available"
- [ ] Withdraw → status `WITHDRAWN`; can request again
- [ ] After assignment the farm shows in My Managed Farms and the owner's Properties shows "Managed Farm"
- [ ] Crop plan creates the cycle and activities once (re-saving creates none)
- [ ] Complete a "Flowering" activity → stage moves forward; completing an earlier-stage activity later does **not** move it back
- [ ] Advance past Planting without a sowing date → blocked with message
- [ ] Record two harvests → both listed; cycle completes only on explicit action
- [ ] Offline during any step → clear error, no half-saved record

## 9. Definition of Done
Standard DoD plus: any status the client writes is covered by an RLS/RPC negative test, and Admin portal behaviour is confirmed with the Admin team for the same scenario.
