# STATUS — FRONTEND

**Owner:** FRONTEND sub-session
**Last update:** 2026-06-04

**Status:** Session not yet started — initialize by opening a new Claude session and pasting the FRONTEND prompt from `docs/SESSION_PROMPTS.md`.

## Current Phase
_pending — set when the session starts_

## Done
- (none)

## In Progress
- (none)

## Blockers
- none

## Next
- (none)

## Hand-offs
- (none)

## Updates Log
=== UPDATE: 2026-06-04 00:00 ===
File initialised by master session. Awaiting first FRONTEND sub-session.
=========

=== UPDATE: 2026-06-04 SESSION-START ===
Task: Initial audit — read all spec docs + current frontend state.

FRAMEWORK NOTE (critical): CLAUDE.md spec says Angular 18. Actual implementation
is React 18 + Vite + Zustand + React Router + Vitest. This session treats React 18
as ground truth and will continue in React 18 unless founder directs otherwise.

AUDIT RESULTS — What exists:
  Pages (all in src/pages/):
    - Landing.jsx           — hero + CTA
    - Onboarding.jsx        — phone OTP + verify (covers /signup + /login)
    - Dashboard.jsx         — catalog grid, stats bar, empty state
    - CatalogCreate.jsx     — simplified form (NOT the full Smart Picker + schema form)
    - CatalogPreview.jsx    — exists (content not yet audited)
    - QualityCheck.jsx      — exists (content not yet audited)
    - PriceCalculator.jsx   — MRP/weight/category → P&L via API
    - ExportPage.jsx        — exists (content not yet audited)

  Components (all in src/components/):
    - Navbar.jsx, CatalogCard.jsx, ImageUploader.jsx
    - PnLBreakdown.jsx, QualityScorecard.jsx

  Services:
    - src/api/client.js     — axios + JWT interceptor + 401 auto-logout ✓
    - src/stores/authStore.js   — Zustand + persist (localStorage) ✓
    - src/stores/catalogStore.js — Zustand catalog state

  Tests: Vitest + @testing-library/react — test files present for all above

ROUTE DELTA (spec vs actual):
  Spec route                    →  Actual route
  /signup, /login               →  /onboarding (merged — gap vs spec)
  /catalogs/new                 →  /catalog/new (path differs)
  /catalogs/:id/edit            →  MISSING
  /catalogs/:id/images          →  /quality/:id (path differs)
  /catalogs/:id/preview         →  /catalog/:id (path differs)
  /catalogs/:id/pricing         →  /pricing (no :id, standalone — gap vs spec)
  /catalogs/:id/export          →  /export/:id ✓

FEATURE GAPS (vs V1_FEATURE_SPEC.md):
  - Smart Category Picker (Feature 2): CatalogCreate is a simple static-category
    select, not the AI-powered 3-card suggestion flow
  - Catalog Edit Form (Feature 3): /catalogs/:id/edit with dynamic schema + autosave
    does not exist
  - AI Autofill UI (Feature 4): autofill button + yellow-highlight diff — missing
  - Image Pre-check Report (Feature 5): PrecheckReportComponent — status unknown
  - Live Preview (Feature 6): feed/detail/mobile mock views — status unknown
  - Export progress poll (Feature 9): ExportProgressComponent — status unknown

Blockers: none yet
Next: Await founder's task assignment
Hand-offs: none
=========
