# M08 — Labor Connect & Work Jobs

| | |
|---|---|
| **Status** | 🧪 Mock + 🚧 Hidden — a complete UI prototype running on bundled mock data. Entry points are disabled/commented out. DB tables exist but are unused |
| **Roles (intended)** | Farmer (post jobs, hire, mark attendance, pay), Laborer (find work, apply — **no sign-up path today**), Owner (read-only reports) |
| **Code** | `src/modules/labor/**` (screens, Redux slices, mock data, `laborApi`), `src/modules/work/**` (screens, `workSlice`, `workJobApi`, mock data), `src/modules/attendance/utils/attendanceCalculator.ts`, `src/middleware/permissions/*`, `src/screens/owner/{OwnerWorkReport,BudgetApprovals}Screen.tsx`, `src/modules/payments/*` |
| **DB** | `labor_jobs`, `job_applications` in `schema.sql` (not used by the app). No attendance, assignment or wage tables |
| **Related** | [M07 Crops](M07-crop-management.md), [M13 Payments](M13-payments.md), [M12 Maps](M12-agronomy-services.md) |

## 1. Purpose & scope
Connect farmers who need hands (harvesting, weeding, spraying…) with nearby daily-wage labor, track who showed up, and pay wages — all tied to a specific **crop cycle** (CropCycle → WorkJob → Labor).

**Today:** a clickable prototype. **Target:** a real two-sided marketplace. **Decision needed (M08-T0):** is Labor in launch scope? It requires a new user type (laborer), SMS-friendly flows and a payments model. The roadmap treats it as Phase 2, P1.

## 2. What is built (all mock data)

| ID | Feature | Status | Where |
|----|---------|:------:|-------|
| M08-F01 | Labor dashboard: counts of jobs / applications | 🧪 | `LaborDashboardScreen` (hard-coded farmer `'F001'`) |
| M08-F02 | **Post Job**: work type (9), crop, acres/hours, workers needed, wage/day, date, location, notes | 🧪 | `PostJobScreen`, `jobSlice` |
| M08-F03 | Browse jobs with filters (work type, min wage, distance) and sort | 🧪 | `JobListScreen` |
| M08-F04 | My Jobs | 🧪 | `MyJobsScreen` |
| M08-F05 | Applications: accept / reject applicants | 🧪 | `ApplicationsScreen`, `applicationSlice` |
| M08-F06 | Find laborers on a **map**; laborer profile (skills, expected wage, rating, experience) | 🧪 | `FindLaborMapScreen`, `LaborDetailsScreen` ("Booking Initiated" alert only) |
| M08-F07 | Attendance marking per laborer per day; wage calculator (per labor, per job, cost per acre) | 🧪 | `AttendanceScreen`, `attendanceCalculator.ts` (the one pure, reusable piece) |
| M08-F08 | Payment summary with Razorpay test checkout (lump sum for pending wages) | 🧪 | `PaymentSummaryScreen` — hard-coded laborers (Ramu, Sita, Gopal); pays the platform account, not laborers |
| M08-F09 | **Work module**: Create Work against a crop cycle (type, description, workers, wage, date, start/end time), Work List, Work Details | 🧪 | `modules/work/screens/*`. The crop-cycle picker is real, but `workJobApi.createJob` writes to an **in-memory array** — the "Job created successfully!" alert appears and nothing is saved (lost on restart; invisible to other users). Only farmers allowed (`requirePermission('create_jobs')`) |
| M08-F10 | Owner **Work Report** per land (jobs + crops) | 🚧 | `OwnerWorkReportScreen` uses `MOCK_WORK_JOBS`; Owner Home shows "coming soon" |
| M08-F11 | Owner **Budget & Approvals** | 🚧 | `BudgetApprovalsScreen`; no table; Owner Home item commented out |
| M08-F12 | Role/permission map (Owner / Farmer / Labor) | 🟡 | `middleware/permissions` — only used by Create Work |
| M08-F13 | Real backend, laborer sign-up, notifications, ratings, disputes | ⚪ | |

**Where the entry points are switched off**
* Owner Home: "Labor" and "Work report" tiles → `Alert('… coming soon!')`.
* Farmer Home: "Hire Labor" / "Create Work" quick actions commented out; `labor` action still routes to `LaborConnect` (reachable only via old shortcuts and the hidden "Today's tasks").
* Create Work is still registered in several stacks and reachable from crop screens.

## 3. Screens and navigation
`LaborConnectStack` (nested inside Farmer/Owner Home stacks as route `LaborConnect`): `LaborDashboard`, `PostJob`, `JobList`, `Applications`, `MyJobs`, `Attendance`, `FindLaborMap`, `LaborDetails`, `PaymentSummary`.
Work screens (in `MyCropsStack`): `CreateWork`, `WorkList`, `WorkDetails`.

## 4. Data model — current vs target

**Current (TypeScript, in-memory):** `Job` (labor module) and `WorkJob` (work module) are **two overlapping job models** — `Job` has farm name / acres / hours / location; `WorkJob` links to `cropCycleId` + `landId` with start/end time. `Labor`, `Application`/`JobApplication`, `AttendanceRecord`/`LaborAssignment`.

