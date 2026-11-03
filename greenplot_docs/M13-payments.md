# M13 — Payments (Razorpay)

| | |
|---|---|
| **Status** | 🟡 Partial — secure order-create / verify pipeline is built (test mode). Used in exactly two places: the **security deposit at agreement signing** and a **demo labor-wage payment**. No rent collection, payouts, refunds or receipts |
| **Roles** | Farmer pays; Owner (payee) |
| **Code** | `src/modules/payments/{RazorpayCheckout.tsx,index.ts}`, `src/services/paymentsApi.ts`, `src/config/env.ts` (`RAZORPAY_KEY_ID`, `isRazorpayConfigured`), `supabase/functions/{create-razorpay-order,verify-razorpay-payment,_shared/cors.ts}`, callers: `src/screens/AgreementScreen.tsx`, `src/modules/labor/screens/PaymentSummaryScreen.tsx` |
| **DB** | `payments` (**not in repo SQL**) |
| **Related** | [M04 Leasing](M04-leasing.md), [M05 Closure](M05-lease-closure.md), [M08 Labor](M08-labor-work.md) |

## 1. Purpose & scope
Move money safely inside the app: deposits, rent, wages, settlements — with a server-verified record for every rupee.

## 2. Architecture (what exists)

```
App (AgreementScreen)           Supabase Edge Function                 Razorpay
 paymentsApi.createOrder  ───►  create-razorpay-order                      │
   {amountPaise, context,        • reads payer from the user's JWT          │
    contextId, payeeId}          • creates Order (key id + SECRET) ────────►│
                                 • inserts payments(status='created')        │
                           ◄───  {orderId, amount, currency, keyId}          │
 RazorpayCheckout (WebView, checkout.js) ─── user pays ─────────────────────►│
 onSuccess {order_id, payment_id, signature}                                  │
 paymentsApi.verifyPayment ───►  verify-razorpay-payment                      │
                                 • HMAC-SHA256 check with KEY SECRET           │
                                 • payments → status='paid', paid_at           │
                           ◄───  { verified: true/false }
```
* Checkout is **Razorpay Standard Checkout inside a `react-native-webview`** (no native SDK to link).
* The **Key Secret exists only as an Edge Function secret**; the app has only the public `RAZORPAY_KEY_ID`.
* The caller's **JWT must be attached manually** to `functions.invoke` (`paymentsApi.authHeader`).
* Amount is always **paise** (₹1 = 100 paise).
* `context` ∈ `lease_rent | labor_wage` (the deposit currently reuses `lease_rent`).

## 3. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M13-F01 | Create order via Edge Function (payer from JWT, never from the client body) | ✅ | |
| M13-F02 | WebView checkout with success / dismiss / error callbacks | ✅ | `RazorpayCheckout` |
| M13-F03 | Server-side signature verification and `payments` row update | ✅ | |
| M13-F04 | Security deposit at agreement signing (farmer draws signature → pays → lease activates) | 🟡 | Activation is a client step after the client sees `verified`; see M04-D1. Fallback mock ₹5,000 deposit |
| M13-F05 | Pay/disable behaviour when keys are missing (alert explaining setup) | ✅ | `isRazorpayConfigured` |
| M13-F06 | Labor wage payment (lump sum of pending wages) | 🧪 | Hard-coded laborers; pays the platform account; no payout |
| M13-F07 | Recurring **rent** schedule, reminders, pay-now, receipts | ⚪ | `leases.rent/next_payment` unused |
| M13-F08 | Payment history screen (per user, per lease) | ⚪ | |
| M13-F09 | Refund of security deposit / closure settlement transfer | ⚪ | [M05](M05-lease-closure.md) computes the amount only |
| M13-F10 | **Payouts** to owners / laborers (Razorpay Route, linked accounts, KYC) | ⚪ | Money currently lands in one merchant account |
| M13-F11 | Webhooks for reconciliation (captured, failed, refunded) | ⚪ | Verification today is client-triggered only |
| M13-F12 | Invoices / GST, platform fee | ⚪ | Needs business decision |
| M13-F13 | UPI intent / deep-link, saved methods | ⚪ | |

