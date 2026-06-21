# Coverage gaps — accumulated across waves

The running ledger of untested (or under-tested) surfaces. Survives between
sessions: read it at the start of every wave so each spec targets the real gaps,
and prune an entry only when a merged test PR closes it.

## Known at bootstrap (2026-06-22)
- **Frontend ships ZERO `data-testid` attributes** (verified across `frontend/apps/`).
  E2E flows are stubbed (`test.fixme`) until selectors are added to components and
  verified live. This is the #1 blocker for the E2E lane — needs a memo to the
  frontend lead.
- E2E flow specs in `frontend/e2e/flows/` are intentional STUBS (onboarding,
  catalog-creation, image-precheck, export, plan-guard, logout-guard). The design
  taxonomy also lists `google-signin` and `category-picker` (not yet stubbed).
- Backend/frontend per-feature coverage to be mapped at Wave-1 dispatch against
  the live `backend/tests/` + `frontend/src/**/*.spec.ts` trees.
