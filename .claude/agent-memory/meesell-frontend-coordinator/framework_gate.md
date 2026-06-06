---
name: framework-gate
description: Founder ratified Angular 18 over the existing React scaffold on 2026-06-05; this resolves the gate that blocked all Phase A.5 onwards
metadata:
  type: project
---

# Framework Gate — RESOLVED 2026-06-05

## What happened

Prior session (session-1, 2026-06-04) noted CLAUDE.md spec says Angular 18 but on-disk implementation is React 18 + Vite + Zustand + React Router + Vitest. That session unilaterally decided to "treat React 18 as ground truth and continue in React 18 unless founder directs otherwise" — recorded in STATUS_FRONTEND.md.

I (session-2) surfaced this conflict on session start as the gating decision before any architecture work could proceed.

## Founder's decision (2026-06-05)

**Angular 18 per locked Decision 9.** The React scaffold is to be DELETED at the first specialist dispatch under FRONTEND_ARCHITECTURE.md. No hybrid. No incremental port.

## Why: How to apply

The decision is now LOCKED. Future sessions/specialists must:
1. Treat the React scaffold under `frontend/src/` as dead code awaiting deletion
2. Author all new frontend code in Angular 18 standalone
3. Use my 3 specialists (`meesell-angular-component-builder`, `meesell-angular-service-builder`, `meesell-angular-ui-styler`) — do NOT propose renaming them
4. Reference FRONTEND_ARCHITECTURE.md §0.F.FE-D1 ("React scaffold to be deleted in full") if challenged

If a future session/founder/specialist re-raises the React option, redirect them to FE-D1 and the chain of locked docs that depend on Angular 18: CLAUDE.md D9, V1_FEATURE_SPEC §6, MVP §4 wizard code sample, BACKEND_ARCHITECTURE §1 topology diagram.
