# M02 — Dashboards (Farmer Home & Owner Home)

| | |
|---|---|
| **Status** | 🟡 Partial — real data for leases, farms, crops and notifications; some tiles are mock, disabled or commented out |
| **Roles** | Farmer (`FarmerHomeScreen`), Owner (`OwnerHomeScreen`) |
| **Code** | `src/screens/farmerHome/**`, `src/screens/ownerHome/**`, `src/utils/activityFeed.ts`, `src/components/organisms/HomeHeader.tsx`, `src/components/molecules/AppHeader.tsx` |
| **Related** | Aggregates M03, M04, M05, M06, M07, M09, M12, M14 |

## 1. Purpose & scope
The first screen after login. It answers: *"What is happening on my land / farm today, and what should I do next?"* and gives one-tap access to the main tools. It owns **no data of its own** — it reads from contexts and services owned by other modules.

## 2. Pattern (copy for new dashboards)
```
FarmerHomeScreen ── useFarmerHome() ──► view-model (data + handlers)
        └──────────► <FarmerHomeContent {...vm}/>  ──► sections/*.tsx
```
All navigation logic is in the hook (`onAction(actionKey)` switch). Content components are presentational.

## 3. Features — Farmer Home

| ID | Feature | Status | Source of data |
|----|---------|:------:|----------------|
| M02-F01 | Header: greeting, location label, language button, bell, avatar | ✅ | `AuthContext`, device GPS (`useCurrentLocation`) |
| M02-F02 | **Weather hero** (temp, condition, advice) | ✅ | OpenWeather via `useWeather(location)` — see [M12](M12-agronomy-services.md) |
| M02-F03 | **Farm snapshot**: Managed farms · Acres farmed · Crops · Tasks due | 🟡 | First three real (`myManagedFarms`, `cropCycles`); **Tasks due is a disabled "Soon" tile** |
| M02-F04 | **Market ticker** (mandi prices strip) | 🟡 | Mock rows `FARMER_TICKER`; "see all" opens Mandi Prices (real) |
| M02-F05 | **Quick actions**: Add Crop · My Requests · My Managed Farms · Satellite · Soil Test · Soil Advisory | ✅ | Static list; several others commented out (Create Work, Hire Labor, Lease Status, Mandi, Kisan Mitra) |
| M02-F06 | **Recent activity** feed (notifications + lease/management/closure events) | ✅ | `notificationsApi`, `LeaseContext`, merged by `useFarmerHome.activities` |
| M02-F07 | **Farms available for management** carousel (max 6) | ✅ | `FarmListingsContext.availableForManagement` (DB view) |
| M02-F08 | **Schemes & News** with tabs and category filter | ✅ | NewsData.io via `useAgriNews`, else mock `FARMER_NEWS` + `schemeCatalog` |
| M02-F09 | **Videos** (news / technology / training) | ✅ | YouTube RSS / API via `useAgriVideos` |
| M02-F10 | AI advisory card + microphone shortcut to Kisan Mitra | 🟡 | Static text `FARMER_AI_ADVISORY`; mic opens [M11](M11-kisan-mitra-ai.md) |
| M02-F11 | Today's tasks section | 🚧 | `TasksSection` commented out |
| M02-F12 | Crop health section | 🚧 | `CropHealthSection` commented out (sample data) |
| M02-F13 | Browse by crop | 🚧 | commented out |

## 4. Features — Owner Home

| ID | Feature | Status | Source of data |
|----|---------|:------:|----------------|
| M02-F20 | Header, language, bell, avatar, weather hero (reuses farmer components) | ✅ | same as farmer |
| M02-F21 | **Portfolio summary**: lands · verified · managed · acres | ✅ | `FarmListingsContext.ownerListings` + `utils/farmManagementStatus.ts` |
| M02-F22 | **Metrics**: verified / managed / pending-verification counts | ✅ | derived |
| M02-F23 | **Action items**: closures needing owner input | ✅ | `LeaseContext.closures` |
| M02-F24 | Action items: budget approvals, rent overdue, lease renewal, disease risk | 🚧 | Commented out — no data source (see §7) |
| M02-F25 | **Pending lease requests** card → `LeaseRequests` | ✅ | `LeaseContext.requests` |
| M02-F26 | **Tools**: Add land · Satellite · Soil advisory · Mandi prices | ✅ | static |
| M02-F27 | Tools: Labor · Work report | 🚧 | Show "coming soon" alert |
| M02-F28 | Property snapshots list | ✅ | `buildPropertySnapshots(ownerListings, activeLeases)` |
| M02-F29 | Recent activity, Schemes & News, Videos | ✅ | as farmer |

## 5. Navigation map (what each tile opens)

