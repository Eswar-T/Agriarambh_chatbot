# M12 — Agronomy Services (Weather, Soil, Satellite)

| | |
|---|---|
| **Status** | 🟡 Partial — Weather and both Soil tools use **real** APIs. Satellite map, plot drawing and layer UI work, but the **NDVI/time-lapse data is mock** |
| **Roles** | Farmer, Owner |
| **Code** | Weather: `src/services/weatherApi.ts`, `src/hooks/useWeather.ts`, `src/screens/WeatherDetailScreen.tsx`, `farmerHome/.../WeatherHero.tsx`. Soil: `src/services/{soilService,soilAdvisoryApi}.ts`, `src/utils/soil/soilAdvisor.ts`, `src/screens/{SoilTest,SoilAdvisory}Screen.tsx`, `src/components/soil/SoilReport.tsx`, `src/types/soil.ts`. Satellite: `src/screens/satelliteMap/**`, `src/components/satelliteMap/*`, `src/context/SatelliteMapContext.tsx`, `src/services/satelliteMapService.ts`, `src/config/mapbox.ts`, root `SATELLITE_MAP_FEATURE.md`, `MAPBOX_SETUP.md`. Location: `src/hooks/useCurrentLocation.ts`, `src/utils/geo/*` |
| **External APIs** | OpenWeather (current + 5-day forecast), SoilGrids (ISRIC, no key), Kaegro soil API, geocode.maps.co, Mapbox |
| **DB** | none used (`soil_tests` exists, unused) |
| **Related** | [M02 Dashboards](M02-dashboards.md), [M07 Crops](M07-crop-management.md), [M03 Land](M03-land-listing-verification.md) |

## 1. Purpose & scope
Give each user **local, practical field intelligence**: what the weather means for today's work, what the soil needs, and what the crop looks like from space.

## 2. Features

### 2.1 Weather
| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M12-F01 | Weather hero on both homes (temp, condition emoji, short advice) | ✅ | location = profile label → GPS address |
| M12-F02 | **Weather & Farm Advisory** screen: temp, humidity, wind, forecast days, **rule-based tips** (spray window, irrigation, fungal risk, rain) | ✅ | Tip cards are built in `WeatherDetailScreen`; one-line advice in `weatherApi` (`getAdvice/getAdvisory`). Rules: rain/thunder → avoid spraying; ≥ 34 °C → irrigate before 9 AM; humidity ≥ 80 % → watch for fungal disease; wind ≥ 25 km/h → no spraying |
| M12-F03 | Refresh on demand | ✅ | `useWeather().refresh` |
| M12-F04 | Weather by **farm coordinates** (currently by place-name string) | ⚪ | |
| M12-F05 | Rain/heat/frost **alerts** and push | ⚪ | |
| M12-F06 | Hourly forecast, rainfall mm, sunrise/sunset, evapotranspiration | ⚪ | |

### 2.2 Soil
| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M12-F10 | **Soil Test** screen: GPS (or default coords) → Kaegro soil API → report | ✅ | `SoilReport`, rating `good/medium/low/danger`, health score 0–100, texture, best crops, **step-by-step fertiliser guide**, amendments, disclaimer — built by pure functions in `soilAdvisor.ts` |
| M12-F11 | **Soil Advisory** (SoilGrids pH, nitrogen, organic carbon at the farm point → amendments + crops) | ✅ | goal: "spend less, grow more" |
| M12-F12 | Save soil test to the farm and compare over time | ⚪ | `soil_tests` table unused |
| M12-F13 | Lab-test upload / Soil Health Card OCR | ⚪ | |
| M12-F14 | Use the farm's saved polygon centroid instead of the phone's GPS | ⚪ | `utils/geo/polygonCentroid.ts` exists |

### 2.3 Satellite monitoring
| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M12-F20 | Full-screen Mapbox satellite map, camera controls, location search | ✅ | `SatelliteMapScreen` |
| M12-F21 | **Draw plot** polygon; live area (acres+guntas); return GeoJSON to Add Land | ✅ | used by [M03](M03-land-listing-verification.md) |
| M12-F22 | Show the farm's saved plot boundary and focus the map on it | ✅ | `farmId` param → `getListingById(farmId).plotGeoJSON` (`lands.geo`) |
| M12-F23 | Layer panel: NDVI, soil moisture, weather, govt (ISRO Bhuvan) toggles, opacity slider | 🧪 | UI works; layers are **mock** WMS URLs |
| M12-F24 | **Timelapse slider** over 5 capture dates | 🧪 | `MOCK_TIMELAPSE_DATES` (Jan–Mar 2024) |
| M12-F25 | Health legend | ✅ | static |
| M12-F26 | Default map centre Purnea, Bihar | 🟡 | should default to the user's state/farm |
| M12-F27 | **Real NDVI / moisture** from Sentinel-2 or a provider, per farm, with history | ⚪ | SAT-1 |
| M12-F28 | Vegetation alerts (NDVI drop) | ⚪ | |

