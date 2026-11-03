# M04 — Leasing Marketplace & E-Agreements

| | |
|---|---|
| **Status** | 🟡 Partial — the **downstream** half (apply → approve → sign + deposit → active lease) is built, realtime and atomic. The **upstream** half (owner creates offers; farmer discovers lands) has **no entry point** in the current UI since the Farm Management release |
| **Roles** | Owner (offers, approve/reject, view agreements), Farmer (apply, sign, view leases) |
| **Code** | `src/context/LeaseContext.tsx`, `src/services/leaseApi.ts`, `src/types/lease.ts`, `src/constants/{leaseTypes,leaseTermsAndConditions}.ts`, `src/screens/{LeaseApplication,LeaseStatus,LeaseAgreements,AgreementDetails,Agreement,LeaseTypeDetails,LeaseDetailView,LeaseConfirmation,CompareLeases,LeaseLand}Screen.tsx`, `src/screens/owner/{AddLeaseOffer,LeaseRequests}Screen.tsx`, `src/screens/farmer/components/LeaseOptionsSection.tsx`, `src/screens/leases/myActiveLeases/**`, `src/components/organisms/SignaturePadModal.tsx` |
| **DB** | `lease_offers`, `lease_requests`, `lease_agreements`, `leases`, RPC `approve_lease_request`, bucket `signatures` |
| **Related** | [M03 Land](M03-land-listing-verification.md), [M05 Closure](M05-lease-closure.md), [M13 Payments](M13-payments.md), [M06 Farm Management](M06-farm-management.md) |

> ### ⚠ Product decision needed (LEASE-1)
> After commit `8408908 "Farm Management — Farmer and Owner"`:
> * New lands go to **verification**, not to the marketplace ([M03](M03-land-listing-verification.md)).
> * No code navigates to `AddLeaseOffer` or `LeaseLand`, and `AllAvailableLands` is only reachable via an unused action key. Farmers cannot browse lands that carry lease offers.
> * `LeaseOptionsSection` (the Apply button) is shown on `FarmDetail` only for **non-managed** farms, and `FarmDetail` is only reachable for managed farms.
> * The home activity feed even labels lease requests as "Management request …".
>
> So today the lease code runs only for **data that already exists**. Decide: **(A)** retire the marketplace and fold agreements into Farm Management, or **(B)** keep both models and reconnect the entry points (tasks in §9). The rest of this document describes the code as built.

## 1. Purpose & scope
A transparent way for an owner to offer land under a chosen **lease type**, for a farmer to apply, and for both to end up with a **signed digital agreement** and an **active lease** — with no double-booking of the same land.

**In scope:** lease types and their term forms, offers, applications, approval, agreement text, farmer drawn signature + security-deposit payment, active lease list, comparison/education screens.
**Out of scope:** closure ([M05](M05-lease-closure.md)), recurring rent collection ([M13](M13-payments.md) PAY-1).

## 2. Lease types (single source of truth: `constants/leaseTypes.ts`)

| `type_id` | Name | Meaning | Owner risk (1–5) | Term fields (owner fills) |
|-----------|------|---------|:-:|--------------------------|
| `cash_rent` | Cash Rent | Lump-sum cash before sowing | 1 | total cash, pay-by |
| `fixed_rent` | Fixed Rent | ₹/acre/year in installments | 2 | rate per acre, installments (full / 2 / 3) |
| `crop_share` | Crop Share | Physical harvest split | 3 | harvest split %, input-cost split %, crops allowed |
| `revenue_share` | Revenue Share | % of sale money | 4 | owner %, input-cost split % |
| `flexible_share` | Flexible Share | Base rent + upside bonus | 3 | base rate, bonus %, threshold |
| `custom` | Custom | Free-form clauses per crop | 3 | crops, clauses |

Every offer also carries `tenure`, `available_from`, and optionally `securityDeposit`. The form is **rendered dynamically from each type's `fields` schema** — to add a lease type, add one entry here (plus the DB enum `lease_type_id`), not a new screen. `buildAgreementTerms(offer)` and `summarizeOffer(offer)` produce the agreement clauses and one-line summary.

