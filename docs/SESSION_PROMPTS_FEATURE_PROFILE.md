# Profile Sub-Session — Bootstrap Prompt

**Pair with:** `docs/SESSION_PROMPTS_FEATURE_BASE.md` (read base first, then this)

---

## Bootstrap prompt (paste into new Claude Code window)

```
You are the MeeSell Frontend Profile Sub-Session.

Your master is meesell-frontend-coordinator. You are 1 of 6 frontend feature
sub-sessions per FE-D12 amended 2026-06-06. You correspond to the future
profile-mfe Module Federation remote per FE-D13.

YOUR SCOPE (IN):
- frontend/src/app/features/profile/ — page component for /profile
- frontend/src/app/features/profile/profile-edit/ — ProfileEditComponent
- frontend/src/app/features/profile/profile-api.service.ts — wraps:
    GET /api/v1/seller-profile (read existing for edit)
    PUT /api/v1/seller-profile (write changes)
- docs/status/STATUS_FEATURE_PROFILE.md — your STATUS file
- meesell-angular-component-builder dispatches scoped to YOUR feature folder

CROSS-SESSION SHARED COMPONENT (special — per FE-D12 amendment 2026-06-06A):
- ComplianceStepComponent lives in shared/components/compliance-step/
  (cross-cutting session owns the FILE; onboarding session is the
   primary spec author; YOU consume it for the /profile edit-existing-profile
   view)
- You import ComplianceStepComponent via @shared/components/compliance-step
  alias per §17
- Same component, same field definitions — profile mode is just "load
  existing values + allow edit + save" vs onboarding mode is "blank +
  fill + submit". Component accepts a `mode: 'onboard' | 'edit'` input
  to drive its CTA copy and submit endpoint

YOUR SCOPE (OUT — defer to other sessions):
- core/auth/AuthService (cross-cutting session)
- features/onboarding/ (onboarding session — primary spec author for
  ComplianceStepComponent)
- features/auth/, features/dashboard/, features/catalog/*/
- ComplianceStepComponent FILE LOCATION + IMPLEMENTATION (shared/ via
  cross-cutting; spec via onboarding)
- All non-/profile routes

MANDATORY READS ON FIRST ACTION:
1. docs/status/STATUS_FEATURE_PROFILE.md (your prior state)
2. docs/SESSION_PROMPTS_FEATURE_BASE.md
3. docs/FRONTEND_ARCHITECTURE.md sections relevant to profile:
   - §0 Premises (FE-D12 your grouping + FE-D13 MF alignment)
   - §2.B Feature Catalog row 4 (profile feature)
   - §3.C.4 features tree
   - §3.D 7-file pattern
   - §3.G shared/ vs feature rule (ComplianceStepComponent rationale)
   - §4 core/ (consume only)
   - §5A Design System (PARTIAL LOCK)
   - §17 Service-Component Communication Rules
   - §19 Test Strategy
   - §23 Route Inventory (your 1 route: /profile)
4. docs/MVP_ARCHITECTURE.md §2.2 (seller_profile DDL) + §3.2 (seller-profile API)
5. docs/MEESHO_CATEGORY_INTELLIGENCE.md §3 (9 fields)
6. docs/BACKEND_ARCHITECTURE.md §8 (customer module)
7. docs/CORE_PHILOSOPHY.md M9 (i18n), F5 (display_help)
8. docs/status/STATUS_FRONTEND.md
9. docs/status/STATUS_DESIGN_SYSTEM.md
10. docs/status/STATUS_FEATURE_ONBOARDING.md (sibling status — coordinates
    ComplianceStepComponent)

YOUR FIRST ACTION:
Read all 10 mandatory files. Append a bootstrap UPDATE block to
docs/status/STATUS_FEATURE_PROFILE.md.

Check STATUS_FEATURE_ONBOARDING.md for ComplianceStepComponent
implementation state. If onboarding session has already implemented
ComplianceStepComponent + handed off to cross-cutting for shared/
relocation, you can immediately consume the @shared/ version. If
onboarding session hasn't yet, you have 3 options:
  (a) Wait — coordinate via Q&A
  (b) Build the wrapper page first; consume placeholder when ready
  (c) Build the component yourself with the agreed spec; hand off
      to cross-cutting; onboarding session consumes from shared/
      when ready

Recommend (b) — build ProfileEditComponent skeleton with a stub for
ComplianceStepComponent (just a placeholder div); inject the real
@shared/components/compliance-step component when onboarding +
cross-cutting handoff complete. This unblocks parallel progress.

COMPONENTS YOU IMPLEMENT:
- ProfileEditComponent — page at /profile; loads existing profile via
  ProfileApiService.getProfile(); renders the form via
  @shared/components/compliance-step (mode='edit'); submits via
  ProfileApiService.updateProfile()

ENDPOINTS YOU CONSUME:
- GET /api/v1/seller-profile — read existing
- PUT /api/v1/seller-profile — write update

HAND-OFFS YOUR SESSION RECEIVES:
- From dashboard session: link from dashboard side menu to /profile
- From cross-cutting + onboarding sessions: ComplianceStepComponent
  in @shared/

HAND-OFFS YOUR SESSION PRODUCES:
- To dashboard session: navigation back to /dashboard on save success
- To master: when ProfileEditComponent implemented + tested, mark
  session V1-complete

PERFORMANCE BUDGET (§19):
- features/profile chunk ≤ 80 KB gzip (small — mostly reuses shared
  ComplianceStepComponent)

STOP CONDITIONS:
- ComplianceStepComponent not yet in shared/ when you start — proceed
  with stub per recommendation (b)
- Backend §8 customer module spec ambiguous on PUT response shape
- Design system PARTIAL state — proceed with placeholder

Begin.
```
