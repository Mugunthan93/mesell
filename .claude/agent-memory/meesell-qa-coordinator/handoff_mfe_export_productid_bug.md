# Handoff memo → meesell-frontend-coordinator

**Topic:** mfe-export ignores the route productId (V1 XLSX-export is broken end-to-end through the UI)
**From:** meesell-qa-coordinator (session `mesell-qa-wave-1-e2e-session-1`)
**Opened:** 2026-06-22
**Severity:** HIGH (a shipped V1 feature — XLSX Export — is non-functional through the UI)
**Found by:** the QA Wave-1 e2e codify run (PR #385), verified LIVE on the federated stack.

## The bug

`frontend/apps/mfe-export/src/app/export.component.ts`, `onGenerate()` (~L431):

    const productId = 'current-product-id';   // HARDCODED PLACEHOLDER

It never reads `this.route.snapshot.params['id']`. The `ngOnInit` comment admits the
route-read was planned but never wired ("For V1: product ID read from ActivatedRoute
in onGenerate()" — it wasn't).

## Live evidence

Clicking the export Generate button (`export-trigger`) on `/catalogs/{realProductId}/export`
POSTs to `/api/v1/products/current-product-id/export-xlsx` -> 422 (no such product).
Because the request never succeeds, the component never reaches the `ready` state, so the
`export-download` link is UNREACHABLE through the UI for any real product. Not a test
artifact — it reproduces for a real seller.

## Fix

Inject `ActivatedRoute`, read `snapshot.params['id']` (or subscribe to `paramMap`), and use
that id in `onGenerate()` (and anywhere else the placeholder leaks). Keep the change surgical
to `export.component.ts` — do not touch the export service contract or the backend
`/products/{id}/export-xlsx` route (that route is correct; it 422s only because of the bogus id).

## E2E coupling

`frontend/e2e/flows/export.spec.ts` has a passing render test (export page + Generate button
render for a real product) and a `test.fixme('clicking Generate triggers a non-empty file
download', ...)` blocked on THIS bug. The fixme body already carries the real assertions
(download event + .xlsx/.zip filename). Un-fixme that test once the component reads the route
productId — it is the regression guard for this fix.

## Tracking

Recorded on `docs/status/feature_board_qa.md` -> "Inter-lead requests open" (frontend-coordinator,
OPEN) and in the Wave-1 e2e findings table. 48-hour SLA before escalating to the founder.
The resolving lead reads this memo and adds their own incoming-side row on their board — I do
NOT edit `feature_board_frontend.md`.
