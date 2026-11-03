# M01 — Authentication & Onboarding

| | |
|---|---|
| **Status** | 🟡 Partial — works, but **not secure** (no real OTP). Blocks public launch |
| **Roles** | Farmer, Owner |
| **Code** | `src/context/AuthContext.tsx`, `src/screens/ProfileOnboardingScreen.tsx`, `src/services/{supabase,authService}.ts`, `src/types/auth.ts`, `src/utils/validation.ts`, `src/navigation/AppNavigator.tsx` |
| **DB** | `profiles`, trigger `handle_new_user`, RPC `save_own_profile`, `supabase/add_terms_acceptance.sql`, `add_avatar_url_to_save_profile.sql`, `repair_missing_profiles.sql` |
| **Related** | [M15 Settings/Legal](M15-settings-localization-legal.md), [02 Database](../02-database-backend.md) |

## 1. Purpose & scope
Get a person into the app in under a minute as either a **Farmer** or a **Land Owner**, keep them signed in, and record that they accepted the Terms & Privacy Policy.

**In scope:** sign-up, login, session restore, logout, profile read/edit, terms acceptance, role routing.
**Out of scope:** social login, email/password, KYC, admin accounts.

## 2. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M01-F01 | One-screen onboarding (name, role, phone, WhatsApp flag, location, terms) | ✅ | `ProfileOnboardingScreen`; GPS fills location/district/state |
| M01-F02 | Returning-user login with phone number only | 🟡 | **No OTP** — see Known issues |
| M01-F03 | Phone validation (Indian mobile, 10 digits, starts 6–9, not repeated digit) | ✅ | `utils/validation.ts` |
| M01-F04 | Role chosen at sign-up and fixed; routes to Farmer or Owner tab bar | ✅ | `AppNavigator.MainNavigator` |
| M01-F05 | Duplicate protection: "You already registered with this number as a farmer/owner. Please log in." | ✅ | profile lookup by phone variants `98…`, `9198…`, `+9198…` |
| M01-F06 | Terms & Privacy acceptance (checkbox enabled only after opening the legal text); timestamp stored | ✅ | `profiles.accepted_terms_and_policies` |
| M01-F07 | Session persistence and restore on launch | ✅ | Supabase session in AsyncStorage; splash waits until `authReady` |
| M01-F08 | Safe logout (4 s timeout, always clears local state, spinner) | ✅ | `AuthContext.logout` |
| M01-F09 | Edit profile (name, location, WhatsApp, photo) | ✅ | `updateProfile` → `save_own_profile` |
| M01-F10 | Profile photo upload | ✅ | `avatars` bucket |
| M01-F11 | Profile auto-repair when the `profiles` row is missing | ✅ | recovers a minimal farmer profile |
| M01-F12 | **Real OTP verification** | ⚪ | Task SEC-1, P0 |
| M01-F13 | Mock mode auth (any 4-digit code works) | 🧪 | `authService.ts`, in-memory registry |
| M01-F14 | Account deletion / data export | ⚪ | Required by store policies |

## 3. User flows

### 3.1 New user
1. App opens → branded splash (≥ 1.2 s; in live mode until saved session is checked).
2. No session → `ProfileOnboardingScreen` (mode **signup**).
3. Enter name, choose **Farmer** or **Land Owner**, enter mobile, toggle "this number is on WhatsApp".
4. Tap the Terms/Privacy text (opens `LegalDocumentScreen`) → checkbox becomes enabled → tick it.
5. Continue → GPS permission → location, district, state auto-filled.
6. `AuthContext.onboard()` creates the account and profile → navigator switches to the role dashboard automatically (no manual navigation).

### 3.2 Returning user
1. Open app → `ProfileOnboardingScreen` toggled to **login** → enter phone → `loginWithPhone()` → dashboard.
2. If no profile: alert "Account not found" with **Create account**.

### 3.3 Session restore
`onAuthStateChange` → `INITIAL_SESSION` → load profile (4 s guard) → `authReady = true`. If the profile load is slow, a minimal session-derived user is shown and silently upgraded.

## 4. Screens

| Screen | Route / where | Purpose |
|--------|---------------|---------|
| `SplashScreen` | shown by `AppNavigator` | Brand + wait for session |
| `ProfileOnboardingScreen` | RootStack `Onboarding` | Sign-up and login (the only auth UI in use) |
| `LegalDocumentScreen` | `SettingsStack` | Terms / Privacy text (`constants/legalContent.ts`) |
| `EditProfileScreen` | `SettingsStack` | Edit profile |
| *Legacy, not mounted:* `WelcomeScreen`, `OnboardingScreen`, `RoleSelectionScreen`, `LoginScreen`, `RegisterScreen`, `OtpScreen`, `ProfileSetupScreen`, `LanguageSelectionScreen` | `AuthStack` | Earlier OTP-style flow. **Reuse these for SEC-1** rather than rebuilding |

