# STATUS — FEATURE PROFILE

**Owner:** Profile Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_PROFILE.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/profile/`
**Routes owned:** `/profile`
**MF-remote target (Phase 2):** profile-mfe per FE-D13
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-06 (initial skeleton — profile sub-session not yet bootstrapped)

**Status:** ACTIVE — Dispatch 1 complete; awaiting ComplianceStepComponent from onboarding + cross-cutting.

## Current Phase

DISPATCH 1 COMPLETE — awaiting sibling sessions for Dispatch 2

## Done

- Mandatory reads (all 10) complete — 2026-06-06
- `profile-api.service.ts` — CREATED; correct 3-PATCH contract per BACKEND §8.B
- `profile-api.service.spec.ts` — 4/4 tests passing
- `profile.component.ts` — stub REPLACED with full skeleton (form, load, save, 404 handling)
- `profile.component.spec.ts` — 4/4 tests passing
- `account.routes.ts` — `providers: [ProfileApiService]` added to /profile route (coordinator hand-off resolved)

## In Progress

_(none — waiting on sibling sessions)_

## Blockers

- **B3 (gating Dispatch 2):** ComplianceStepComponent not yet implemented — onboarding session awaiting D1/D2/D3 founder decisions
- **B4 (non-blocking):** Un-merger (features/account/ → features/profile/) not yet applied to code — cross-cutting session's scope
- **B2 (non-blocking):** `core/models/seller-profile.model.ts` shape drift → cross-cutting session fix; workaround: inline `SellerProfileCorrect` in profile-api.service.ts
- **B1 (resolved by workaround):** Endpoint was PUT in docs → confirmed 3 PATCH; profile-api.service.ts implements correctly

## Next

1. Dispatch 2 — wire `<mee-compliance-step [mode]="'edit'">` once onboarding session hands off ComplianceStepComponent to `@shared/components/compliance-step/`
2. Coordinator wires `providers: [ProfileApiService]` in `account.routes.ts`
3. Cross-cutting fixes `core/models/seller-profile.model.ts` shape → remove inline `SellerProfileCorrect`

## Hand-offs

- **To coordinator (DONE):** `account.routes.ts` profile route — `providers: [ProfileApiService]` added 2026-06-06
- **To cross-cutting (pending):** `core/models/seller-profile.model.ts` shape fix per BACKEND §8.E
- **Waiting from onboarding + cross-cutting:** ComplianceStepComponent in `@shared/components/compliance-step/`

## Updates Log

=== UPDATE: 2026-06-06 SKELETON ===
STATUS file created. Profile sub-session awaits founder bootstrap.
ComplianceStepComponent shared with onboarding via shared/ per amendment
2026-06-06A.
=========

=== UPDATE: 2026-06-06 BOOTSTRAP ===
Profile sub-session opened. All 10 mandatory reads complete.

MANDATORY READS COMPLETE:
  1. docs/status/STATUS_FEATURE_PROFILE.md (prior: bootstrap pending)
  2. docs/SESSION_PROMPTS_FEATURE_BASE.md (universal governance)
  3. docs/FRONTEND_ARCHITECTURE.md §0 (FE-D1 through FE-D13), §2.B row 4
     (profile feature), §3.C.4 (features tree post un-merger), §3.D (7-file
     pattern), §3.G (shared/ vs feature rule), §4 (core/ — consume only),
     §5A (PARTIAL LOCK — design tokens pending), §17 (6 comm rules), §19
     (test + perf budget), §23 (route inventory — /profile owned here)
  4. docs/MVP_ARCHITECTURE.md §2.2 (seller_profile DDL — 9 LM fields +
     COO + compliance_extensions JSONB + active_super_categories)
     §3.2 (5 seller-profile endpoints per BACKEND §8)
  5. docs/MEESHO_CATEGORY_INTELLIGENCE.md §3 (Onboarding bucket — 10 base
     compliance fields + 6 conditional compliance extensions keyed by
     super-category slug)
  6. docs/BACKEND_ARCHITECTURE.md §8 (customer module LOCKED 2026-06-05 —
     5 endpoints, SellerProfileResponse + PatchProfileRequest schemas,
     COMPLIANCE_EXTENSION_MAP with 6 entries, exception hierarchy)
  7. docs/CORE_PHILOSOPHY.md M9 (LocaleMap structural i18n — no hardcoded
     EN strings) + F5 (every rendered field has display_label + display_help)
  8. docs/status/STATUS_FRONTEND.md (service-builder dispatch 2026-06-05
     landed core/ + shared/ + features stubs; FE-D12A un-merger applied to
     docs; 77 tests passing; initial bundle 111.76 KB)
  9. docs/status/STATUS_DESIGN_SYSTEM.md (Phase 1 Round 1 curation complete;
     38 strong refs; values PENDING founder picks — tokens are PARTIAL LOCK)
  10. docs/status/STATUS_FEATURE_ONBOARDING.md (bootstrapped 2026-06-06;
      D1/D2/D3 awaiting founder decisions; ComplianceStepComponent is an
      empty stub at features/account/components/compliance-step/ —
      NOT YET IMPLEMENTED; Q1/Q2/Q3 surfaced to master)

STATE ASSESSMENT — pre-dispatch codebase:
  - features/account/profile/profile.component.ts:
      Empty stub (class ProfileEditComponent, selector mee-profile-edit).
      Ready to be replaced with full implementation.
  - features/account/components/compliance-step/compliance-step.component.ts:
      Empty stub (class ComplianceStepComponent, selector mee-compliance-step).
      NOT IMPLEMENTED — onboarding session hasn't dispatched yet.
  - features/account/account-api.service.ts:
      Has getProfile() + updateProfile(PUT) — WRONG endpoint verb. BACKEND §8.B
      has NO PUT. Profile update requires 3 separate PATCH endpoints. Will create
      a dedicated profile-api.service.ts with the correct PATCH contract.
  - core/models/seller-profile.model.ts:
      SHAPE MISMATCH vs BACKEND §8.E (existing model uses legalName/gstNumber/
      businessAddress/superCategoryIds instead of locked manufacturer_name/
      packer_name/etc. with active_super_categories: string[]). Cross-cutting
      owned — cannot modify from this session. Will define correct inline types
      in profile-api.service.ts and surface as Q for master + cross-cutting.
  - No features/profile/ folder exists yet — code lives at features/account/
      profile/ (pre-amendment 2026-06-06A structure). Un-merger not applied.

FOUR BLOCKERS:
  B1. Endpoint contract mismatch — bootstrap prompt says GET + PUT. BACKEND §8.B
      has NO PUT endpoint. 3 PATCH endpoints for profile updates:
        PATCH /api/v1/seller-profile (9 LM fields + country_of_origin)
        PATCH /api/v1/seller-profile/active-categories (replaces super_id array)
        PATCH /api/v1/seller-profile/compliance/{super_id} (per-super_id JSONB merge)
      Same as onboarding Q1. Proceeding with 3-PATCH pattern per BACKEND §8.B.
      Surfacing to master for confirmation.
  B2. core/models/seller-profile.model.ts shape drift — same as onboarding Q3.
      Cross-cutting owned. Defining CORRECT inline types in profile-api.service.ts
      (mirroring BACKEND §8.E) until cross-cutting fixes the core model.
  B3. ComplianceStepComponent not yet implemented by onboarding session. Proceeding
      with a stub <div> placeholder per bootstrap recommendation (b). Will replace
      with real @shared/components/compliance-step import when available.
  B4. Un-merger (features/account/ → features/profile/) not yet applied to code.
      Building at EXISTING features/account/profile/ location per onboarding D1
      precedent. Cross-cutting will restructure at un-merger time.

STRUCTURAL DECISION:
  Per recommendation (b) in bootstrap prompt + onboarding D1 precedent:
  Building at features/account/profile/ (pre-un-merger location).
  Adding dedicated profile-api.service.ts (NOT shared account-api.service.ts)
  with correct 3-PATCH contract per BACKEND §8.B. Unblocks parallel progress.

Current phase: DISPATCH 1 — ProfileApiService + ProfileEditComponent skeleton
Action: dispatching meesell-angular-component-builder
=========

=== UPDATE: 2026-06-06 DISPATCH 1 COMPLETE ===
Phase: /profile — ProfileApiService + ProfileEditComponent skeleton

Done:
  - features/account/profile/profile-api.service.ts  CREATED
      getProfile() → GET /api/v1/seller-profile
      patchBaseProfile() → PATCH /api/v1/seller-profile
      patchActiveCategories() → PATCH /api/v1/seller-profile/active-categories
      patchComplianceExtension(superId, payload) → PATCH /api/v1/seller-profile/compliance/{superId}
      SellerProfileCorrect interface inline (correct §8.E shape; TODO for cross-cutting to fix core model)
  - features/account/profile/profile-api.service.spec.ts  CREATED — 4/4 tests passing
  - features/account/profile/profile.component.ts  REPLACED (was empty stub)
      Standalone, OnPush, signals (loading/saving/profile), reactive form (9 LM fields + COO)
      404 gracefully treated as "first-time seller" → empty form (PATCH is upsert)
      ComplianceStep = stub <div> with TODO comment for dispatch-2 wire-in
      Save → patchBaseProfile → navigateByUrl('/dashboard')
  - features/account/profile/profile.component.spec.ts  CREATED — 4/4 tests passing

Tests: 8/8 passing (ran per-file with --no-coverage; machine disk constraint)
Build: ng build zero errors; profile-component chunk 2.45 kB gzip;
       total initial bundle 130.39 kB gzip (§19 ≤180 kB met)
Chunk target: ≤80 kB gzip per route — WELL UNDER (2.45 kB; most logic deferred to dispatch-2)

Pending hand-offs (coordinator scope):
  - account.routes.ts needs providers: [ProfileApiService] on the profile route entry
  - core/models/seller-profile.model.ts shape drift → cross-cutting session fix needed

In progress: none — awaiting ComplianceStepComponent from onboarding + cross-cutting
Blockers: B3 (ComplianceStep), B4 (un-merger); B1+B2 documented with workarounds
Next: Dispatch 2 — wire ComplianceStepComponent + patchActiveCategories + patchComplianceExtension
     into ProfileEditComponent once @shared/components/compliance-step lands
=========

=== UPDATE: 2026-06-06 DESIGN SYSTEM INTEGRATION ACKNOWLEDGED ===
Trigger: Master-relayed notification — §5A AMENDMENT 2026-06-06B (design system
sub-session deliverables integrated by meesell-frontend-coordinator)

READS COMPLETED:
  ✓ FRONTEND_ARCHITECTURE.md §5A — AMENDMENT 2026-06-06B; STATUS confirmed FULL LOCK
  ✓ frontend/src/app/design-system/_tokens.scss
      Primary: #F26B23 · Secondary: #1E40AF · bg: #f0f5f9 · surface: #ffffff
      on-surface: #2a3547 · outline: #e5eaef (Spike) · radius: 7/16/18/full
      8-point spacing grid · reduced-motion respected
  ✓ _theme.scss — Material M3 + Spike light-theme wired
  ✓ _typography.scss — Plus Jakarta Sans 300-800 Google Fonts; global html/body rule
  ✓ _elevation.scss, _motion.scss, _component-overrides.scss (15 Material components
      pre-styled — button pill shape, textfield 37px, dialog, snackbar, etc.)
  ✓ breakpoints.ts, tokens.ts (TS mirrors)
  ✓ tailwind.config.js — all semantic colors + radius + elevation + motion wired
  ✓ styles.scss — import order verified

IMPACT ON DISPATCH 1 WORK (profile.component.ts):
  NO RE-DISPATCH NEEDED — per §5A implication #5.
  Existing component is already token-compliant:
    - Tailwind classes consume locked tokens via tailwind.config.js extensions ✓
    - mat-raised-button color="primary" → auto-inherits #F26B23 + pill shape ✓
    - mat-form-field + matInput → auto-inherits Spike textfield overrides ✓
    - Plus Jakarta Sans applied globally (html/body rule) — no component change ✓
    - No hardcoded hex values anywhere ✓
  Minor non-blocker: compliance-step stub uses text-gray-400 (Tailwind default gray)
    instead of text-on-surface-variant. Stub will be fully replaced in Dispatch 2.

DISPATCH 2 PLAN (token-aware):
  - Import ComplianceStep via @shared/components/compliance-step alias
  - Replace stub div with <mee-compliance-step [mode]="'edit'" ...>
  - Wire patchActiveCategories() + patchComplianceExtension() to saved event
  - Add bg-bg min-h-screen to page wrapper (per Q-PROFILE-002)
  - Iconography: Material Symbols Outlined for any icons (interim ratification)
  - No hardcoded colors — all via CSS custom properties or Tailwind semantic classes

TOKEN DISCREPANCY NOTE (see Q-PROFILE-001 in questions section):
  _tokens.scss --mee-color-outline: #e5eaef vs §5A.B doc table #D1D5DB.
  Using var(--mee-color-outline) in code (not the literal). Adapts automatically.

Status: ACTIVE — design system acknowledged; no re-dispatch; waiting on sibling
sessions (onboarding + cross-cutting) for Dispatch 2
=========

=== UPDATE: 2026-06-06 COORDINATOR FIX APPLIED ===
Action: Profile sub-session applied coordinator hand-off item directly.

CHANGE:
  features/account/account.routes.ts — profile route entry updated:
    Added `import { ProfileApiService } from './profile/profile-api.service';`
    Added `providers: [ProfileApiService]` to the /profile route object.
  Without this, Angular's lazy-load boundary means ProfileApiService (Injectable()
  with no providedIn) would not resolve when the route chunk loads.

BUILD VERIFICATION:
  ng build --configuration development — zero errors
  profile-component chunk: 20.76 kB (§19 ≤80 kB met)

Status after this update:
  - Coordinator hand-off B (account.routes.ts providers) — RESOLVED ✓
  - All other blockers unchanged: B3 (ComplianceStep), B4 (un-merger), B2 (core model)

Next: Dispatch 2 — awaiting ComplianceStepComponent from onboarding + cross-cutting
=========

## Questions for master

**Q-PROFILE-001 — outline token value discrepancy:**
`_tokens.scss` line 36 sets `--mee-color-outline: #e5eaef` (Spike value).
`FRONTEND_ARCHITECTURE.md §5A.B` table says `--mee-color-outline: #D1D5DB`.
These do not match. The SCSS file is the source of truth per §5A; I will use
`var(--mee-color-outline)` (not the literal) so whichever wins, my code adapts.
But the §5A doc table should be updated for accuracy. Please confirm which value
is canonical and update the doc table if needed.

