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

- **To coordinator (pending):** `account.routes.ts` profile route needs `providers: [ProfileApiService]` added
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

## Questions for master

_(sub-session appends here)_

## Questions for sibling sessions

_(sub-session appends here — likely to onboarding + cross-cutting)_
