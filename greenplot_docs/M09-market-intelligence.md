# M09 — Market Intelligence & Cold Storage

| | |
|---|---|
| **Status** | 🟡 Partial — price, trend, arrivals, mandi list, demand map and crop-compare run on **real** Agmarknet data. Seven screens are placeholders. Cold-storage booking is mock |
| **Roles** | Farmer, Owner (same Market tab for both) |
| **Code** | `src/modules/market/**` (screens, components, `navigation/{MarketStack,marketRoutes}`, `theme/marketTokens.ts`, `constants/marketCatalog.ts`, `data/coldStorages.ts`, `types`), `src/services/mandiApi.ts`, `src/screens/MandiPricesScreen.tsx`, `src/localization/marketTranslations.ts`, Home ticker (`farmerHome/components/sections/MarketTicker.tsx`) |
| **External API** | data.gov.in Agmarknet daily prices (resource `9ef84268-d588-465a-a308-a864a43d0070`), key `DATA_GOV_API_KEY` |
| **DB** | none yet (cold-storage tables proposed below) |
| **Related** | [M12 Agronomy](M12-agronomy-services.md), [M11 Kisan Mitra](M11-kisan-mitra-ai.md), [M02 Dashboards](M02-dashboards.md) |

## 1. Purpose & scope
Help farmers **sell at a better price and plan what to plant**: where a crop pays most, how the price is moving, how much is arriving, which crop is more attractive in their state, and where to store produce when prices crash.

## 2. Data source and its limits
`mandiApi.fetchPrices({ commodity, state, district, market, limit })` calls the Agmarknet resource and returns `MandiPrice { commodity, variety, market, district, state, minPrice, maxPrice, modalPrice (₹/quintal), arrivalDate }`. Records with `modalPrice ≤ 0` are dropped. On any error it returns `[]` (UI shows empty state).

* `compareMarkets(commodity, state)` — best (highest modal) price per market, sorted high→low.
* `commoditiesForState(state)` — distinct commodity list.

Limits to design around: public sample key is **rate-limited**; data is *daily and sparse by market*; only recent days are returned (so "trend" is a short window, not history); state names must match Agmarknet spelling; the crop catalog is currently **5 crops** (`MARKET_CROPS`: Tomato, Onion, Chilli, Jowar, Cotton). The default state is `user.state || 'Karnataka'`.

## 3. Features

| ID | Feature | Status | Data |
|----|---------|:------:|------|
| M09-F01 | **Market Home / Overview**: crop tabs, hero price, stats, mini chart, nav strip (Overview · Trend · Arrivals · Mandis · Demand · AI · Compare) | ✅ | real |
| M09-F02 | **Price Trend** (area chart, change %) | ✅ | real, short window |
| M09-F03 | **Mandi List** (best markets, sorted) | ✅ | real |
| M09-F04 | **Arrivals** (volume proxy by district, activity bars) | ✅ | real |
| M09-F05 | **Demand Map** (price strength + freshness score per market) | ✅ | real, computed client-side |
| M09-F06 | **Which Crop to Plant / Crop Compare** (ranks catalog crops for the state from recent price + arrivals) | ✅ | real, computed client-side |
| M09-F07 | **Alerts Centre** (derived alerts from price movement) | 🟡 | derived on the device; no stored alert rules, no push |
| M09-F08 | Mandi Prices (legacy screen) reachable from Home ticker/Quick action — pick commodity+state, best market first | ✅ | real |
| M09-F09 | Language switch and translated market strings (6 languages) | ✅ | `marketTranslations.ts` |
| M09-F10 | Price Forecast | ⚪ | `MarketFeatureUnavailable` |
| M09-F11 | Find Buyers | ⚪ | placeholder |
| M09-F12 | MSP / FRP reference prices | ⚪ | placeholder |
| M09-F13 | Oversupply alert | ⚪ | placeholder |
| M09-F14 | AI Market Insight | ⚪ | placeholder |
| M09-F15 | Filter & Search, Empty State | ⚪ | placeholder |
| M09-F16 | **Cold storage**: list (distance, rating, capacity, rate/kg/day, features) → detail → booking (quantity, days, insurance, cost breakdown) → confirmation | 🧪 | `MOCK_COLD_STORAGES`; booking not persisted; confirmation id is fake |
| M09-F17 | Price alerts a user can subscribe to (crop, market, threshold) with push | ⚪ | |
| M09-F18 | Sell-now vs hold advice using forecast + storage cost | ⚪ | |

