# M16 — Machinery Rental

| | |
|---|---|
| **Status** | ⚪ Planned — only a "Coming soon" placeholder tab exists |
| **Roles** | Farmer and Owner (both can list and rent; the tab is in both bars) |
| **Code today** | `src/screens/MachineryScreen.tsx`, `src/navigation/MachineryStack.tsx` (tab "Machinery" in `FarmerTabNavigator` and `OwnerTabNavigator`) |
| **Related** | Mirrors [M04 Leasing](M04-leasing.md); uses [M13 Payments](M13-payments.md), [M14 Notifications](M14-notifications.md), [M10 Hub media rules](M10-community-hub.md) |

> This is a **product specification**, not a description of existing code. Everything below is proposed and needs product sign-off before build. The legal text already mentions "machinery" data, and the placeholder promises "tractors, rotavators and other implements, harvesters, mini tractors, borewell machines, goods vehicles, and any other equipment".

## 1. Problem and goal
Small farmers cannot afford tractors/harvesters, and owners of machinery have idle time. **Goal:** a local marketplace to rent equipment (with or without operator) by the hour, day or acre, with trust, scheduling and payment built in.

## 2. Personas
* **Machine owner** (farmer or land owner or a dealer) — lists equipment, sets price/availability, accepts bookings.
* **Renter** (farmer) — searches nearby, books for a date, pays, rates.
* *(Later)* **Operator** — driver/technician for hire.

## 3. MVP feature set (proposed)

| ID | Feature | Pri | Size |
|----|---------|:---:|:----:|
| M16-F01 | Equipment categories: tractor, rotavator/cultivator, harvester, sprayer, seeder, thresher, water pump/borewell rig, trolley/goods vehicle, other | P1 | S |
| M16-F02 | **List equipment**: type, make/model, year, horsepower, implements included, photos/video (reuse media rules), price per hour / day / acre, operator included (Y/N), fuel policy, service radius, location, availability calendar | P1 | L |
| M16-F03 | **Search & browse**: by category, distance (GPS), price, availability on date, rating; list + map | P1 | L |
| M16-F04 | **Equipment detail** with owner profile, rating, photos, rate card, policies | P1 | M |
| M16-F05 | **Book**: pick date/time range or acreage, location of work (use a farm from the app), operator needs; see price breakdown | P1 | L |
| M16-F06 | Owner **accepts/declines** (auto-decline when overlapping); in-app chat or call/WhatsApp | P1 | M |
| M16-F07 | **Payment**: advance via Razorpay at booking confirmation; balance after service; platform fee; refunds/cancellation rules | P1 | L |
| M16-F08 | Booking lifecycle & statuses: `requested → accepted → paid → in_progress → completed | cancelled | disputed` | P1 | M |
| M16-F09 | **Ratings & reviews** both ways | P2 | M |
| M16-F10 | Link a completed booking to a crop activity (e.g. "Ploughing" logged automatically on the cycle in [M07](M07-crop-management.md)) | P2 | M |
| M16-F11 | Notifications for every status ([M14](M14-notifications.md)) | P1 | M |
| M16-F12 | Verification badge for owners (ID + RC book/insurance documents reviewed by Admin) | P2 | L |
| M16-F13 | Damage/dispute flow with photos before/after (reuse closure-handover pattern from [M05](M05-lease-closure.md)) | P2 | L |
| M16-F14 | Hire operator separately; fuel/attachment add-ons | P3 | L |
| M16-F15 | Group booking / cost sharing among neighbours | P3 | L |

## 4. Proposed data model