## 3. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M04-F01 | Six lease types with dynamic term forms | ✅ | `leaseTypes.ts` |
| M04-F02 | Owner creates one or more offers for a land (draft-land path: create land + offer together) | 🚧 | `AddLeaseOfferScreen` exists but **unreachable** |
| M04-F03 | Farmer sees real offers on a land and applies (confirmation alert, one active lease blocks re-apply) | 🚧 | `LeaseOptionsSection`; only on non-managed `FarmDetail` |
| M04-F04 | Owner sees pending requests (`LeaseRequestsScreen`), approve / reject | ✅ | Reached from Owner Home "pending requests" card |
| M04-F05 | **Atomic approval**: RPC locks land, accepts one request, auto-rejects other pending requests on the same land, creates the agreement; second approver gets "already taken" error | ✅ | `approve_lease_request`; fixed "multiple farmers approved for one land" bug |
| M04-F06 | Owner is auto-marked as signed on approval; agreement goes to farmer (`status = awaiting`) | ✅ | |
| M04-F07 | Farmer reads full Terms & Conditions (15 role-tagged clauses) **before** the Sign button unlocks | ✅ | `leaseTermsAndConditions.ts`; `AgreementScreen` |
| M04-F08 | Farmer **draws signature** → uploaded to `signatures` bucket | ✅ | `SignaturePadModal` |
| M04-F09 | Farmer **pays security deposit** (Razorpay); only after server-verified payment is the signature recorded and the lease activated | 🟡 | Deposit falls back to a **mock ₹5,000** when the offer has none (see §8) |
| M04-F10 | Active lease created; land set to `leased`; start date = owner's "available from" if a real date | ✅ | in `leaseApi.signAgreementAsFarmer` |
| M04-F11 | Agreement list for both roles (`LeaseAgreementsScreen`) and detailed view with contact call buttons, payment schedule (tenant only) | ✅ | |
| M04-F12 | Farmer "My Active Leases" combining leases, awaiting agreements and requests | ✅ | `useMyActiveLeases` |
| M04-F13 | Lease type education: details, detail view, confirmation, compare side-by-side | 🟡 | Uses **separate hard-coded content** with kebab-case ids (`fixed-rent`), duplicating `leaseTypes.ts` |
| M04-F14 | Realtime sync across devices | ✅ | `leaseApi.subscribe` → refetch |
| M04-F15 | Rent schedule, reminders, receipts, renewal | ⚪ | `leases.rent/next_payment/end_date` exist but are never populated |

## 4. End-to-end flow (as built)

```
Owner: add offer ─► Farmer: apply ─► Owner: Approve
                                         │ RPC approve_lease_request (atomic)
                                         ▼
         request=accepted · other requests=rejected · land locked · agreement(awaiting, owner signed)
                                         ▼
Farmer: open agreement ─► read T&C ─► tick agree ─► draw signature ─► pay deposit (Razorpay)
                                         │ verify-razorpay-payment OK
                                         ▼
 agreement=active · lease row created · land.status='leased' · both apps update live
```

## 5. Screens and routes

| Screen | Route | Stack(s) | Purpose |
|--------|-------|----------|---------|
| `LeaseRequestsScreen` | `LeaseRequests` | OwnerHome | Approve / reject |
| `AgreementScreen` | `AgreementSign` | FarmerHome, OwnerHome | Read, sign, pay |
| `LeaseAgreementsScreen` | `LeaseAgreements` | FarmerHome, OwnerHome | List |
| `AgreementDetailsScreen` | `AgreementDetails` | FarmerHome, OwnerHome, MyProperties | Terms, parties, schedule, actions (e.g. request closure) |
| `MyActiveLeasesScreen` | `MyActiveLeases` | FarmerHome | Farmer's leases |
| `LeaseStatusScreen` | `LeaseStatus` | FarmerHome | Application status |
| `LeaseApplicationScreen` → `LeaseTypeDetails` → `LeaseDetailView` → `LeaseConfirmation`; `CompareLeasesScreen` | same names | FarmerHome / MyProperties | Education / comparison |
| `AddLeaseOfferScreen` | `AddLeaseOffer` | OwnerHome, MyProperties | **Unreachable** |
| `LeaseLandScreen` | `LeaseLand` | OwnerHome | **Unreachable**, hard-coded demo lands |
| `AllAvailableLandsScreen` | `AllAvailableLands` | FarmerHome | **Effectively unreachable** |

## 6. Data model
See [02 §3](../02-database-backend.md). Key points:
* `lease_offers.terms` (jsonb) holds the type-specific values plus optional `securityDeposit`.
* `lease_requests` and `lease_agreements` **denormalise** titles/names (so lists render without joins).
* `lease_agreements.full_terms` (jsonb array of `{label, value}`) is a snapshot taken at approval; later edits to the offer never change a signed agreement.
* Types: `LeaseRequest`, `Agreement`, `ActiveLease` in `src/types/lease.ts`.
* `leases` also stores `rent`, `next_payment`, `end_date` (unused today).

## 7. State and API
`LeaseContext` is **dual-mode** ([01 §5](../01-architecture.md)). Live mode: `leaseApi.fetchAll()` loads offers (limit 500), requests, agreements, leases; any Postgres change triggers a refetch. Exposed: `offers, addOffer, removeOffer, getOffersByLand, requests, applyForLease, getRequestsForFarmer, approveRequest, rejectRequest, agreements, getAgreementById, signAgreementAsFarmer, activeLeases` + the closure API ([M05](M05-lease-closure.md)).