**Existing SQL:** `labor_jobs(id, farmer_id, work_type, description, workers_needed, wage_per_day, work_date, status, location)` and `job_applications(id, job_id, labor_id, status)`.

**Proposed target schema (to be reviewed — not implemented):**

| Table | Key columns |
|-------|-------------|
| `labor_profiles` | `user_id`, `skills[]`, `expected_wage`, `experience_years`, `location` (point), `radius_km`, `rating`, `is_available` |
| `work_jobs` | merge of `Job` + `WorkJob`: `farmer_id`, `crop_cycle_id`, `land_id`, `work_type`, `description`, `workers_needed`, `workers_hired`, `wage_per_day`, `work_date`, `start_time`, `end_time`, `location`, `status` |
| `job_applications` | `job_id`, `labor_id`, `status`, `message` (+ unique `(job_id, labor_id)`) |
| `job_assignments` | `job_id`, `labor_id`, `assigned_at`, `payment_status` |
| `attendance_records` | `job_id`, `labor_id`, `date`, `status`, `hours`, `wage_amount`, `marked_by` |
| `wage_payments` | links to `payments` ([M13](M13-payments.md)): `job_id`, `labor_id`, `amount`, `status` |
| `labor_ratings` | `job_id`, `rater_id`, `ratee_id`, `stars`, `comment` |

## 5. Business rules (target)
1. Only a **farmer** can create jobs; a **laborer** can apply; an **owner** has read-only reports. (`ROLE_PERMISSIONS` in `middleware/permissions`.)
2. A job belongs to one crop cycle that is `current` and whose lease (if any) is `active`.
3. `workers_hired ≤ workers_needed`; accepting an application that fills the job closes it to new applications.
4. Daily wage = `wage_per_day × presentDays`; cost per acre = total wage ÷ acres worked (`attendanceCalculator`).
5. Payment must reach the **laborer** (Razorpay Route / UPI payout) — today's flow pays the platform account and is a test-only demo.
6. Attendance can be marked only by the hiring farmer, once per laborer per day.

## 6. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| KI-7 | Farmer id `'F001'` hard-coded in several screens; slices call mock APIs with `setTimeout` | Replace with `useAuth().user.id` + Supabase |
| KI-8 | Dead-end entry points / "coming soon" alerts | LAB-1 |
| M08-D1 | Two job models, two Redux flows (`job` vs `work` slices) in a store named `laborStore` for the whole app | Merge into one `WorkJob` model; move to the contexts + `*Api.ts` pattern used elsewhere |
| M08-D2 | No laborer role / onboarding; `UserRole` mismatch (`'Owner'/'Farmer'/'Labor'` vs `'owner'/'farmer'`) | Add role to enum, normalise the permission map |
| M08-D3 | Payments demo pays a lump sum; fixture data in `PaymentSummaryScreen` | Real wage data + payout design |
| M08-D4 | Owner Work Report and Budget screens read mock data only | OWN-1 |
| M08-D5 | Map screen needs Mapbox token; laborer locations are fake | Real location capture with consent |
| M08-D6 | Safety/compliance: minimum wage display, child labor policy, grievance process | Policy decision before launch |

## 7. Implementation plan (if Labor is approved for Phase 2)

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 0 | Product decision (scope, laborer onboarding: app vs farmer-entered contacts, payment model) | M08-T0 | P1 | S | Written spec in this doc |
| 1 | Add `laborer` role (enum, onboarding variant with skills + availability, role guard) | M08-T1 | P1 | L | Laborer can sign up and sees only the labor tab |
| 1 | Create merged schema + RLS (farmer owns job; laborer owns application; both read assignment) + realtime | M08-T2 | P1 | L | Migration in repo; negative RLS tests |
| 1 | `workApi.ts`, `LaborContext` (replace Redux slices); keep `attendanceCalculator` | M08-T3 | P1 | L | Screens read real data; mock mode retained |
| 2 | Post job → nearby laborers (distance filter via lat/long), apply, accept/reject, notifications | M08-T4 | P1 | L | Two-device test passes |
| 2 | Attendance marking and wage totals persisted | M08-T5 | P1 | M | Totals match calculator unit tests |
| 2 | Wage payment: laborer payout design + Razorpay Route/UPI; receipts | M08-T6 | P1 | XL | Money reaches laborer; ledger reconciles |
| 2 | Re-enable entry points (Farmer Home, Owner Home) and Owner Work Report on real data | M08-T7 | P1 | M | No "coming soon" alerts remain |
| 3 | Ratings, repeat-hire list, WhatsApp share of job | M08-T8 | P2 | M | |
| 3 | Owner Budget & Approvals: farmer requests input budget, owner approves | M08-T9 | P2 | L | New `budget_requests` table + approval states |

## 8. Test checklist (once real)
- [ ] Farmer posts a job; laborer within radius sees it; far laborer does not
- [ ] Two laborers apply; farmer accepts one; counts update live on both phones
- [ ] Job full → apply button disabled
- [ ] Attendance 3 of 5 days → wage = 3 × rate; cost per acre correct
- [ ] Owner cannot post jobs; laborer cannot mark attendance
- [ ] Payment failure leaves wage `pending`, success marks `paid` server-side only

## 9. Definition of Done
Standard DoD plus: product/legal sign-off on labor policy, payout compliance reviewed, and mock data fully removed from user-visible screens.
