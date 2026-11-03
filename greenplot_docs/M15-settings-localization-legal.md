# M15 — Settings, Localization & Legal

| | |
|---|---|
| **Status** | 🟡 Partial — Settings, Edit Profile, language switching and the legal text work. **Translation coverage is low** (most screens are English-only) and three Settings rows do nothing |
| **Roles** | Farmer, Owner |
| **Code** | Settings: `src/navigation/SettingsStack.tsx`, `src/screens/settings/**`. Language: `src/localization/{i18n.ts,languageDetector.ts,useTranslationHook.ts,marketTranslations.ts,resources/*.json}`, `src/screens/LanguageSelectionScreen.tsx`, `src/screens/farmerHome/components/LanguagePickerModal.tsx`, `src/components/LanguageDropdown.tsx`. Legal: `src/constants/legalContent.ts`, `src/screens/settings/LegalDocumentScreen.tsx`. OTA: `hot-updater.config.ts`, `App.tsx` |
| **DB** | `profiles.accepted_terms_and_policies`; language is stored on-device only (AsyncStorage key `greenplot_language`) |
| **Related** | [M01 Auth](M01-auth-onboarding.md), [M11 AI](M11-kisan-mitra-ai.md) |

## 1. Settings

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M15-F01 | Settings screen (profile header, preferences list, language, logout) reachable from the avatar in every tab header | ✅ | nested `SettingsStack` inside every tab stack |
| M15-F02 | **Edit profile** (name, location/district/state, WhatsApp flag, photo) | ✅ | `AuthContext.updateProfile` |
| M15-F03 | **Privacy Policy** and **Terms & Conditions** viewer | ✅ | `LEGAL_CONTENT`, `LEGAL_VERSION = '1.0'` |
| M15-F04 | **Logout** with confirmation, spinner, guaranteed completion | ✅ | |
| M15-F05 | Language row → Language Selection | ✅ | |
| M15-F06 | "Notifications", "Help & Support", "Consent logs" rows | ⚪ | rendered but have no destination |
| M15-F07 | Generic web page viewer (`SettingsWebView`) | 🟡 | wired for URL items, none configured |
| M15-F08 | App version / build number, OTA status | ⚪ | |
| M15-F09 | Delete account, export my data | ⚪ | required for store compliance |
| M15-F10 | Contact support / report a problem (WhatsApp, phone, email) | ⚪ | |

## 2. Localization (i18n)

**How it works:** `i18next` with the `common` namespace. English is bundled; `hi, kn, mr, te, ta` JSON files load lazily via `loadLanguage(lng)`. The user's choice is saved to AsyncStorage and restored by `languageDetector` (default `en`). The Market module has its own `marketTranslations.ts` merged under `market.*`. `fallbackLng = en`; missing keys are logged (`[i18n missing]`).

**Available languages:** English, हिंदी, ಕನ್ನಡ, मराठी, తెలుగు, தமிழ். Header buttons show a short label (`EN, हि, ಕ, म, తె, த`).

**Reality check (measured on the current code):**

| Measure | Value |
|---------|-------|
| Screens/components that call `useTranslation` | **32 of 244** `.tsx` files |
| Strings in `en.json` / `kn.json` | **59** (namespaces: dashboard, labor, satellite, settings, common, soilTest) |
| Strings in `hi / mr / ta / te` | **40** (no `soilTest`) |
| Where translation is real | Market module (own bundle), Home headers, My Properties, My Crops, Hub content, My Active Leases, onboarding, language pickers |
| Where it is **not** | Lease, agreement, closure, management, crop dashboards, settings rows, alerts, validation messages — hard-coded English |

So choosing Kannada changes some titles but most of the app stays in English. Kisan Mitra has separate language handling ([M11](M11-kisan-mitra-ai.md), only en/hi/kn fully).

| ID | Feature | Status |
|----|---------|:------:|
| M15-F20 | Language picker (modal in headers, full screen in Settings/onboarding), persisted | ✅ |
| M15-F21 | Lazy-loaded bundles | ✅ |
| M15-F22 | Full string coverage for all screens | ⚪ |
| M15-F23 | Language stored on the profile (so push/AI/emails use it) | ⚪ |
| M15-F24 | Locale formatting (₹ lakh/crore, dates, acres/guntas wording) per language | ⚪ |
| M15-F25 | Translation workflow (export/import to translators, missing-key CI check) | ⚪ |

