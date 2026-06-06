# STATUS — FEATURE ONBOARDING

**Owner:** Onboarding Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_ONBOARDING.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/onboarding/`
**Routes owned:** `/onboarding`
**MF-remote target (Phase 2):** onboarding-mfe per FE-D13
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-06 (initial skeleton — onboarding sub-session not yet bootstrapped)

**Status:** Session not yet started — initialize by opening a new Claude Code window and pasting bootstrap prompts (BASE + ONBOARDING).

## Current Phase

_pending_

## Done

_(none yet)_

## In Progress

_(none yet)_

## Blockers

- Onboarding sub-session not yet bootstrapped (founder action)

## Next

1. Founder opens new Claude window + pastes bootstrap prompts
2. Sub-session reads mandatory files per BASE + ONBOARDING prompts
3. Coordinate ComplianceStepComponent ownership with cross-cutting session via STATUS hand-off (recommend implement-then-relocate)
4. Recommended first dispatch: OnboardingWizardComponent skeleton (mat-stepper 3 phases) + SuperCategoryChipsComponent

## Hand-offs

_(none yet)_

## Updates Log

=== UPDATE: 2026-06-06 SKELETON ===
STATUS file created by master per FE-D12 amended grouping.
Onboarding sub-session awaits founder bootstrap. Note: per
amendment 2026-06-06A, ComplianceStepComponent moves to
shared/components/compliance-step/ (cross-cutting session's scope) —
profile session also reuses it. Coordinate via STATUS hand-off.
=========

=== UPDATE: 2026-06-06 SUB-SESSION BOOTSTRAPPED ===
Onboarding sub-session opened by founder per FE-D12 amended grouping +
SESSION_PROMPTS_FEATURE_ONBOARDING.md bootstrap prompt.

Mandatory reads complete (9 files + 2 supporting):
  1. docs/status/STATUS_FEATURE_ONBOARDING.md (prior state)
  2. docs/SESSION_PROMPTS_FEATURE_BASE.md (universal governance)
  3. docs/FRONTEND_ARCHITECTURE.md
       §0 (FE-D11 + FE-D12 amended + FE-D13 grasped)
       §2.B + §2.C.2 (onboarding row + responsibility)
       §3.C.4 (features tree post un-merger)
       §3.D (7-file pattern)
       §3.G (decision rules — shared/ qualifying rule)
       §4.C (AuthService API contract) + §4.E (ApiClient) + §4.I (core/models)
       §5A (PARTIAL LOCK — tokens consumed as CSS custom properties)
       §17 (6 communication rules — no cross-feature imports)
       §18 (11 primitives — NOT consumed by onboarding; that's catalog-form)
       §19 (Vitest + @analogjs/vite-plugin-angular; 80 KB chunk budget)
       §23 (1 route owned — /onboarding)
  4. docs/MVP_ARCHITECTURE.md §2.2 (seller_profile DDL) + §3.2 (5 seller-profile
     endpoints) + §4.3 (3-phase onboarding wizard) + §11.4 (DATA→FRONTEND
     hand-off; acceptance "10 base + 1-4 extension steps")
  5. docs/MEESHO_CATEGORY_INTELLIGENCE.md §3 (Onboarding bucket — 9 LM + COO
     + compliance_extensions JSONB) + §7 (compliance extensions table)
  6. docs/BACKEND_ARCHITECTURE.md §8 (customer module — 5 endpoints, schemas,
     COMPLIANCE_EXTENSION_MAP with 6 entries, exception hierarchy)
  7. docs/CORE_PHILOSOPHY.md M9 (LocaleMap structural i18n) + F5 (every field
     has display_help)
  8. docs/status/STATUS_FRONTEND.md (master context — service-builder dispatch
     2026-06-05 landed core/ + shared/ + features stubs BEFORE 2026-06-06A
     un-merger; FE-D13 MF-alignment ratified)
  9. docs/status/STATUS_DESIGN_SYSTEM.md (Phase 1 Round 1 curation complete;
     38 strong refs; values still PENDING founder picks — placeholder tokens
     in FRONTEND_ARCH §5A are non-authoritative)
  Supporting reads: .claude/agent-memory/meesell-angular-component-builder/
                    MEMORY.md (empty baseline);
                    docs/status/STATUS_FEATURE_CROSS_CUTTING.md (expecting
                    implement-then-relocate pattern for ComplianceStep);
                    docs/status/STATUS_FEATURE_PROFILE.md (not bootstrapped).

STATE ASSESSMENT — pre-bootstrap codebase:
  - features/ tree on disk reflects PRE-amendment 2026-06-06A merged
    structure: features/account/ exists (with onboarding/, profile/,
    signup/, login/, components/{compliance-step,super-category-chips,
    otp-verify}/, account.routes.ts, account-api.service.ts, account.model.ts).
    features/onboarding/, features/auth/, features/profile/ do NOT yet exist
    as separate folders.
  - app.routes.ts routes /onboarding into account/account.routes.ts (pre-
    amendment). The un-merger has not yet been applied to the codebase.
  - Existing onboarding stubs in features/account/:
      onboarding/onboarding.component.ts            — empty template stub
      components/compliance-step/compliance-step.component.ts  — empty stub
      components/super-category-chips/super-category-chips.component.ts
                                                    — empty stub with
                                                       selectionChange output
  - core/models/seller-profile.model.ts present BUT SHAPE MISMATCH vs locked
    BACKEND §8.E SellerProfileResponse — see BLOCKER #3 below.
  - core/auth/AuthService + 4 interceptors + ApiClient + 9 cross-feature
    models + InjectionTokens + 6 shared component stubs are LANDED per the
    cross-cutting STATUS (77 tests passing, initial bundle 111.76 KB).

THREE BLOCKERS SURFACED TO MASTER Q&A (this STATUS file's Q sections):
  B1. Backend contract typo — bootstrap prompt names PUT /seller-profile;
      backend §8.B has NO PUT, only 3 PATCH endpoints. Likely shorthand;
      need master confirmation.
  B2. Super-category chip count — bootstrap prompt says 7; backend
      COMPLIANCE_EXTENSION_MAP has 6 entries (Grocery/Kids/Electronics/
      Beauty/Books/Appliances); MEESHO §7 has Pet (75) as a 7th overlap
      reusing FSSAI. Need master confirmation on chip count for V1.
  B3. core/models/seller-profile.model.ts shape DRIFT from BACKEND §8.E:
      existing fields (legalName, gstNumber, businessAddress,
      superCategoryIds: UUID[]) do not match locked SellerProfileResponse
      (9 LM fields, country_of_origin, active_super_categories: string[]
      of Meesho super_ids, compliance_extensions: dict[str, dict],
      profile_complete bool). Owned by cross-cutting per §17 — cannot
      modify from this session. Need master + cross-cutting alignment
      before onboarding-api.service.ts ships.

THREE FOUNDER DECISIONS REQUESTED (presented in chat):
  D1. Code location — restructure to features/onboarding/ first (extracting
      from account/), OR build at existing features/account/onboarding/ and
      defer un-merger to cross-cutting session? (RECOMMEND: build at
      features/account/onboarding/ for now to unblock; cross-cutting does
      the un-merger restructure when it bootstraps — keeps app.routes.ts
      ownership clean.)
  D2. ComplianceStepComponent ownership — implement-then-relocate (fastest
      momentum) vs spec-first coordination with cross-cutting. (RECOMMEND:
      implement-then-relocate; cross-cutting STATUS already EXPECTS this
      pattern — "ComplianceStepComponent landing in shared/components/
      compliance-step/ (coordinate with onboarding session — likely
      implement-then-relocate pattern)".)
  D3. First dispatch scope — bootstrap recommendation is OnboardingWizard-
      Component skeleton (mat-stepper, 3 phases, no inner rendering) +
      SuperCategoryChipsComponent (MatChipListbox + 6/7 super-categories).
      Defer ComplianceStepComponent to 2nd dispatch after wizard frame works.

Current phase: Pre-dispatch — awaiting founder direction on D1/D2/D3
Current round: Bootstrap presentation (no dispatch yet)

Action this turn:
  - 9 mandatory files read; blockers + decisions surfaced to founder in chat
  - Awaiting founder response on D1/D2/D3
  - On master poll: Q1/Q2/Q3 in "Questions for master" section below
=========

## Questions for master

**Q1 (Bootstrap prompt contract — likely typo).**
My bootstrap prompt names `PUT /api/v1/seller-profile` as the submission
endpoint. BACKEND_ARCHITECTURE.md §8.B has NO PUT endpoint for
seller-profile — only:
  - `PATCH /api/v1/seller-profile` (base profile partial-update; 9 LM
    fields + country_of_origin)
  - `PATCH /api/v1/seller-profile/active-categories` (replaces super_id
    array)
  - `PATCH /api/v1/seller-profile/compliance/{super_id}` (per-super_id
    JSONB merge of compliance extension)
The 3-phase wizard maps naturally to these 3 PATCH endpoints in order.
Please confirm: treat bootstrap prompt's PUT as shorthand for "the 3
PATCH endpoints"; OR provide canonical endpoint that I missed.

**Q2 (Super-category chip count).**
Bootstrap prompt says "7 super-categories with compliance extensions".
Backend §8.F `COMPLIANCE_EXTENSION_MAP` constant has **6 entries**:
  - 26 Grocery (FSSAI compulsory)
  - 13 Kids (BIS optional)
  - 16 Electronics (BIS + R-Number + IS-Number + CM/L-Number optional)
  - 19/36/37/14/88/34 Beauty (License-trio compulsory within subset)
  - 80 Books (ISBN optional, follow-Meesho-lenient)
  - 30 Home & Kitchen appliance subset (License-pair optional)
MEESHO_CATEGORY_INTELLIGENCE.md §7 shows a 7th row (Pet super_id=75) which
"reuses FSSAI from Grocery" for the food-overlap case. Backend
COMPLIANCE_EXTENSION_MAP does NOT include Pet as a separate entry.
Please confirm V1 chip count: 6 (backend constant) or 7 (include Pet
chip; reuse FSSAI in compliance_extensions["26"]).

**Q3 (CRITICAL — core/models/seller-profile.model.ts contract drift —
cross-cutting session attention required).**
The model landed by service-builder dispatch 2026-06-05 declares fields
(`legalName: string`, `gstNumber: string | null`, `fssaiLicenseNumber:
string | null`, `businessAddress: string`, `superCategoryIds: UUID[]`)
that do NOT exist in BACKEND §8.E SellerProfileResponse. Locked backend
shape: 9 LM fields (`manufacturerName/Address/Pincode`,
`packerName/Address/Pincode`, `importerName/Address/Pincode`),
`countryOfOrigin: string`, `activeSuperCategories: string[]` (Meesho
super_ids like "26", NOT UUIDs), `complianceExtensions: Record<string,
Record<string, unknown>>`, `profileComplete: boolean`, timestamps.
`RequiredProfileFields` also drifts from §8.E `RequiredFieldsResponse`
(`baseFields: FieldSpec[]`, `extensionFields: Record<string,
FieldSpec[]>`, `completed: Record<string, boolean>`).
This is in core/models/ — cross-cutting session's scope per §17. I
cannot modify it. Cannot ship onboarding-api.service.ts accurately
without this. Request master coordinate with cross-cutting session
(or authorize me to surface a fix PR to cross-cutting once it bootstraps).

## Questions for sibling sessions

**To cross-cutting session (when bootstrapped):**
- Please ratify the `SellerProfile` + `RequiredProfileFields` model shape
  fix per Q3 above against BACKEND §8.E.
- Please plan to receive ComplianceStepComponent implementation hand-off
  per founder D2 ruling (implement-then-relocate recommended) — target
  location `shared/components/compliance-step/`.
- Please plan to handle un-merger restructure of features/account/ →
  features/auth/ + features/onboarding/ + features/profile/ + extraction
  of account-api.service.ts into auth-api / onboarding-api / profile-api
  service files + update of app.routes.ts loadChildren references. This
  cross-cuts 4 sessions and must be sequenced.

**To profile session (when bootstrapped):**
- ComplianceStepComponent will be implemented inside onboarding scope
  first (per founder D2 recommendation) and handed off to cross-cutting
  for relocation to shared/. Profile session consumes via
  `@shared/components/compliance-step` alias once relocated. No action
  required from profile session yet — coordinate at hand-off time.
