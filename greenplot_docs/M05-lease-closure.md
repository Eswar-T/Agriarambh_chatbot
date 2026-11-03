# M05 — Lease Closure / Early Termination

| | |
|---|---|
| **Status** | ✅ Live — complete 6-step workflow with audit trail and realtime. Hardening items listed below |
| **Roles** | Farmer (requests, participates), Owner (responds, confirms, **finalises**) |
| **Code** | `src/screens/leaseClosure/{RequestLeaseClosureScreen,ClosureRequestedScreen,LeaseClosureScreen}.tsx`, `src/constants/leaseClosure.ts`, `src/types/lease.ts`, `src/services/leaseClosureApi.ts`, closure section of `src/context/LeaseContext.tsx` |
| **DB** | `lease_closures`, `lease_closure_history`, bucket `farm-media` (handover photos), `notifications` |
| **Related** | [M04 Leasing](M04-leasing.md), [M07 Crops (standing crop)](M07-crop-management.md), [M14 Notifications](M14-notifications.md) |

## 1. Purpose & scope
End a lease before (or at) its term **fairly and with evidence**: notice, a money settlement both agree on, a decision about any crop still in the ground, and a photo-backed handover of the land.

**In scope:** request, owner response, notice period, settlement calculation, standing-crop decision, handover photos/notes/confirmations, finalise or cancel, history log.
**Out of scope:** actually moving money for the settlement (shown as an amount only), legal dispute handling.

## 2. The six steps and statuses

| Step | What happens | Who | Status after |
|------|--------------|-----|--------------|
| 1 Request | Farmer picks a reason, comments, proposed handover date, notice (30/60/90 days) | Farmer | `requested` |
| 2 Notice | `eligible_closure_date = requested_at + notice days`; owner may **waive** it | Owner | — |
| 3 Owner response | Accept · Reject · Propose new date · Accept **with settlement required** | Owner | `under_review` / `settlement_pending` / `rejected` |
| 4 Settlement | Pending rent, water, electricity, other expenses, security deposit, deductions → computed amount; both **confirm** | Both | `settlement_pending` → `handover_pending` |
| 5 Standing crop | Choose one of 4 options (below) | Both | — |
| 6 Handover | Each side uploads photos + notes and confirms; when both confirmed → `ready_for_closure`; **owner** presses **Close lease** | Both / Owner | `handover_pending` → `ready_for_closure` → `closed` |
| — | Farmer or owner can cancel before closing | Either | `cancelled` |

Statuses (`LeaseClosureStatus`): `requested, under_review, settlement_pending, handover_pending, ready_for_closure, closed, rejected, cancelled`.

**Standing-crop options:** continue until harvest · harvest by an agreed deadline · owner takes possession before harvest · mutual agreement (free-text notes).

**Owner responses (`OwnerClosureResponse`):** `accepted, rejected, proposed_new_date, accepted_with_settlement`.

## 3. Features

| ID | Feature | Status |
|----|---------|:------:|
| M05-F01 | Request closure with reason list, comments, proposed date, notice period, security deposit snapshot | ✅ |
| M05-F02 | One open closure per lease (a second request returns the open one) | ✅ |
| M05-F03 | Owner response (4 options) with comments / proposed date | ✅ |
| M05-F04 | Notice period computation and owner waiver | ✅ |
| M05-F05 | Settlement form + **pure** calculation `computeSettlement()` — nothing auto-deducted; requires explicit confirmation | ✅ |
| M05-F06 | Standing crop resolution (4 options, deadline, notes) | ✅ |
| M05-F07 | Handover: photos (upload), notes, per-party confirmation | ✅ |
| M05-F08 | Owner-only **Close lease** (confirmation alert); farmer sees outcome | ✅ |
| M05-F09 | Cancel closure | ✅ |
| M05-F10 | Audit trail `lease_closure_history` (15 action types, shown as activity) | ✅ |
| M05-F11 | Notification to the other party on request and on owner response | 🟡 | cross-role insert, likely RLS-blocked — see KI-14 |
| M05-F12 | "Action required" vs "Recent activity" split on Owner Home using `closureNeedsOwnerAction()` | ✅ |
| M05-F13 | Money transfer of settlement via Razorpay | ⚪ |
| M05-F14 | Closing a lease also completes the farmer's open crop cycle | ⚪ |
| M05-F15 | PDF closure certificate | ⚪ |

## 4. Settlement math (`constants/leaseClosure.ts`)

```
otherExpenses  = Σ otherExpenses[].amount
totalPending   = pendingRent + pendingWater + pendingElectricity + otherExpenses
totalDeductions= Σ deductions[].amount
depositRefund  = max(0, securityDeposit − totalDeductions)
finalAmount    = depositRefund − totalPending
payer          = finalAmount > 0 → owner pays farmer
                 finalAmount < 0 → farmer pays owner
                 0 → none
```
Notice is satisfied when `noticeWaived` or today ≥ `eligible_closure_date`.

## 5. Screens and navigation

| Screen | Route | Notes |
|--------|-------|-------|
| `RequestLeaseClosureScreen` | `LeaseClosureRequest { leaseId }` | Step 1 form (farmer) |
| `ClosureRequestedScreen` | `ClosureRequested { closureId }` | **Every entry point lands here first** (step 1 view + owner response) |
| `LeaseClosureScreen` | `LeaseClosure { closureId }` | Step 2 onward; reached only by pushing from `ClosureRequested`, so Back returns to it |