## 3. Business rules
1. Location precedence for weather: stored profile location → device GPS reverse-geocoded → none (hide card, never show another place's weather).
2. Advice must come from **visible rules** (thresholds above) so it can be reviewed by an agronomist; changes to thresholds are code reviews, not silent.
3. Soil reports always show the **disclaimer**: indicative only, a lab test is the reference.
4. Plot area is computed from the polygon (`utils/geo/polygonArea.ts`) and displayed with `formatArea` (acres + guntas).
5. Map needs a valid `MAPBOX_ACCESS_TOKEN`; without it show a clear message (dev warning exists).
6. Never present mock satellite imagery as real — until SAT-1 ships the NDVI controls should be labelled "Preview" or hidden.

## 4. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| KI-11 | NDVI tile URL and time-lapse dates are mock | SAT-1 |
| M12-D1 | Weather keyed by free-text location, not coordinates; ambiguous place names possible | Use lat/lon from profile or farm |
| M12-D2 | API keys in bundle (OpenWeather, Mapbox) | Restrict by app id; proxy weather via Edge Function with caching |
| M12-D3 | `SoilTestScreen` falls back to hard-coded coordinates (`16.59, 74.91`) when permission is denied | Ask for farm selection instead of silently using another place |
| M12-D4 | Two soil sources (Kaegro and SoilGrids) give different numbers for the same place | Pick one primary or explain the difference |
| M12-D5 | Satellite UI state lives in a global context even though only the map screen uses it | Keep (needed to return the drawn polygon), document |
| M12-D6 | `SATELLITE_MAP_FEATURE.md` / `MAPBOX_SETUP.md` partly stale (mentions `SatelliteMapScreen` path and placeholder token) | Fold into this doc |
| M12-D7 | No caching: every Home open refetches weather | Cache 30 min in memory/AsyncStorage |

## 5. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Label or hide mock satellite layers/time-lapse | M12-T0 | P0 | S | No fake imagery presented as real |
| 1 | Use farm/profile coordinates for weather; cache 30 min | M12-T1 | P1 | S | One API call per 30 min per location |
| 2 | Soil Test: select a farm (uses its centroid) and **save** results to `soil_tests`; history view | M12-T2 | P1 | M | Result linked to land; comparison between two dates |
| 2 | Weather alerts (rain tomorrow, heat wave) as notifications | M12-T3 | P1 | M | Opt-in; once per event ([M14](M14-notifications.md)) |
| 2 | Connect crop stage ([M07](M07-crop-management.md)) to weather advice (e.g. flowering + rain → protect) | M12-T4 | P2 | M | Advice mentions stage |
| 3 | **Real NDVI**: Edge Function fetches Sentinel-2 L2A for each farm polygon every 5–10 days, stores `farm_ndvi(land_id, date, mean, min, max, tile_url)`; app shows time-lapse and trend | M12-T5 | P2 | XL | Real index per farm; cloud cover handled |
| 3 | NDVI drop → observation prompt + notification | M12-T6 | P2 | M | |
| 3 | Government layers (ISRO Bhuvan / soil maps) with correct licence/attribution | M12-T7 | P2 | M | |

## 6. Test checklist
- [ ] Weather loads for a city and for a village; denied GPS → profile location used
- [ ] Heavy rain data → "Avoid spraying" tip; ≥ 34 °C → irrigation tip
- [ ] Soil Test with GPS on/off; report sections present; disclaimer visible
- [ ] Draw a 1-acre square → area ≈ 1 ac (40 guntas); redraw/clear works; polygon returns to Add Land
- [ ] Open Satellite from a managed farm → boundary shown at the right place
- [ ] Map token missing → friendly error, no crash

## 7. Definition of Done
Standard DoD plus: API quota impact estimated, caching in place, and any agronomy rule reviewed by a domain expert.