## 5. Data model
`profiles` — see [02 §3](../02-database-backend.md). App type `User` (`src/types/auth.ts`): `id, name, phoneNumber, role, email?, location?, district?, state?, hasWhatsapp?, acceptedTermsAndPoliciesAt?, avatarUrl?`.
Roles: `farmer | owner` (enum `user_role`).

## 6. Services & state

| Piece | Responsibility |
|-------|----------------|
| `AuthContext` | `user`, `isAuthenticated`, `isLoading`, `authReady`, `realAuth`; `onboard`, `loginWithPhone`, `signInWithPhone`, `signUpWithPhone`, `updateProfile`, `logout`, mock `login/completeProfile` |
| `loadUserFromSession` | Always a fresh profile read. **Do not add caching** — it was removed twice because it caused new sign-ups to land with the wrong role (race between the auth listener and onboarding read-back; see the long comment in the file) |
| `saveOwnProfile` | Calls RPC `save_own_profile`, falls back to `profiles.upsert` |
| `services/authService.ts` | Mock registry used only when Supabase is not configured |

**Identity scheme today:** the phone number becomes a synthetic email `<10-digit>@greenplot.app`, and the password is derived from the phone (`GreenPlot-<phone>-v1`). Supabase "Confirm email" must be OFF.

## 7. Business rules
1. One phone number = one account = one role. Role cannot be switched in the app.
2. Phone is normalised to 10 digits (`+91`/`91` prefix stripped).
3. Terms must be accepted at sign-up; the timestamp is stored once.
4. Logout always completes locally even if the network call hangs (4 s).
5. A user with no profile row is treated as `farmer` and a minimal row is created (repair path).
6. Role decides the whole app shell (`FarmerTabNavigator` vs `OwnerTabNavigator`).

## 8. Dependencies
Supabase Auth + `profiles`; GPS + geocoding (`utils/geo`) for location; `avatars` storage; i18n for the language picker.

## 9. Known issues & tech debt
| ID | Issue | Severity |
|----|-------|:--------:|
| KI-1 | Login with phone only, deterministic password → anyone can log in as anyone | **Critical** |
| KI-17 | Legacy `AuthStack` and mock `authService` are dead weight | Low |
| — | Temporary `[LOGIN]` debug logging in `ProfileOnboardingScreen.onContinue` should be removed | Low |
| — | Location is required via GPS at sign-up; denial blocks onboarding (no manual entry fallback) | Medium |
| — | "Confirm email" must be OFF in Supabase or sign-up fails with a setup message | Medium |

## 10. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Choose OTP channel (Supabase phone auth + Twilio/MSG91, or email OTP for v1) and get provider account | M01-T1 | P0 | S | Decision recorded; test numbers working |
| 1 | Add OTP step: request code → verify code → session. Reuse `OtpScreen` UI | M01-T2 | P0 | L | Cannot sign in without a valid code; wrong code shows error; resend with cooldown; rate-limited |
| 1 | Remove derived password; use the OTP session as the identity | M01-T3 | P0 | M | No password computed in app code; `phoneToPassword` deleted |
| 1 | Migrate existing users (they currently have the derived password) — first OTP login re-links by phone | M01-T4 | P0 | M | Existing profiles keep data and role after migration |
| 1 | Remove `[LOGIN]` debug logs; delete or archive unused `AuthStack` screens and mock `authService` | M01-T5 | P1 | S | No dead auth code left |
| 2 | Manual location entry fallback when GPS denied | M01-T6 | P1 | S | User can finish onboarding by choosing state/district |
| 2 | Account deletion (profile, media, leases anonymised) | M01-T7 | P0 for stores | L | In-app "Delete my account"; DB function removes/anonymises data; documented retention |
| 3 | Optional: add Laborer role end to end | M01-T8 | P2 | L | See [M08](M08-labor-work.md) |

## 11. Test checklist
- [ ] Sign up as Farmer; kill app; reopen → still logged in as Farmer
- [ ] Sign up as Owner with the same number → blocked with "already registered as a farmer"
- [ ] Invalid numbers rejected (`0123…`, `9999999999`, 9 digits)
- [ ] Terms checkbox disabled until legal text opened
- [ ] Deny GPS → clear message, can retry
- [ ] Airplane mode at logout → still returns to onboarding within ~4 s
- [ ] Edit profile name/photo; restart; changes persist
- [ ] (After SEC-1) wrong OTP, expired OTP, resend limit, OTP for unregistered number

## 12. Definition of Done
Standard DoD ([05 §5](../05-documentation-standards.md)) plus: security review of the auth flow, penetration check that a known phone number cannot be used to obtain a session, and Play/App Store account-deletion requirement met.