| Tile / action key | Destination route | Module |
|-------------------|-------------------|--------|
| `MyActiveLeases` | `MyActiveLeases` | M04 |
| `labor` | `LaborConnect` (farmer only, currently hidden) | M08 |
| `satellite` | `SatelliteMap` | M12 |
| `weather` | `WeatherDetail` | M12 |
| `soil` / `soilAdvisory` | `SoilTest` / `SoilAdvisory` | M12 |
| `mandiCompare` / `market` | `MandiPrices` / Market tab | M09 |
| `aiAssistant` | `AIAssistant` | M11 |
| `allLands` | `AllAvailableLands` (dormant — see M03 issue) | M03 |
| `myManagementRequests` / `myManagedFarms` | `MyManagementRequests` / `MyManagedFarms` | M06 |
| `notifications` | `NotificationsCenter` | M14 |
| `settings` | `Settings` | M15 |
| Farm card | `FarmDetail { farmId }` | M03 |
| Activity row | `AgreementDetails` / `ClosureRequested` / `NotificationsCenter` | M04 / M05 |

## 6. Business rules
1. Dashboards never write data. Every tile only navigates.
2. Activity feed = real notification rows **plus** locally derived events (lease started, closure requested/ended). Derived events must have a stable id to avoid duplicates.
3. "Acres farmed" counts active crop cycles' areas / managed farms using `formatArea` (acres + guntas).
4. A tile that has no real data source must be **hidden or marked "Soon"**, never filled with invented numbers (this is why the owner action items are commented out).
5. The language button opens `LanguagePickerModal`; the weather location falls back: profile location → GPS address → empty (no card).

## 7. Dependencies and known gaps
| Gap | Why | Fix |
|-----|-----|-----|
| Owner "Rent overdue" and "Lease renewal" | `leases.next_payment` and `end_date` are never set when a lease is created, and no payments flow reads them | [M13](M13-payments.md) PAY-1 + set both at agreement activation |
| Owner "Budget approvals" | `BudgetApprovalsScreen` has no table behind it | [M08](M08-labor-work.md) OWN-1 |
| Owner "Disease risk" | `crop_cycles.health_status` is real; owner-side query (`owner_id = me and health_status = 'pest_alert'`) not wired | DASH-1 |
| Farmer "Tasks due" | `farm_activities` exist (real, [M07](M07-crop-management.md)) but no home-level aggregate | DASH-1 |
| Market ticker is mock | `FARMER_TICKER` | Use `mandiApi` for the user's state and top crops |
| Cross-tab navigation depends on `navigation.getParent()` shape | Fragile if tab nesting changes | Wrap in a typed helper |

## 8. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 2 | Home "Tasks due" tile: count of `farm_activities` with `status = PENDING` and `scheduled_date ≤ today` for this farmer; tap opens the crop's activity list | M02-T1 | P1 | M | Count matches DB; updates in realtime; zero shows "All clear" |
| 2 | Replace mock market ticker with live mandi data for user's state and 3 crops from active cycles | M02-T2 | P1 | M | Shows real prices with arrival date; offline shows last cached |
| 2 | Owner action items: wire "Disease risk" from `crop_cycles.health_status` | M02-T3 | P2 | S | Count equals pest-alert cycles on owner's lands |
| 2 | Owner action items: "Rent overdue/renewal" once M13 sets `next_payment` / `end_date` | M02-T4 | P1 | M | Items appear only with real dates |
| 2 | Re-enable `CropHealthSection` using `deriveCropHealth()` ([M07](M07-crop-management.md)) instead of sample data | M02-T5 | P2 | S | Shows real health per active crop |
| 2 | Replace static AI advisory card with Kisan Mitra daily tip from weather + crop stage | M02-T6 | P2 | M | Tip changes with weather/stage; opens chat with pre-filled question |
| 3 | Extract typed `goToTab()` helper; remove `getParent()` casts | M02-T7 | P2 | S | No `as ParentNav` casts |
| 3 | Pull-to-refresh refetching leases, lands, notifications | M02-T8 | P2 | S | Spinner then fresh data |

## 9. Test checklist
- [ ] New farmer with no data: every section shows a clean empty state (no crash, no fake numbers)
- [ ] Approve a lease on the owner phone → the farmer's activity feed updates without restart
- [ ] Switch language: header button label changes (`EN`, `हि`, `ಕ` …)
- [ ] No GPS permission: weather card hidden or falls back to profile location
- [ ] Every tile navigates to an existing route for both roles (no "undefined route" warning)

## 10. Definition of Done
Standard DoD plus: no hard-coded demo numbers visible to users, every tile has either live data or an explicit "Soon/disabled" state.