Registered in `FarmerHomeStack`, `OwnerHomeStack` and `MyPropertiesStack` — keep param types identical. Entry points: Agreement Details (`LeaseClosureRequest` to start, `ClosureRequested` to resume), Farmer Home and Owner Home activity rows, and Owner Home "closure actions" items (all open `ClosureRequested`).

## 6. Data model
`LeaseClosure` fields map 1:1 to `lease_closures` columns (snake_case): ids and names, `status`, `reason, comments, proposed_handover_date, requested_at`, `notice_period_days, notice_waived, eligible_closure_date`, `owner_response, owner_response_comments, owner_proposed_date, owner_responded_at`, `pending_rent, pending_water, pending_electricity, other_expenses (jsonb), security_deposit, deductions (jsonb), settlement_confirmed`, `standing_crop_option, standing_crop_deadline, standing_crop_notes, standing_crop_resolved`, `farmer_photos[], owner_photos[], farmer_handover_notes, owner_handover_notes, farmer_confirmed_at, owner_confirmed_at`, timestamps. `lease_closure_history`: `closure_id, action, performed_by, user_role, details`.

## 7. Business rules
1. At most one open closure (`not in closed/rejected/cancelled`) per lease.
2. Only the **owner** can finalise, and only from `ready_for_closure` (both handover confirmations present).
3. Settlement amounts are **proposals** until both parties confirm; nothing is deducted automatically.
4. After settlement is confirmed **and** the standing crop is resolved the status moves to `handover_pending`.
5. Finalising sets `lease_closures.status='closed'`, `leases.status='closed'` and `lands.status='active'` (land becomes available again; shown under *Completed* in Properties).
6. Each party can edit only their own section (`editable = role === who`).
7. Every state change writes a history row.

## 8. Known issues & tech debt

| ID | Issue | Impact | Fix |
|----|-------|--------|-----|
| M05-D1 | `finalizeClosure` makes three separate writes (closure, lease, land) — not atomic; partial failure leaves inconsistent state | Land stuck `leased` | One `SECURITY DEFINER` RPC `finalize_lease_closure` |
| M05-D2 | `leases.status = 'closed'` but `lease_status` enum in `schema.sql` is `pending/active/expired/cancelled` — **no `closed`**. Works only if the live DB differs | Update fails silently | Confirm enum in DB; add migration |
| M05-D3 | All live writes are `.then(refetch).catch(() => {})`; `requestClosure` returns the literal `'pending'` in live mode (no real id) | Silent failures; navigation to a fake id | Await and return real id |
| M05-D4 | Notifications inserted from the client for the **other** user — blocked by `notif own` policy | Counterparty not told | Trigger on `lease_closures` / history (NOT-1) |
| M05-D5 | Cross-party writes to `lease_closures` (farmer ↔ owner updating one row) depend on RLS that is not in the repo | Possible silent denial | Export policies (DB-1); move to RPCs |
| M05-D6 | Handover photos live in a **public** bucket | Privacy | Private bucket + signed URLs (SEC-6) |
| M05-D7 | Closing a lease does not touch the farmer's crop cycle ([M07](M07-crop-management.md)); standing-crop choice is informational | Orphan cycles | M05-T4 |
| M05-D8 | `LeaseClosureScreen` is 527 lines and handles steps 2–6 in one file | Maintainability | Split per step |

## 9. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Verify live enum/policies; migration for `closed` status; export closure policies | M05-T1 | P0 | S | Closure finalise works end to end in staging |
| 1 | RPC `finalize_lease_closure` (atomic) and RPCs for owner/farmer role-checked transitions | M05-T2 | P0 | M | Raw table updates denied; RPC enforces role and state order |
| 1 | Await writes; `requestClosure` returns real id; show errors | M05-T3 | P0 | M | Failure → alert; success → navigates to real closure |
| 2 | On finalise, close or hand over the crop cycle per the standing-crop option (continue → keep open until harvest) | M05-T4 | P1 | M | Cycle state matches the chosen option |
| 2 | Notifications via DB trigger for every step (request, response, settlement, handover, closed) + push | M05-T5 | P1 | M | Counterparty notified within seconds |
| 2 | Private bucket for handover photos | M05-T6 | P1 | S | Photos only viewable by the two parties |
| 3 | Settlement payment through Razorpay (payer → payee) with receipt | M05-T7 | P2 | L | `payments` row linked to closure; closure blocks until paid or waived |
| 3 | PDF closure certificate | M05-T8 | P2 | M | Downloadable by both |
| 3 | Reminders when handover date or notice date arrives | M05-T9 | P2 | S | Push on the day |

## 10. Test checklist
- [ ] Farmer requests closure; owner sees an "Action required" card
- [ ] Second request on the same lease returns the first
- [ ] Notice 30 days: owner cannot finalise before eligible date unless waived
- [ ] Settlement: pending ₹10,000, deposit ₹20,000, deductions ₹2,000 → refund ₹18,000, final +₹8,000, payer owner
- [ ] Negative final amount → payer farmer
- [ ] Each of 4 standing-crop options saves and shows in history
- [ ] Farmer cannot press Close lease; owner cannot confirm farmer handover
- [ ] After close: lease listed as *Completed*, land `active`, Back from step 2 returns to step 1
- [ ] Phone offline mid-step → no partial state after reconnect

## 11. Definition of Done
Standard DoD plus: state machine transitions covered by unit tests (pure function over `LeaseClosure`), and RLS negative tests for each transition.