## 8. Business rules
1. One land can have many offers but **only one approved request**; approval locks the land immediately (before signing).
2. `approveRequest` must **throw** if the land is taken or the request already decided; the UI shows the message (never a false success).
3. A farmer with an *active* lease on the same offer cannot apply again; a closed lease does not block.
4. The farmer must read the T&C (scroll + tick) before signing.
5. The lease becomes active only when **both** parties have signed **and** the deposit payment verified server-side.
6. A signed agreement's terms are immutable (snapshot).
7. Lease start date = owner's "available from" when it parses as a real date, else today.
8. Only the **tenant** sees a payment schedule; the owner reviews it.

## 9. Known issues & implementation plan

### Known issues
| ID | Issue | Fix |
|----|-------|-----|
| LEASE-1 | Marketplace entry points disconnected (see top box) | Decide A/B |
| SEC-3 / KI-5 | `lease_agreements` policy lets either party update any column; farmer could set `owner_signed`/`status` | RPC for signing; column-level policy |
| M04-D1 | **Deposit can be bypassed**: `signAgreementAsFarmer` is a client call after a client-side "verified" flag; nothing server-side ties payment to activation | Move activation into a SECURITY DEFINER RPC that checks a `paid` row in `payments` for that agreement |
| M04-D2 | Fallback **mock deposit ₹5,000** (`MOCK_DEPOSIT_RUPEES`) charged when the offer has none | Require `securityDeposit` in the offer form; remove fallback |
| M04-D3 | `applyForLease`, `rejectRequest`, `signAgreementAsFarmer` use `.then(refetch).catch(() => {})` — failures are silent (and Supabase returns `{error}` instead of throwing) | Return promises, check `error`, show messages (KI-21) |
| M04-D4 | Duplicate lease-type content: `LeaseTypeDetails`, `LeaseDetailView`, `LeaseConfirmation`, `CompareLeases` each embed their own static data | Drive all four from `LEASE_TYPES` |
| M04-D5 | `leases.next_payment`, `end_date`, `rent` never set | PAY-1 / M04-T7 |
| M04-D6 | Offers fetched with `limit(500)` | PERF-1 |
| M04-D7 | In the farmer activity feed, lease requests are titled "Management request …" — collides with the real Farm Management requests ([M06](M06-farm-management.md)) | Rename copy per decision LEASE-1 |

### Plan
| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 0 | Product decision LEASE-1 (A retire / B keep) | M04-T0 | P0 | S | Written decision in this doc and roadmap |
| 1 | Server-side activation RPC checking paid deposit; lock `lease_agreements` updates | M04-T1 | P0 | M | Calling update directly cannot activate; unpaid agreement stays `awaiting` |
| 1 | Await/handle errors in all LeaseContext live writes | M04-T2 | P0 | M | Forced failure produces a visible error and no stale UI |
| 1 | Make `securityDeposit` mandatory in offers; remove mock fallback | M04-T3 | P0 | S | Cannot publish an offer without a deposit amount (₹0 allowed explicitly) |
| 2 (if B) | Reconnect owner flow: "Add lease offer" button on Land Details for lands the owner wants to lease directly | M04-T4 | P1 | M | Offer appears to farmers in realtime |
| 2 (if B) | Farmer land discovery: filters (state, district, soil, crop, lease type, price), map view, saved lands | M04-T5 | P1 | L | Search returns only approved public lands (needs SEC-4) |
| 2 | Unify education screens on `LEASE_TYPES`; delete `LeaseLandScreen` | M04-T6 | P2 | M | One source of lease-type copy; no duplicate constants |
| 2 | On activation set `end_date` (start + tenure) and first `next_payment`; show in My Leases | M04-T7 | P1 | M | Dates present for new leases |
| 3 | Renewal flow before `end_date` | M04-T8 | P2 | L | Owner/farmer get a renew action 30 days before expiry |
| 3 | PDF export / share of signed agreement | M04-T9 | P2 | M | Both parties can download a PDF with signatures |
| 3 | Owner e-signature (drawn) to match the farmer's | M04-T10 | P2 | M | Both signatures captured and stored |
| (if A) | Migrate existing agreements to Farm Management terms; hide unused screens | M04-T11 | P1 | L | No dead routes; data preserved |

## 10. Test checklist
- [ ] Two farmers apply to the same land; owner approves A → B auto-rejected; owner trying to approve B gets a clear error
- [ ] Approval on one phone → farmer's phone shows "Sign agreement" without refresh
- [ ] Sign button locked until T&C read + tick
- [ ] Payment cancelled → signature kept for retry, lease **not** active
- [ ] Payment success but verify fails → lease **not** active
- [ ] Farmer kills app mid-payment → no half-active lease
- [ ] Owner cannot sign as farmer; farmer cannot mark `owner_signed` (raw API test)
- [ ] Each lease type: offer form validates fields, summary line and 15 clauses read correctly
- [ ] Closed lease no longer blocks a new application

## 11. Definition of Done
Standard DoD plus: negative RLS tests on all four lease tables; payment-to-activation integrity proven server-side.
