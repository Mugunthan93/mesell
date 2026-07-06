# F6 live-preview BACKEND route retirement — 2026-07-06 (fast-mode chore, founder-approved)

**Session:** mesell-live-preview-retire-backend-session-1 (relaunched twice — transient API drop + session limit; worktree `/tmp/mesell-wt/prevret` off origin/develop `c24e158`).

**What / why.** Retired the orphaned backend route `GET /api/v1/products/{id}/preview`
(§10.B.4 Live Product Preview, Feature 6). PR #278 (feat/my-live-listings) was a
FRONTEND-only change — delivered `/catalogs/live` (client-side XLSX parse) and DELETED
the frontend `:id/preview` route/component, but LEFT the backend route mounted
(flag-gated OFF). Founder-approved as action #5 of `docs/status/V1_CONFORMANCE_REPORT.md`.

**Zero-consumer evidence (verified, do not re-derive).**
- Frontend `apps/`+`libs/`+`src/`: NO preview component/service files on disk; NO code
  calls the `/preview` API path. `catalog-list.component.ts onPreview()` navigates to
  `['/catalogs', id, 'edit']` (repointed in PR #395), not the API. `app.routes.ts` has a
  tombstone comment only. `.angular/cache/*results.json` preview specs are STALE cache.
- `frontend/e2e/flows/live-preview.spec.ts` = `test.fixme` empty skip (drives nothing);
  documents the retirement. Not a functional consumer.
- Backend: the only references were the route's OWN tests (retirement scope) + shared
  integration tests with a preview facet (surgically edited).

**⭐ CONVENTION DETERMINATION (reusable pattern for flag-gated route counting).**
Two distinct flag-gating conventions in this codebase:
- **Mount-gated** (e.g. `google/verify`): `if settings.FLAG: app.include_router(...)`.
  Route ABSENT from OpenAPI/route_map when flag off → does NOT count toward the §17
  mounted inventory when off. (CLAUDE.md google-auth amendment: "not mounted when flag
  off → total remains 28".)
- **Handler-gated** (preview was THIS): `@router.get(...)` ALWAYS registered; handler does
  `if not settings.FLAG: raise MeesellError(404, code="feature.live_preview.disabled")`.
  Route is ALWAYS in OpenAPI/route_map; returns a RUNTIME 404 when off → it DID count
  toward the mounted inventory. Confirmed by `test_app_boot_integration.py` asserting the
  path in `allowed_paths` + the route-count, and `test_live_preview_flag_404.py` R1.
→ Because preview was handler-gated, retiring it DECREMENTS: §17 mounted **28 → 27**
  (google flag off), §0.C contract **27 → 26**, `catalog` module **6 → 5**.
Rule of thumb: to know if a flag-gated route counts, check whether the MOUNT or the
HANDLER is gated. Only handler-gated routes count while their flag is off.

**Removed (surgical, nothing shared).**
- `catalog/router.py` — `get_product_preview` handler + `MeesellError` import (orphaned
  after removal — only the preview guard used it) + `ProductPreview{Field,Response}`
  schema imports + docstrings.
- `catalog/service.py` — `get_preview` + `PreviewField`/`ProductPreviewInternal` domain
  imports + `__all__` entry + docstring. (`customer_service` NOT orphaned — still used at
  L543 `assert_eligible_for_super_id`; `category_service` used many places.)
- `catalog/schemas.py` — `ProductPreviewField` + `ProductPreviewResponse` + `__all__` +
  docstring (12→10 models). `Literal` import kept (5 other uses).
- `catalog/domain.py` — `PreviewField` + `ProductPreviewInternal` + `__all__`.
- `catalog/__init__.py` — docstring 6→5 endpoints.
- `shared/config.py` — `FEATURE_LIVE_PREVIEW_ENABLED` field (kept a tombstone comment).
  ⭐ Boot-safe: config `model_config` uses `extra="ignore"` (L93), so lingering
  k8s-injected `FEATURE_LIVE_PREVIEW_ENABLED` env vars are ignored — NO hard dependency on
  infra cleanup ordering (unlike `extra="forbid"` which would crash boot).
- Tests: DELETED `tests/modules/catalog/test_live_preview_route.py` +
  `tests/integration/test_live_preview_flag_404.py` (exclusively preview; no importers —
  the 2 refs in `test_catalog_delete_route.py` are prose docstring mentions, not imports).
  EDITED `test_preview_delete_draft_gap_fill.py` (dropped CAT-BE-40/41/42, kept 43/44/45),
  `test_app_boot_integration.py` (allowed_paths −1; route count `35/34 → 34/33`; docstrings).
- `docs/BACKEND_ARCHITECTURE.md` §17.B row 18 struck + §17.B.2 consolidated F6 amendment
  (convention determination + decrement record) + §2.4 count 6→5 + §10.B.4 RETIRED banner.
- `backend/postman/openapi.json` — removed the preview path + 2 orphan schemas via stdlib
  `json` round-trip (indent=2, ensure_ascii=False to match `gen_openapi.py`) → clean
  140-line deletion, 28 paths / 50 schemas.

**⭐ §19.H multi-tenant Vector 1 repoint (important).** `test_multi_tenant_isolation.py`
Vector 1 was "GET another tenant's /preview → 404". With preview gone it would still pass
but for the WRONG reason (route-not-found 404, not ownership 404) — a latent quality trap.
REPOINTED to `GET /products/{id}/draft` (§10.B.6): verified `get_draft` calls
`assert_product_ownership` BEFORE the None-draft check, so cross-tenant → 404 (not 204).
Keeps the §15.B Layer-2 no-leak vector meaningful. §19.H stays a 4-vector regression.

**Follow-ups flagged (NOT done — out of surgical scope / different owners).**
1. `image.service.get_image_urls` is now DEAD CODE (preview was its only caller). Left in
   place (image module = different owner; documented in LOCKED §11.C + §2.D). Stale image
   docstrings ref `catalog.service.get_preview` (image/service.py L13/35/278/286,
   image/domain.py L13/79). → image-module owner (services-builder) follow-up.
2. `backend/services/svc-catalog/` (MS-migration extraction copy) has a PARALLEL preview
   route + config + `test_svc_catalog_routes.py`. Out of scope (task scoped to `backend/app`
   = the monolith Fly.io serves). → MS-migration program follow-up when svc-catalog lands.
3. `k8s/config.yaml`, `k8s/overlays/staging/config.yaml`, `k8s/svc-catalog/configmap.yaml`
   still set `FEATURE_LIVE_PREVIEW_ENABLED="false"`. Harmless (extra="ignore"). → infra
   cleanup handoff.
4. Other stale doc refs left (locked sections beyond §17 authorization): BACKEND_ARCH
   §10.B.4 body (banner added), line ~7553 test-vector comment, line ~8036 acceptance ✓;
   `docs/MVP_ARCHITECTURE.md`, `docs/V1_FEATURE_SPEC.md`. → future doc-hygiene pass.

**Verification.** stdlib `ast.parse` OK on all 9 edited .py files; residual-symbol sweep
clean (only intentional tombstones + image stale docstrings); `MeesellError`=0 in router,
`Literal`=5 in schemas (no orphan imports). No local Python env (per Director) → full
verification = CI on push (unit/smoke/integration + deploy-backend post-deploy live smoke).

**Rule B (rebuild-localhost-on-merge):** backend `uvicorn --reload :8000` restart deferred
to the founder's next dev session (noted; this chore only pushes to develop).