## 4. Data model (inferred `payments` table — to be committed, DB-1)
`id`, `payer_id` (from JWT), `payee_id`, `context` (`lease_rent`, `labor_wage`, plan: `security_deposit`, `settlement`, …), `context_id` (agreement id / job id / closure id), `amount` (paise), `currency`, `razorpay_order_id` (unique), `razorpay_payment_id`, `status` (`created → paid | failed | refunded`), `created_at`, `paid_at`. RLS target: payer and payee can **read** their rows; **nobody** can write from the client (only Edge Functions with the service role).

## 5. Business rules
1. The client never decides that a payment succeeded; only `verify-razorpay-payment` can mark `paid`.
2. Amount, payer and payee are fixed server-side at order creation; the client cannot change them afterwards.
3. A business action that depends on payment (activate lease, release wage) must be performed by the **server** after seeing `paid` — not by the client.
4. Test mode (`rzp_test_…`) and live mode keys must never be mixed between environments.
5. Every payment must reference the thing it pays for (`context` + `context_id`).
6. Idempotent verification: re-verifying a paid order is a no-op.

## 6. Known issues & tech debt

| ID | Issue | Severity | Fix |
|----|-------|:--------:|-----|
| M04-D1 | Lease activation not tied to payment server-side | **High** | RPC `activate_agreement(agreement_id)` that requires a `paid` row for that agreement |
| M13-D1 | `payments` table, its RLS, and `supabase/functions/README.md` are missing from the repo | High | DB-1 |
| M13-D2 | Fallback mock deposit ₹5,000 | High | M04-T3 |
| M13-D3 | No webhook: if the app dies after paying, money is taken but order stays `created` | High | Webhook `payment.captured` + reconcile job (M13-T2) |
| M13-D4 | Same Edge Function used for deposit/wage; `context` list is a TypeScript union only | Medium | Enum/check constraint in DB |
| M13-D5 | Labor payment screen uses fixture data | Medium | M08 |
| M13-D6 | WebView loads `checkout.razorpay.com`; no certificate pinning/CSP review | Low | Security review |
| M13-D7 | Test-mode only; no live-mode checklist | High (launch) | See §7 launch checklist |

## 7. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Commit `payments` table + RLS + function docs; unique `razorpay_order_id`; status check constraint | M13-T1 | P0 | S | Fresh DB deploy works end to end in test mode |
| 1 | **Server-side activation** after payment (see M04-T1) | M13-T1b | P0 | M | Cannot activate a lease without a paid row |
| 1 | **Webhook** Edge Function for `payment.captured/failed/refunded` with signature check; reconcile job for stuck `created` orders | M13-T2 | P0 | M | Kill the app after paying → state still becomes `paid` |
| 2 | Rent engine: on activation create `rent_schedule` rows (due date, amount) from the offer terms; "Pay rent" and reminders; mark paid via payments | M13-T3 | P1 | XL | Overdue/renewal items appear in [M02](M02-dashboards.md); receipts available |
| 2 | Payment history + downloadable receipt (PDF) | M13-T4 | P1 | M | List by lease; receipt has order/payment ids |
| 2 | Decide commercial model: platform fee, who pays gateway fees, GST invoices | M13-T5 | P0 (product) | S | Written decision |
| 2 | Razorpay Route onboarding for owners (linked account + KYC) and automatic transfer of rent/deposit | M13-T6 | P1 | XL | Owner receives funds; ledger reconciles |
| 3 | Refund of deposit and settlement transfer from [M05](M05-lease-closure.md) | M13-T7 | P2 | L | Closure cannot finish until payment or explicit waiver |
| 3 | Laborer wage payouts (UPI) | M13-T8 | P2 | XL | Per laborer per day totals paid |
| 3 | Live-mode launch: KYC, live keys per environment, 1-rupee live test, runbook | M13-T9 | P0 for launch | M | Checklist signed off |

## 8. Test checklist
- [ ] Test card success → `payments.status = paid`; lease activates once
- [ ] Failed card → no activation; retry reuses the drawn signature
- [ ] Close the app after paying → after relaunch the lease is active (needs M13-T2)
- [ ] Tamper: wrong signature → `verified:false`, nothing changes
- [ ] Client tries to insert/update `payments` directly → denied
- [ ] User A cannot read User B's payments
- [ ] No Razorpay key → friendly message, no crash

## 9. Definition of Done
Standard DoD plus: reconciliation report matches Razorpay dashboard for the test period, and a security review of every code path that moves money.
