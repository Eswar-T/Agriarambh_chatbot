# M14 — Notifications & Activity Feed

| | |
|---|---|
| **Status** | 🟡 Partial — in-app notification list with realtime refresh and a home "Recent activity" feed are built. **No push notifications**, almost no event producers, and rows are never marked read |
| **Roles** | Farmer, Owner |
| **Code** | `src/services/notificationsApi.ts`, `src/screens/NotificationsCenterScreen.tsx`, `src/utils/activityFeed.ts`, `farmerHome/hooks/useFarmerHome.ts` and `ownerHome/hooks/useOwnerHome.ts` (activity merge), closure inserts in `src/services/leaseClosureApi.ts`, `src/constants/leaseClosure.ts` (history labels) |
| **DB** | `notifications(id, user_id, type, title, body, read, created_at)`; `lease_closure_history` |
| **Related** | [M05 Closure](M05-lease-closure.md), [M04 Leasing](M04-leasing.md), [M06 Farm Mgmt](M06-farm-management.md), [M10 Hub](M10-community-hub.md) |

## 1. Purpose & scope
Tell the right person, at the right time, that something needs their attention — inside the app and (planned) on the lock screen.

## 2. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M14-F01 | **Notifications Center** list (newest first, unread accent, type-based icons) | ✅ | Reachable from the bell on every tab (route `NotificationsCenter` in every stack) |
| M14-F02 | Realtime refresh when a row is inserted/updated | ✅ | `notificationsApi.subscribe(userId, cb)` with a **unique channel name per mount** |
| M14-F03 | Home **Recent activity** (5 latest) merging notifications with locally derived events (lease request sent/accepted/rejected, agreement signed, closure requested/closed) | ✅ | `activityFeed.ts` + home hooks |
| M14-F04 | Visual mapping by `type`: `payment`, `lease`, `job`, `disease`, default | ✅ | `activityVisual()` |
| M14-F05 | Owner Home "Action required" vs "Recent activity" for closures | ✅ | `closureNeedsOwnerAction()` |
| M14-F06 | Notification inserts for lease closure request and owner response | 🟡 | Client inserts a row for the **other** user; blocked by the repo's `notif own` policy unless live DB differs (KI-14) |
| M14-F07 | Producers for: lease request received, request approved/rejected, agreement ready to sign, agreement active, management request status changes, crop activity due/overdue, payment received, weather alerts, price alerts, Hub likes/comments | ⚪ | none exist |
| M14-F08 | Mark as read / mark all read; unread badge on the bell | ⚪ | `read` is never updated; no badge |
| M14-F09 | **Push notifications** (FCM Android, APNs iOS), device-token registry, deep links | ⚪ | |
| M14-F10 | Notification preferences (per type, quiet hours, language) | ⚪ | Settings row "Notifications" has no action |
| M14-F11 | Tap a notification → open the related screen | ⚪ | The cards in `NotificationsCenterScreen` have no `onPress` handler; home feed rows do navigate |

## 3. Target design

### 3.1 Event → notification producers (all server-side)
Create notifications **in the database**, not from the app, so RLS and offline behaviour don't matter:

| Source event | Recipient | `type` | Deep link |
|--------------|-----------|--------|-----------|
| `lease_requests` insert | owner | `lease` | `LeaseRequests` |
| `lease_requests` update → accepted/rejected | farmer | `lease` | `AgreementSign` / `LeaseStatus` |
| `lease_agreements` signed both | both | `lease` | `AgreementDetails` |
| `lease_closures` insert/update (each status/owner response) | counterparty | `lease` | `ClosureRequested` |
| `management_requests` status change (Admin) | farmer (+ owner on approval) | `management` | `ManagementRequestDetails` |
| `lands.verification_status` change (Admin) | owner | `land` | `PropertyDetails` |
| `farm_activities` overdue (daily job) | farmer | `crop` | `ManagedFarmDashboard` |
| `payments` → paid | payer + payee | `payment` | receipt |
| `comments` / `post_likes` insert | post author | `community` | `Hub` post |
| Weather / price alert jobs | subscribed user | `weather` / `market` | detail screen |

Use `SECURITY DEFINER` trigger functions that `insert into notifications`. Add `data jsonb` (route + params) and `read_at timestamptz` to the table.

### 3.2 Push pipeline
`device_tokens(user_id, token, platform, app_version, updated_at)` ← app registers on login (and removes on logout). An Edge Function (invoked by a DB webhook on `notifications` insert) sends via FCM/APNs; payload carries `data.route/params`. App opens the right screen on tap, even from a killed state.

## 4. Business rules
1. A user reads and updates only their own notifications.
2. Notifications are created by the server, one per recipient per event; duplicates for the same event are not allowed (use `event_key` unique).
3. Push respects user preferences and quiet hours; critical items (payments, closure deadlines) may bypass quiet hours.
4. Language: title/body stored in the recipient's language (or a key + params resolved on the device).
5. Deleting an account removes its tokens and notifications.

## 5. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| KI-14 | Cross-role inserts from `leaseClosureApi` (result unchecked) | Replace with DB triggers (M14-T1) |
| M14-D1 | No unread concept (`read` never set) and no badge | M14-T3 |
| M14-D2 | Notification cards are not tappable | M14-T3 |
| M14-D3 | Home feed derives events client-side → can disagree with Notifications Center | Use one source of truth (server events) |
| M14-D4 | Two timestamps/labels sources (`relativeTime` helpers exist in several files) | Share one util |
| M14-D5 | Settings "Notifications" row is dead | M14-T6 |
| M14-D6 | Realtime channel per mount; many channels open at once (leases, closures, lands, activities, notifications) | Monitor connection count; consolidate if limits are hit |

## 6. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Verify live `notifications` policies/triggers; commit them; remove client cross-role inserts | M14-T1 | P0 | S | Closure events notify the other party for real |
| 1 | Add `data jsonb`, `read_at`, `event_key` columns | M14-T2 | P1 | S | Migration in repo |
| 2 | Trigger functions for lease request / approval / sign / closure events (table in §3.1) | M14-T3a | P1 | M | Every row of the table fires in a two-device test |
| 2 | Tap → deep link; mark read on open; "Mark all read"; unread badge on the bell | M14-T3 | P1 | M | Badge count equals unread rows |
| 2 | Triggers for management requests, land verification, payments | M14-T4 | P1 | M | Admin portal actions notify within seconds |
| 2 | **Push**: FCM/APNs setup, `device_tokens`, send function, deep-link handling, Android 13 permission prompt, iOS capabilities | M14-T5 | P1 | XL | Push received with app killed; opens correct screen |
| 2 | Preferences screen (types on/off, quiet hours) | M14-T6 | P2 | M | Respected by sender |
| 3 | Scheduled jobs: overdue crop activities, rent due, price/weather alerts | M14-T7 | P2 | L | Daily digest option |
| 3 | WhatsApp/SMS fallback for critical events | M14-T8 | P2 | L | Cost-capped |

## 7. Test checklist
- [ ] Owner receives "lease request" while the app is closed (after push)
- [ ] Notification list updates live without refresh
- [ ] Tap opens the right screen with the right params
- [ ] Mark read persists; badge decrements
- [ ] User A never sees User B's notifications
- [ ] Logout removes the device token; a logged-out device gets no push
- [ ] Recipient language is used

## 8. Definition of Done
Standard DoD plus: every event type documented in §3.1 with a passing two-device test, and push verified on a physical Android and iOS device.