| Table | Key columns |
|-------|-------------|
| `equipment` | `id, owner_id, category, title, make, model, year, horsepower, description, photos[], price_hour, price_day, price_acre, operator_included, fuel_policy, location (point), service_radius_km, state, district, status (active/paused), verified, created_at` |
| `equipment_availability` | `equipment_id, date_from, date_to, reason (blocked/booked)` |
| `equipment_bookings` | `id, equipment_id, renter_id, owner_id, land_id?, start_at, end_at, unit (hour/day/acre), quantity, rate, amount, platform_fee, status, cancel_reason, created_at` (exclusion constraint to prevent overlapping accepted bookings) |
| `equipment_reviews` | `booking_id, rater_id, ratee_id, stars, comment` |
| `payments` | reuse ([M13](M13-payments.md)) with `context = 'equipment_booking'` |

RLS: public read of `active` equipment; owner CRUD own; booking visible to renter and owner only; status transitions through RPCs (`request_booking`, `accept_booking`, `complete_booking`, `cancel_booking`) to avoid the silent cross-role write problem.

## 5. Screens (proposed `MachineryStackParamList`)
`Machinery` (home: categories, nearby, my bookings, my equipment) · `EquipmentList {category?}` · `EquipmentDetail {id}` · `BookEquipment {id}` · `BookingSummary {bookingId}` · `MyBookings` · `MyEquipment` · `AddEquipment {editId?}` · `OwnerBookingRequests` · `RateBooking {bookingId}` · plus existing `NotificationsCenter`, `Settings`.

## 6. Business rules (proposed)
1. A machine cannot have two overlapping **accepted** bookings.
2. Owner must accept within X hours (e.g. 6) or the request expires and the renter is notified.
3. Cancellation: free until 24 h before start; later cancellations lose part of the advance (set by policy).
4. Renter cannot book their own equipment.
5. The platform fee and who bears gateway fees are decided before build ([M13-T5](M13-payments.md)).
6. Safety: operator licence/insurance statements and a liability disclaimer in the T&C; unsafe-use reports reviewed by Admin.
7. Prices shown in ₹ with the unit; acre-based pricing uses the app's acre/gunta conversion.

## 7. Open questions (need answers before design)
1. Who lists — only individuals, or also dealers/FPOs? Is Admin verification mandatory?
2. Operator included or separate? Fuel included?
3. Payment model: full advance, partial, or cash on completion? Platform commission?
4. Pricing basis: hour/day/acre — which is mandatory for each category?
5. Delivery/transport charge between farms?
6. Insurance and damage liability — who is responsible?
7. Do we need an operator-only (labor) marketplace and does it merge with [M08](M08-labor-work.md)?

## 8. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 0 | Discovery: interview 10 owners + 10 renters; answer §7; define fees and policies | M16-T0 | P2 | M | Signed-off spec |
| 0 | Replace the placeholder text with a **waitlist**/"notify me" capture (stores interest per user) | M16-T0b | P2 | S | Count of interested users per category |
| 1 | Migrations: tables + RLS + RPCs + realtime; seed categories | M16-T1 | P2 | M | Negative RLS tests |
| 1 | `equipmentApi.ts`, `EquipmentContext` (dual-mode) | M16-T2 | P2 | M | Mock + live |
| 1 | Owner: Add/Edit equipment + calendar | M16-T3 | P2 | L | |
| 2 | Renter: browse/search/detail/book + availability check | M16-T4 | P2 | L | |
| 2 | Owner request handling + notifications | M16-T5 | P2 | M | Two-device test |
| 2 | Payments (advance, balance, refund) | M16-T6 | P2 | L | Reconciled in `payments` |
| 3 | Reviews, verification badge, dispute flow, crop-activity link | M16-T7 | P2 | XL | |
| 3 | Operator marketplace decision | M16-T8 | P3 | — | Product decision |

## 9. Test checklist (once built)
- [ ] Two renters request overlapping slots → only one can be accepted
- [ ] Distance filter returns only machines within radius
- [ ] Booking → payment → owner payout flow matches ledger
- [ ] Cancel before/after cutoff applies the correct refund
- [ ] Owner cannot see renters' other bookings; renter cannot edit equipment

## 10. Definition of Done
Standard DoD plus: legal review of rental/liability terms and moderation path for listings (shared with [M10](M10-community-hub.md)).