**Q-PROFILE-002 — page background class:**
The profile page uses `max-w-2xl mx-auto p-4` with no explicit page bg. The
body/html gets `--mee-color-bg: #f0f5f9` globally. Should the profile page
wrapper explicitly add `bg-bg min-h-screen` to ensure consistent page
background in any context (e.g. if the page is embedded later), or is the
global body background sufficient for V1? Will address in Dispatch 2 unless
master directs otherwise.

## Questions for sibling sessions

**To onboarding session:**
Dispatch 2 is blocked on ComplianceStepComponent. Please notify this session
(via STATUS_FEATURE_ONBOARDING.md "Questions for sibling sessions" section)
when ComplianceStepComponent is implemented AND when cross-cutting has
confirmed the `@shared/components/compliance-step/` relocation path.
The agreed interface for profile edit mode:
  `<mee-compliance-step [mode]="'edit'" [profile]="profile()" (saved)="onComplianceSaved($event)">`
Please confirm this `mode` input + `saved` output shape when you spec the component.

**To cross-cutting session:**
Two items needed before profile Dispatch 2:
  1. Fix `core/models/seller-profile.model.ts` to match BACKEND §8.E
     (manufacturer_name/packer_name/etc. not legalName/gstNumber/etc.)
  2. Accept the ComplianceStepComponent relocation hand-off from onboarding to
     `shared/components/compliance-step/` — profile session imports via
     `@shared/components/compliance-step`