**Rules for new UI code**
1. No user-facing literal in new code: `t('feature.key')`; add the English string to `en.json` in the same PR.
2. Keys are grouped by feature (`market.*`, `settings.*`, …) — never reuse a key for a different meaning.
3. Interpolate values (`t('x', { count })`), never concatenate sentences.
4. Alerts and validation messages are UI text too.
5. Design for longer Indic text (no fixed widths on buttons/chips).

## 3. Legal & consent

* Single source of truth `legalContent.ts` (sections of the Privacy Policy and Terms) read by both onboarding and Settings. `LEGAL_VERSION = '1.0'`.
* At sign-up the checkbox is enabled only after the user opens the text; the timestamp is stored in `profiles.accepted_terms_and_policies`. **The version accepted is not stored.**
* Policy text states data collected (profile, farm, crop, lease, machinery, work info; device/usage) and third-party services.

| ID | Feature | Status |
|----|---------|:------:|
| M15-F30 | Combined T&C + Privacy acceptance with timestamp | ✅ |
| M15-F31 | Store accepted **version** and re-prompt when the version changes | ⚪ |
| M15-F32 | Consent log screen (the "Consent logs" row) | ⚪ |
| M15-F33 | Separate consent for location, camera/mic, notifications, AI image processing, marketing | ⚪ |
| M15-F34 | Policy hosted at a public URL (stores require one) and linked in the app | ⚪ |
| M15-F35 | Policy content reviewed by legal counsel (data retention, Aadhaar-like documents, children, grievance officer — India DPDP Act) | ⚪ |

## 4. OTA updates (Hot Updater)
Enabled only when `HOT_UPDATER_BASE_URL` is set; `updateStrategy: 'appVersion'`. Not user-visible. Operational rules are in [03 §6](../03-dev-setup-release.md).

## 5. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| KI-13 | Low translation coverage and mismatched AI/UI language lists | I18N-1 |
| M15-D1 | Dead Settings rows (Notifications, Help & Support, Consent logs) | Hide or build |
| M15-D2 | Language not stored server-side | Add `profiles.language` |
| M15-D3 | `saveMissing: true` logs every missing key in dev | Fine; add CI check |
| M15-D4 | `scripts`-style root file `update_json.js` hard-edits `en.json`/`kn.json` (one-off) | Remove from repo |
| M15-D5 | Terms content is generic; DPDP-specific rights (access, correction, erasure) not implemented | Legal review + M01-T7 |
| M15-D6 | `SettingsWebView` has no allow-list | Restrict to https + trusted hosts |

## 6. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | Hide or implement dead Settings rows; add Help & Support (WhatsApp/phone/email) and app version | M15-T1 | P0 | S | No inert row |
| 1 | Host Privacy Policy & Terms at public URLs; link from Settings and store listings | M15-T2 | P0 | S | URLs live; same text as in-app |
| 1 | Account deletion + data export entry in Settings (backend in M01-T7) | M15-T3 | P0 | M | Store requirement met |
| 1 | Store accepted `LEGAL_VERSION`; re-prompt on change; Consent logs screen | M15-T4 | P1 | M | Re-prompt works; history listed |
| 2 | **Localization sprint**: extract all literals to keys, feature by feature, order: Lease/Agreement → Farm Management → Crops → Closure → Settings → Alerts; translators for hi/kn first | M15-T5 | P1 | XL | ≥ 95 % of visible strings keyed in hi + kn (measured by lint script) |
| 2 | CI check: every key in `en.json` exists in all six files; no new literal in JSX (lint rule) | M15-T6 | P1 | M | PR fails on violation |
| 2 | Save language on profile; use it for push, AI default, server messages | M15-T7 | P1 | S | |
| 3 | Number/date/currency formatting per locale; unit preferences (acre / hectare / guntas) | M15-T8 | P2 | M | |
| 3 | Granular consents (location, camera, mic, AI image upload, marketing) | M15-T9 | P1 | M | Consent recorded with timestamp |

## 7. Test checklist
- [ ] Switch to Kannada: restart app → still Kannada
- [ ] Missing key falls back to English, no crash
- [ ] Long Tamil/Kannada strings don't clip buttons
- [ ] T&C checkbox locked until the text is opened; timestamp saved
- [ ] Logout twice quickly → one clean logout
- [ ] Edit profile: change name/photo → visible on Home and Hub

## 8. Definition of Done
Standard DoD plus: legal text approved, URLs public, and translation key coverage reported in the PR.