## 4. Navigation (`MarketStackParamList`)
`MarketHome` · `PriceTrend` · `MandiList` · `DemandMap` · `AIInsight` · `Arrivals` · `OversupplyAlert` · `FindBuyers` · `PriceForecast` · `AlertsCentre` · `FilterSearch` · `CropCompare` · `MspFrp` · `MarketEmpty` · `ColdStorageList` · `ColdStorageDetail` · `ColdStorageBooking` · `StorageBookingConfirmed` · `NotificationsCenter` · `Settings`. Most take optional `{ cropId, commodity, state, market }`.

## 5. Business rules
1. **Never invent prices.** If the API returns nothing show an explicit empty/"no data for this date" state (module rule: "Prices and intelligence are never stored in the catalog").
2. Prices are ₹ per quintal; convert before comparing with per-kg storage rates (`1 quintal = 100 kg`).
3. Best market = highest `modalPrice` per `(market, district)`.
4. Cold-storage cost = `qty × rate/kg/day × days` + handling (`HANDLING_PER_KG × qty`) + insurance (5% of qty per 30 days unless the storage already insures). Show expected recovery vs outlay before booking.
5. The "Which crop to plant" ranking must be explained to the farmer (price level, trend, arrivals) — it is guidance, not a guarantee.

## 6. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| KI-9 | 7 placeholder screens are linked from visible navigation | Hide until built, or build in priority order (§7) |
| KI-10 | Cold storage is mock end to end | MKT-2 |
| M09-D1 | `mandiApi.fetchPrices` leaves a `console.log` of the entire response | Remove |
| M09-D2 | Every screen refetches 500 rows with no cache; public key rate limit will bite | Cache in an Edge Function / Postgres table with a daily job (M09-T1) |
| M09-D3 | Only 5 crops; names must match Agmarknet commodity strings | Expand catalog + alias table |
| M09-D4 | Home ticker still mock | M02-T2 |
| M09-D5 | The module has its own design tokens (`marketTokens.ts`) and translation bundle | Acceptable; keep in sync with `theme/tokens.ts` colors |
| M09-D6 | Date parsing handles `dd/mm/yyyy` and `yyyy-mm-dd` heuristically (`parseDate`) | Normalise in `mandiApi` once |

## 7. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Remove debug log; hide placeholder links (or show "Coming soon" chip) | M09-T0 | P0 | S | No tappable dead end |
| 2 | **Price cache**: scheduled Edge Function pulls Agmarknet daily into `mandi_prices` (state, commodity, market, date, min/max/modal, arrival qty) + 30–90 day history; app reads from Supabase | M09-T1 | P1 | L | App loads < 1 s; trend shows ≥ 30 days; survives API outage |
| 2 | Expand crop catalog (top 25 by state) with aliases and emoji | M09-T2 | P1 | M | Picker covers launch-state crops |
| 2 | **Price Forecast** v1 (moving average + seasonality from cached history, with confidence label) | M09-T3 | P1 | L | Backtest error reported; labelled "estimate" |
| 2 | **MSP / FRP** reference screen from official table (static JSON updated each season) | M09-T4 | P1 | S | Shows current-year MSP, source and date |
| 2 | **Price alerts**: user rules table + daily job + push | M09-T5 | P1 | L | Alert fires once per crossing; manageable in Alerts Centre |
| 2 | **Find Buyers**: directory of buyers/FPOs/traders by crop + district, tap-to-call/WhatsApp | M09-T6 | P2 | L | Needs data source + verification process |
| 2 | **Oversupply alert** using arrivals vs 30-day average, linking to cold storage | M09-T7 | P2 | M | Alert appears when arrivals > threshold |
| 3 | **Cold storage backend**: tables `cold_storages`, `storage_bookings`; owner onboarding; availability decrement; payment via [M13](M13-payments.md) | M09-T8 | P2 | XL | Real booking and receipt |
| 3 | AI Market Insight (Gemini summarising the cached data, grounded; with citations of numbers shown) | M09-T9 | P2 | M | No claim without a displayed number |
| 3 | Sell-now vs hold advisor | M09-T10 | P2 | M | Uses forecast + storage cost + user's quantity |

## 8. Test checklist
- [ ] Each of the 5 crops loads for Karnataka, Maharashtra, Bihar; empty state when none
- [ ] Airplane mode → empty/error state, no crash, no spinner forever
- [ ] Switching crop cancels the previous request (AbortController) — no flash of the wrong crop's data
- [ ] Prices equal the data.gov.in source for a sampled market
- [ ] Language switch re-renders market labels
- [ ] Cold storage cost matches the formula for sample inputs
- [ ] Placeholder screens never reachable (or clearly labelled)

## 9. Definition of Done
Standard DoD plus: numbers shown can be traced to a record (date + market) and the data source is credited in the UI.
