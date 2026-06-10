# FEATURE_PLAN.md — Fast Catalog Form (Feature F3)

| Field | Value |
|---|---|
| Document type | Feature blueprint (planning artifact, NOT production code) |
| Feature slug | `catalog-form` |
| V1 spec reference | `docs/V1_FEATURE_SPEC.md` §F3 |
| Backend contract reference | `docs/BACKEND_ARCHITECTURE.md` §10 (LOCKED 2026-06-05) |
| Frontend contract reference | `docs/FRONTEND_ARCHITECTURE.md` Layer 4 features |
| Related plans | `docs/plans/repo_management/MASTER_PLAN.md` (APPROVED 2026-06-10), `docs/plans/microservices_migration/MASTER_PLAN.md` §3.B (catalog = service 8 of 8, LAST), `docs/plans/module_federation/MASTER_PLAN.md` §4.2 (mfe-catalog 5th remote) |
| Pre-requisite feature plans | `auth-otp` (LOCKED) — JWT prerequisite; `smart-picker` (LOCKED) — seller lands on `/catalogs/:id/edit` AFTER picking category |
| Author | `meesell-backend-coordinator` |
| Status | DRAFT — awaiting founder review |
| Path | `docs/plans/features/catalog-form/FEATURE_PLAN.md` |
| Branch | `feature/catalog-form/planning` |
| Session | `mesell-catalog-form-planning-session-2` |
| Date | 2026-06-10 |

---

The Fast Catalog Form is the **central spine** of MeeSell. `BACKEND_ARCHITECTURE.md §10.A` calls it *"the most-called module in the architecture"* and §16.H / §21 (microservices migration §3.B) make it the **8th-and-LAST** extraction target in V1.5 precisely because four other modules depend on its service surface (`image`, `pricing`, `dashboard`, `export`). Every product flows through it; every catalog-touching feature reads from it. Getting the contract right here means 4 downstream features land cleanly in parallel; getting it wrong means re-coordination across the entire backend lead chain.

This plan locks **before** any line of production code is written. The reason is the **`assert_product_ownership(product_id, user_id)` cross-module signature** at §10.C. Once `services-builder` ships this method, four sibling features (`ai-autofill`, `image-precheck`, `live-preview`, `xlsx-export`) will import it. A rename or signature drift after-the-fact forces simultaneous PRs across all four. The dispatch templates in §7 of this plan cite the locked signature verbatim and forbid variation; that is the single most important contract this plan defends.

Beyond the cross-module seam, catalog-form locks **three operational patterns** that propagate through V1:
1. **Autosave coalescing** (`PATCH /products/{id}` with 5-min audit-event coalescing per `MVP_ARCH §11.4`). This pattern is reused by `image-precheck` polling and `xlsx-export` status reads.
2. **Schema-driven field rendering** (the `templates.schema_jsonb` envelope per `BACKEND_ARCHITECTURE.md §5A`, 11 primitives, `is_advanced` allowlist, `compliance_shape` standard/collapsed). Every downstream feature that touches product fields must agree to this contract.
3. **Draft recovery** (`product_drafts` table + `GET /products/{id}/draft` per §10.B.6 + `MVP_ARCH §11.6`). The pattern is the seller-trust foundation — if a browser tab dies, the seller's work survives.

The Risk Register (§10) tracks five feature-specific risks plus the master plan §1.2 group-token caveat (R6). The dispatch templates (§7) are ready for each lead to paste with the `{N}` session number filled in — no further authoring should be needed at coding time. The review-and-iteration protocol (§8) caps re-dispatches at 3 per specialist before founder escalation, matching the master plan §7.5 48-hour SLA.

---

## Decisions

Six decisions locked by founder before this plan was authored. Recorded verbatim. Three are scope decisions (D1/D2/D3) from the original `PLANNING_DISPATCH.md` Step 1; three are operational decisions (O1/O2/O3) added by founder during this planning session.

### D1 — Scope confirmation

**Locked answer (founder, 2026-06-10):** *Confirm F3 verbatim + autofill OUT.*

Plan covers **5 of 6 catalog endpoints** from `BACKEND_ARCHITECTURE.md §10.B`:
- `POST /api/v1/products` — create (10.B.1)
- `PATCH /api/v1/products/{id}` — autosave + manual save (10.B.2)
- `GET /api/v1/products/{id}/preview` — Live Product Preview (10.B.4)
- `DELETE /api/v1/products/{id}` — soft-delete (10.B.5)
- `GET /api/v1/products/{id}/draft` — draft recovery on browser reload (10.B.6)

`POST /api/v1/products/{id}/autofill` (10.B.3) is **OUT** — owned by the `ai-autofill` feature dispatch.

Frontend ships **schema-driven `FieldRendererComponent` + `AutosaveDirective` + draft recovery + change-category warning dialog + Advanced-fields expander**. The `ai-autofill` feature later layers `AutofillButton` + `FieldDiff` + yellow-highlight overlay on top of these.

All F3 acceptance criteria locked verbatim:
- ≤50 fields rendered per category schema (first-paint **<500ms** after schema fetch).
- Inline `help_text` from XLSX via `field_aliases.help_text`.
- Compulsory red-asterisk + form-cannot-proceed if blank.
- Autosave every **10s + on blur** via `PATCH /api/v1/products/{id}`. Per-IP rate limited at 600/h per §10.B.2.
- Browser reload resumes from `product_drafts` via `GET /products/{id}/draft` per §10.B.6 + `MVP_ARCH §11.6`.
- Change-category mid-edit shows warning + confirm. V1 behavior: **reset `fields_jsonb`, keep product row id**.
- `is_advanced` gating limited to `{group_id}` only per `BACKEND_ARCHITECTURE.md §5A.F` + D2 founder ruling.

### D2 — Feature flag posture

**Locked answer (founder, 2026-06-10):** *`FEATURE_CATALOG_FORM_ENABLED`; dev=true, staging=false until soak passes.*

- **Backend:** env var on the FastAPI app. Relevant route handlers (or the router include in `app/main.py`) honor the flag and return **404** if disabled. Owned by `meesell-services-builder` per master plan §3.2.
- **Frontend:** `core/services/feature-flags.service.ts` runtime boolean (build-time env in V1). `featureFlagGuard` on the `/catalogs/:id/edit` route. Owned by `meesell-angular-service-builder` per master plan §3.2.
- **Dev default:** `true` from day 1.
- **Staging default:** `false` until ALL of:
  - (a) autosave coalescing test passes under simulated network-flap.
  - (b) draft-recovery test passes on browser reload.
  - (c) cross-tenant `assert_product_ownership` leak test passes.
  - (d) concurrent-edit race test passes (two tabs editing same product).
  - (e) 48h soak on dev with no P0/P1 alerts.
- **Flag removed when catalog-form ships to `main`** per master plan §3.2. Carrying past one release is a debt item.

### D3 — Sprint order

**Locked answer (founder, 2026-06-10):** *Lands 3rd — after auth-otp + smart-picker, before any catalog-dependent sibling.*

- `auth-otp` first (JWT prerequisite for `Depends(get_current_user)` on every catalog route per §10.B + §4.B).
- `smart-picker` second (V1 spec §F3 user-journey step 1: seller lands on `/catalogs/:id/edit` AFTER picking category).
- `catalog-form` third. Once it merges to `develop`, the 4 downstream features (`ai-autofill`, `image-precheck`, `live-preview`, `xlsx-export`) unlock for parallel integration-test work. **AI Auto-fill cannot integration-test without a draft product to autofill against.**

### O1 — Agent lineup locked

**Locked answer (founder, 2026-06-10):** Agent lineup, fixed.

- **Backend:** `meesell-database-builder`, `meesell-api-routes-builder`, `meesell-services-builder` (3 specialists).
- **Frontend:** `meesell-angular-component-builder`, `meesell-angular-service-builder`, `meesell-angular-ui-styler` (3 specialists — `ui-styler` added per the new `mee-*` field styling, Advanced-fields expander, change-category dialog, autosave "Saved" indicator, error/saved/advanced states).
- **Data:** `meesell-xlsx-parser` (**CONDITIONAL** — fires only if the `help_text` sweep finds gaps in `smart-picker`'s shipped categories).
- **AI:** NONE — autofill is the `ai-autofill` feature.
- **Auth:** NONE — uses existing `Depends(get_current_user)` seam, no JWT/OTP changes.
- **Infra:** NONE — no new secrets, no new K3s resources, no DB cluster changes.
- **Legal:** NONE.

### O2 — Branch creation playbook

**Locked answer (founder, 2026-06-10):** Lazy-creation per master plan §1.2.

- **THIS session** creates `feature/catalog-form/planning` off `develop` (planning branch).
  - Caveat: "planning" violates master plan §1.2 group taxonomy `{backend, frontend, ai, data, infra}`. Flagged in Risk Register (R6) as candidate for §1.2 amendment.
- `feature/catalog-form` (integration branch) is created by the **backend lead** off `develop` on the day they dispatch their first specialist (database-builder for the migration). **NOT created in this planning session.**
- `feature/catalog-form/backend` is created by the backend lead off `feature/catalog-form` at the moment they dispatch `meesell-database-builder`.
- `feature/catalog-form/frontend` is created by the frontend lead off `feature/catalog-form` at the moment they dispatch their first specialist.
- `feature/catalog-form/data` is created by the data lead off `feature/catalog-form` **ONLY IF** the `help_text` sweep returns gaps.

This is the **lazy-creation path** per master plan §1.2 — minimizes founder ceremony.

### O3 — Per-feature memory hook (catalog-form working agreement)

**Locked answer (founder, 2026-06-10):** Locked as catalog-form working agreement. Candidate for promotion to master plan §6 amendment after this feature ships if it works.

- Every agent maintains per-feature memo files at `.claude/agent-memory/meesell-{role}/feature_{slug}.md` (e.g., `feature_catalog-form.md`).
- The agent's main `MEMORY.md` carries an **index section at the top** listing every feature memo with a one-line summary + link.
- Session headers MUST state explicitly:
  > `Working on feature: catalog-form. Memo file: feature_catalog-form.md.`
  This is how the agent grounds itself in which feature's context to load.
- Session-close protocol appends learnings to the **feature memo** AND updates the **index in `MEMORY.md`**.
- Role-level wisdom (e.g., "always use SQLAlchemy 2.0 typed `select`", "Tailwind 4 syntax for arbitrary values") stays in the main `MEMORY.md`, **NOT** in per-feature memos.

---

## Agent lineup

Per O1 lock. Empty rows shown so the founder sees what was deliberately excluded.

| Lead | Specialists | What each specialist codes | Conditional? |
|---|---|---|---|
| `meesell-backend-coordinator` | `meesell-database-builder` | Extends `app/shared/models/product.py` foundation-pass model with `fields_jsonb` default `'{}'::jsonb`, `deleted_at`, `ai_suggestions_jsonb`. Adds `app/shared/models/product_draft.py` per `MVP_ARCH §11.6`. Authors the Alembic migration with UNIQUE `(user_id, product_id)` on `product_drafts`. The migration is the linchpin — every sibling feature waits on its head. | No |
| `meesell-backend-coordinator` | `meesell-api-routes-builder` | 5 catalog routes per §10.B.1 / .2 / .4 / .5 / .6 (autofill .3 is OUT). Pydantic v2 schemas `CreateProductRequest`, `PatchProductRequest`, `ProductResponse`, `ProductPreviewResponse`, `ProductDraftResponse` in `app/modules/catalog/schemas.py` per §10.E. Per-route rate-limit decorators per §10.B.1-6 (note: PATCH = per-IP only, not per-user, per §10.B.2). OpenAPI regenerated. | No |
| `meesell-backend-coordinator` | `meesell-services-builder` | 10-method `app/modules/catalog/service.py` surface per §10.C: 6 route-internal (`create_product`, `patch_product`, `get_preview`, `soft_delete`, `get_draft` — `autofill_product` OUT) + 4 cross-module surfaces (`assert_product_ownership`, `get_product_for_export`, `list_products`, `get_validation_summary`). Repository in `app/modules/catalog/repository.py` per §10.D. 5-min autosave coalescing helper extension to `app/core/middleware/audit_mw.py` (or `app/core/audit.py`) per `MVP_ARCH §11.4`. `FEATURE_CATALOG_FORM_ENABLED` flag guard at router include in `app/main.py` per D2. | No |
| `meesell-frontend-coordinator` | `meesell-angular-component-builder` | `CatalogFormComponent` (page, standalone, OnPush) at `frontend/src/app/features/catalog-form/`. `FieldRendererComponent` (presentational, dispatches over the 11 primitives per §5A.D). `AutosaveDirective` (debounce + on-blur trigger on the form-group `valueChanges`). Compulsory-fields validator. Change-category warning dialog using `mee-confirm-dialog`. Advanced-fields expander using only `mee-*` UI Kit primitives — **NO direct PrimeNG imports**. | No |
| `meesell-frontend-coordinator` | `meesell-angular-service-builder` | `CatalogService` at `frontend/src/app/features/catalog-form/services/catalog.service.ts` (or shared service location): `create`, `autosave` (PATCH with `X-Autosave: true` header per §10.B.2), `getDraft`, `softDelete`, `getPreview`. HttpClient wiring against generated OpenAPI client. **Offline queue** with exponential-backoff retry on reconnect (network-drop edge case from V1_FEATURE_SPEC §F3). `featureFlagGuard` on `/catalogs/:id/edit` route. **No token in localStorage** per Decision 14 FE-D5 amendment. | No |
| `meesell-frontend-coordinator` | `meesell-angular-ui-styler` | `mee-*` field-error states (red-asterisk for compulsory, WCAG-AA contrast). Advanced-fields expander animation without layout shift. Autosave "Saved" indicator (visible at 360px and 1280px breakpoints). Saved / error / advanced states on rendered fields. Tailwind 4 class additions only — no new tokens. | No |
| `meesell-data-engineer` | `meesell-xlsx-parser` | **CONDITIONAL.** Extends `backend/app/data/field_aliases.json` with missing `help_text` entries for any category referenced by the smart-picker shipped surface. Sweep precondition: verify each `fields[].canonical_name` in every shipped category schema has a `help_text` row. Fires ONLY if the sweep returns gaps. | **Yes (conditional)** |
| `meesell-ai-coordinator` | NONE — out of scope | Autofill UI work (AutofillButton, FieldDiff, yellow-highlight overlay) is owned by the `ai-autofill` feature dispatch. The `autofill.v1` prompt in `app/ai_ops/prompts/autofill_v1.py` is also out of scope here. | — |
| `meesell-auth-builder` (under backend lead) | NONE — out of scope | Catalog routes consume the existing `Depends(get_current_user)` seam locked at §4.B. No JWT/OTP changes. No new auth middleware. No cookie-path changes. | — |
| `meesell-infra-builder` | NONE — out of scope | No new Secret Manager entries. No new K3s resources. No DB cluster changes. The `FEATURE_CATALOG_FORM_ENABLED` env var is set in the standard env-var injection path (dev = `true`, staging = `false`); that is a standard config update, not an infra change. | — |
| `meesell-legal-writer` | NONE — out of scope | No T&C copy changes, no compliance text changes. The Eye-Serum / FSSAI compliance-extension UX (collapsed-shape preview) is consumed AS-IS from `customer.service.get_compliance_block(user_id)` per §8.C; no new legal copy authored for catalog-form. | — |

---

## Code surfaces

Every file the feature will create or modify. Group by domain. Path corrections applied to PLANNING_DISPATCH.md per FRONTEND_ARCHITECTURE.md Layer 4 (`features/catalog-form/`, NOT `pages/catalog-form/`).

### Backend

| File | Action | Owning specialist | Rationale |
|---|---|---|---|
| `backend/app/shared/models/product.py` | MODIFY | database-builder | Extend foundation-pass model with `fields_jsonb` (default `'{}'::jsonb`), `ai_suggestions_jsonb`, `deleted_at` per `MVP_ARCH §2.4`. |
| `backend/app/shared/models/product_draft.py` | NEW | database-builder | Draft revision table per `MVP_ARCH §11.6`. UNIQUE `(user_id, product_id)`. |
| `backend/alembic/versions/<rev>_catalog_form.py` | NEW | database-builder | Single migration: `products` extension + `product_drafts` table + indexes. Reversible upgrade + downgrade. |
| `backend/app/modules/catalog/router.py` | NEW | api-routes-builder | 5 routes per §10.B.1 / .2 / .4 / .5 / .6. Autofill OUT. |
| `backend/app/modules/catalog/schemas.py` | NEW | api-routes-builder | Pydantic v2: `CreateProductRequest`, `PatchProductRequest`, `ProductResponse`, `ProductPreviewResponse`, `ProductDraftResponse` per §10.E. PRIVATE wire-shape per §16.C. |
| `backend/app/modules/catalog/service.py` | NEW | services-builder | 10-method surface per §10.C. Cross-module surfaces PUBLIC per §16.A; route-internal helpers private. |
| `backend/app/modules/catalog/repository.py` | NEW | services-builder | Methods per §10.D. PRIVATE per §16.A. All use `scope_to_user(user_id)` per §4.C. |
| `backend/app/modules/catalog/domain.py` | NEW | services-builder | Frozen dataclasses for cross-module returns (`ExportSnapshot`, `ValidationSummary`, `PaginatedProducts`, `ProductDraft`) per §10.F + §16.C. |
| `backend/app/modules/catalog/exceptions.py` | NEW | services-builder | `CatalogError` hierarchy per §10.G: `ProductNotFoundError`, `CatalogNotFoundError`, `ValidationFailedError`. |
| `backend/app/core/middleware/audit_mw.py` (or `app/core/audit.py`) | MODIFY | services-builder | Add 5-min coalescing helper for `catalog.product.updated` per `MVP_ARCH §11.4`. Valkey DB 0 window key `audit:coalesce:{user_id}:{product_id}`. |
| `backend/app/main.py` | MODIFY | services-builder | Include `catalog.router` behind `FEATURE_CATALOG_FORM_ENABLED` flag per D2; return 404 if disabled. |
| `backend/app/config.py` | MODIFY | services-builder | Add `FEATURE_CATALOG_FORM_ENABLED: bool = True` to `Settings` per master plan §3.2. |
| `backend/tests/test_catalog_unit.py` | NEW | services-builder | Unit tests: per-field validators against §5A.D primitives; coalescing helper window math; ownership-assertion 404 cases. |
| `backend/tests/test_catalog_form_integration.py` | NEW | backend-coordinator (integration-stitch) | `TestFullProductLifecycle`, `TestDraftRecoveryAfterSimulatedClose`, `TestCrossModuleOwnershipAssertion` per §10.J + master plan §2.1 advisory CI gate 4. |

### Frontend

| File | Action | Owning specialist | Rationale |
|---|---|---|---|
| `frontend/src/app/features/catalog-form/catalog-form.component.ts` | NEW | angular-component-builder | Page component (standalone, OnPush). Schema fetch → reactive form build → autosave cycle → draft recovery → change-category dialog. |
| `frontend/src/app/features/catalog-form/catalog-form.component.html` | NEW | angular-component-builder | Template using `mee-input`, `mee-select`, `mee-textarea`, etc. NO PrimeNG. |
| `frontend/src/app/features/catalog-form/catalog-form.component.scss` | NEW | angular-ui-styler | Tailwind 4 class additions; Advanced-fields expander animation; "Saved" indicator positioning. |
| `frontend/src/app/features/catalog-form/components/field-renderer/field-renderer.component.ts` | NEW | angular-component-builder | Presentational. Dispatches on `data_type` × `primitive` per §5A.D (11 primitives). Throws typed error on unknown primitive (NOT silent skip — see Risk R4). |
| `frontend/src/app/features/catalog-form/directives/autosave.directive.ts` | NEW | angular-component-builder | Debounce on form-group `valueChanges` (NOT individual field blur). On-blur trigger. Hooks `CatalogService.autosave` with `X-Autosave: true`. |
| `frontend/src/app/features/catalog-form/services/catalog.service.ts` | NEW | angular-service-builder | `create`, `autosave`, `getDraft`, `softDelete`, `getPreview`. Offline queue + exponential backoff with jitter (cap 30s). |
| `frontend/src/app/features/catalog-form/guards/feature-flag.guard.ts` | NEW | angular-service-builder | Route guard reading `core/services/feature-flags.service.ts` for `FEATURE_CATALOG_FORM_ENABLED`. |
| `frontend/src/app/features/catalog-form/models/catalog-form.types.ts` | NEW | angular-component-builder | TS types mirroring `ProductResponse`, `ProductDraftResponse`, etc. Sourced from generated OpenAPI client where possible. |
| `frontend/src/app/app.routes.ts` | MODIFY | angular-service-builder | Register `/catalogs/:id/edit` route lazy-loading `CatalogFormComponent` behind `featureFlagGuard`. |
| `frontend/src/app/core/services/feature-flags.service.ts` | MODIFY (or NEW) | angular-service-builder | Add `FEATURE_CATALOG_FORM_ENABLED` runtime boolean per D2. |
| `frontend/src/app/features/catalog-form/catalog-form.component.spec.ts` | NEW | angular-component-builder | Unit tests: 11-primitive coverage + unknown-primitive throws + compulsory-field validator + change-category dialog confirmation flow. |

### AI / Data

| File | Action | Owning specialist | Rationale |
|---|---|---|---|
| `backend/app/data/field_aliases.json` | MODIFY **(CONDITIONAL)** | xlsx-parser | ONLY if `help_text` sweep finds gaps in `smart-picker` shipped categories. Schema version bump recorded in data lead `MEMORY.md`. |

### Infra

NONE. (Adding `FEATURE_CATALOG_FORM_ENABLED` to dev/staging env-var injection is a standard config update, not an infra change.)

### Files explicitly NOT touched in catalog-form scope

| File | Why excluded | Owning feature |
|---|---|---|
| `frontend/src/app/features/catalog-form/components/autofill-button/*` | Autofill UI is out of scope per D1 | `ai-autofill` |
| `frontend/src/app/features/catalog-form/components/field-diff/*` | Yellow-highlight overlay is out of scope per D1 | `ai-autofill` |
| `backend/app/modules/catalog/router.py` — `POST /products/{id}/autofill` route | §10.B.3 is out of scope per D1 | `ai-autofill` |
| `backend/app/ai_ops/prompts/autofill_v1.py` | Prompt content owned by prompt-engineer | `ai-autofill` |
| `backend/app/modules/catalog/service.py` — `autofill_product` method | One of the 6 route-internal surfaces; OUT per D1 | `ai-autofill` |
| `backend/app/modules/catalog/service.py` — `update_ai_suggestions_jsonb` repository method | Used only by autofill flow | `ai-autofill` |
| `app/modules/image/*` | Image upload not part of catalog-form | `image-precheck` |
| `app/modules/pricing/*` | P&L computation not part of catalog-form | `price-calculator` |

If a specialist's planning conversation drifts into any of these, the lead refuses the drift with **"that belongs to the ai-autofill feature dispatch (or image-precheck / price-calculator); flag it on the corresponding `feature_board_{domain}.md` and continue."**

---

## Documentation deliverables

What "documented" means for this feature. Each item is an acceptance-gate condition.

### Backend

- **OpenAPI entries** auto-generated for the 5 catalog routes (POST create / PATCH autosave / GET preview / DELETE soft-delete / GET draft). Verify by inspecting `/openapi.json` after the migration is up and the routes are mounted.
- **Inline service-method docstrings** on every **cross-module surface** in `app/modules/catalog/service.py` per §16.A consumer-reference convention. Specifically:
  - `assert_product_ownership(product_id, user_id) -> None` — docstring MUST list consumers (`image.service` + `pricing.service` + `dashboard.service` + `export.service`) and cite §10.C.
  - `get_product_for_export(product_id, user_id) -> ExportSnapshot` — docstring lists consumer (`export.service`) and cites §10.C.
  - `list_products(user_id, pagination) -> PaginatedProducts` — docstring lists consumer (`dashboard.service`) and cites §10.C.
  - `get_validation_summary(user_id, product_id) -> ValidationSummary` — docstring lists consumer (`dashboard.service`) and cites §10.C.
- **`docs/BACKEND_ARCHITECTURE.md §10` sentinel flip** from `spec` to `implemented YYYY-MM-DD with PR #<num>` once merged to `develop`. Append-only note; do NOT modify the LOCKED contract text.

### Frontend

- **Route entry comment** in `app.routes.ts` documenting `/catalogs/:id/edit` lazy load + `featureFlagGuard`.
- **`CatalogFormComponent` docstring** at the class level describing the **schema-fetch → reactive-form-build → autosave-cycle → draft-recovery** flow, with explicit reference to `BACKEND_ARCHITECTURE.md §5A` for the schema envelope.
- **`AutosaveDirective` docstring** explaining debounce window (form-group `valueChanges`), on-blur trigger, and retry semantics (exponential backoff with jitter, cap 30s).

### AI

N/A — autofill is out of scope.

### Data

- `field_aliases.json` schema version bump recorded in `.claude/agent-memory/meesell-data-engineer/MEMORY.md` note — **ONLY IF** rows added.

### Infra

N/A.

### Cross-cutting

- **`docs/V1_FEATURE_SPEC.md §F3`** marked **"implemented YYYY-MM-DD"** with PR link.
- **`tests/lint/import_rules.toml`** per `BACKEND_ARCHITECTURE.md §16.G` — entries added for the 4 new cross-module call sites (`catalog.service` consumed by `image`, `pricing`, `dashboard`, `export`). Confirms the §2.D cross-module matrix is unchanged (no new ✗ → ✓).
- **`docs/MVP_ARCHITECTURE.md §11.4`** cross-link to the merged `catalog.service.patch_product` (autosave coalescing helper) implementation.
- **`docs/status/STATUS_BACKEND.md`** Updates Log entry with PR URL.
- **`docs/status/feature_board_backend.md`** row `MERGED` with PR link in Notes.

---

## Branch setup

Operationalizes O2. Per master plan §1.2.

| Branch | Parent | Created by | Created when | Deleted when |
|---|---|---|---|---|
| `feature/catalog-form/planning` | `develop` | `meesell-backend-coordinator` (this session) | 2026-06-10 (this session) | After PR to `develop` merges (founder squash) |
| `feature/catalog-form` | `develop` | `meesell-backend-coordinator` (backend lead) | At the moment `meesell-database-builder` is dispatched | After PR to `develop` merges (founder squash) |
| `feature/catalog-form/backend` | `feature/catalog-form` | `meesell-backend-coordinator` (backend lead) | At the moment `meesell-database-builder` is dispatched | After PR to `feature/catalog-form` merges (lead squash) |
| `feature/catalog-form/frontend` | `feature/catalog-form` | `meesell-frontend-coordinator` (frontend lead) | At the moment first frontend specialist is dispatched | After PR to `feature/catalog-form` merges (lead squash) |
| `feature/catalog-form/data` | `feature/catalog-form` | `meesell-data-engineer` (data lead) | **ONLY IF** `help_text` sweep finds gaps | After PR to `feature/catalog-form` merges (lead squash) |

**Master plan §1.2 invariants honored:**
- Every group branch parents on the feature integration branch, never directly on `develop`.
- Group branches are created **at dispatch time**, not pre-allocated (lazy creation).
- Lead merges group → feature; founder merges feature → develop (per D1 of master plan §2.2).

**Group-token caveat:** `feature/catalog-form/planning` uses `planning` as the 6th group token, which is NOT in the master plan §1.2 locked taxonomy `{backend, frontend, ai, data, infra}`. Flagged as Risk R6. Mitigation: this is the same pattern already used for `feature/auth-otp/planning` and `feature/smart-picker/planning` per the established sibling-feature practice; promotion to a §1.2 amendment after this plan ships, OR alternative for future features is `docs-only` PRs without a group branch.

---

## Memory protocol

Operationalizes O3. Catalog-form working agreement.

### Memo file path convention

`.claude/agent-memory/meesell-{role}/feature_catalog-form.md`

Example paths for this feature:
- `.claude/agent-memory/meesell-backend-coordinator/feature_catalog-form.md` (the lead's own memo)
- `.claude/agent-memory/meesell-database-builder/feature_catalog-form.md`
- `.claude/agent-memory/meesell-api-routes-builder/feature_catalog-form.md`
- `.claude/agent-memory/meesell-services-builder/feature_catalog-form.md`
- `.claude/agent-memory/meesell-frontend-coordinator/feature_catalog-form.md`
- `.claude/agent-memory/meesell-angular-component-builder/feature_catalog-form.md`
- `.claude/agent-memory/meesell-angular-service-builder/feature_catalog-form.md`
- `.claude/agent-memory/meesell-angular-ui-styler/feature_catalog-form.md`
- `.claude/agent-memory/meesell-xlsx-parser/feature_catalog-form.md` (conditional)

### MEMORY.md index format

The agent's main `MEMORY.md` carries an index section near the top:

```markdown
## Per-feature memos (index)

- [feature_auth-otp.md](feature_auth-otp.md) — one-line status
- [feature_catalog-form.md](feature_catalog-form.md) — catalog-form planning locked 2026-06-10; PR #<num> open; 6 specialists queued
- ...
```

### Session-header tagline format

Every session opens with this exact line in the agent's first log entry:

> `Working on feature: catalog-form. Memo file: feature_catalog-form.md.`

This is how the agent grounds itself: read the feature memo BEFORE the role-level `MEMORY.md` to load the feature-specific context first.

### Session-close protocol

At session close, the agent:
1. Appends learnings to `.claude/agent-memory/meesell-{role}/feature_catalog-form.md` (NEW file on first session; append-only thereafter).
2. Updates the index entry in `.claude/agent-memory/meesell-{role}/MEMORY.md` with the latest one-line status (date + state + PR URL if any).
3. Role-level wisdom (e.g., "SQLAlchemy 2.0 typed `select` always", "Tailwind 4 arbitrary-value syntax") goes to the main `MEMORY.md` as before, **NOT** to the feature memo.

### Role-level vs feature-level memory — concrete examples (backend-coordinator)

| Goes to main `MEMORY.md` | Goes to `feature_catalog-form.md` |
|---|---|
| "Always use SQLAlchemy 2.0 typed `select`" | "Autosave coalescing implemented in `core/middleware/audit_mw.py` via 5-min Valkey window keyed `audit:coalesce:{user_id}:{product_id}`" |
| "Cross-module calls go via `service.py` PUBLIC surfaces per §16.A" | "`assert_product_ownership` signature locked as `async def assert_product_ownership(product_id: UUID, user_id: UUID) -> None`; raises `ProductNotFoundError` mapped to 404" |
| "Locked lock-protocol: section LOCKED updates STATUS_BACKEND.md + STATUS_MASTER.md" | "Catalog migration parent revision was `f31c75438e61`; head after merge `<sha>`" |
| "PR template requires Test evidence + Migration evidence sections" | "Re-dispatch happened twice on services-builder for autosave-coalescing window math; founder escalation prevented" |

---

## Dispatch templates

One template per specialist. Each is ready for the lead to paste into an `Agent()` call with the `{N}` session number filled in. The session name MUST follow `mesell-catalog-form-{group}-session-{N}` per master plan §4.

### Template 1 — `meesell-database-builder`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-backend-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Author the catalog-form database migration. Extend the foundation-pass `products` model and create the `product_drafts` table per `MVP_ARCH §11.6`. The migration is the linchpin — four downstream features (`ai-autofill`, `image-precheck`, `live-preview`, `xlsx-export`) wait on its head revision.

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-database-builder/MEMORY.md` (your own memory)
2. `.claude/agent-memory/meesell-database-builder/feature_catalog-form.md` (per O3; create if missing — this is session 1)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan — §10.D + §10.F + the Code Surfaces table)
4. `docs/BACKEND_ARCHITECTURE.md` §10.D (repository), §10.F (domain types), §5.E (`shared/models/` 13-table import path lock)
5. `docs/MVP_ARCHITECTURE.md` §2.4 (DDL authority for `catalogs`, `products`) + §11.6 (DDL authority for `product_drafts`) + §2.6 (migration ordering)
6. `backend/app/shared/models/product.py` (foundation-pass current state) — read before extending
7. `backend/alembic/versions/` — find the current head, your new migration must parent on it

## Acceptance criteria
- `app/shared/models/product.py` extended with `fields_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)`, `ai_suggestions_jsonb`, `deleted_at: Mapped[datetime | None]`, `status: Mapped[Literal["draft", "ready"]]`.
- `app/shared/models/product_draft.py` created. ProductDraft has `user_id`, `product_id`, `fields_jsonb`, `autosave_count`, `last_updated`. **UNIQUE constraint on `(user_id, product_id)` per `MVP_ARCH §11.6`** — non-negotiable.
- Alembic migration `<rev>_catalog_form.py` created in `backend/alembic/versions/`. Parent revision MUST be the current head of `develop` at dispatch time. Run `alembic heads` and confirm dev + staging are converged before authoring.
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` produces no row loss on a seed-data fixture. Test evidence pasted in the PR's Migration evidence section per master plan §5.2.
- Indexes: on `products.user_id`, `products.catalog_id`, `products.category_id`, `products.deleted_at`. On `product_drafts.user_id`, `product_drafts.product_id`. (Covers the queries in §10.D.)
- 11 unit tests in `backend/tests/test_database.py` cover the new shape (existing pattern from the foundation pass — check session-2 close-out memory note).

## Hard constraints
- The Alembic migration MUST be reversible. `downgrade()` MUST DROP all new columns + the new table cleanly with NO data side effects.
- Migration parent revision MUST match `develop` head at dispatch time. If staging has diverged, escalate to backend lead BEFORE authoring; the lead coordinates with infra to converge.
- NO direct SQL strings in the model file. Use SQLAlchemy 2.0 `Mapped[T]` style + `mapped_column` per `BACKEND_ARCHITECTURE.md §5.E`.
- NO touch to autofill-related fields. `ai_suggestions_jsonb` is added (it is read by export per §10.B.4 even when autofill UI is OUT) but no autofill migration logic.
- NO touch to `image`, `pricing`, `dashboard`, `export`, `category`, `customer`, `iam` model files.

## Files you MAY touch
- `backend/app/shared/models/product.py` (MODIFY)
- `backend/app/shared/models/product_draft.py` (NEW)
- `backend/app/shared/models/__init__.py` (MODIFY — export ProductDraft)
- `backend/alembic/versions/<rev>_catalog_form.py` (NEW)
- `backend/tests/test_database.py` (MODIFY — add tests for the new shape)

## Files you must NOT touch
- Any other module's model file
- `backend/app/modules/catalog/router.py` or `service.py` or `repository.py` (those are api-routes-builder / services-builder)
- `frontend/**` (different group)
- `app/main.py` (services-builder)

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session-1 entry recording: alembic parent revision used, new head sha after the migration, the `assert_product_ownership` signature you are setting up the schema for (cite §10.C verbatim).
2. Update `MEMORY.md` index: `- [feature_catalog-form.md](feature_catalog-form.md) — catalog-form DB migration session {N} open; parent rev <sha>`.

## Final report format
- PR URL (`feature/catalog-form/backend` → `feature/catalog-form`)
- Migration head sha before and after
- `alembic upgrade head` / `downgrade -1` / `upgrade head` evidence (paste the alembic output)
- Test results: 11 of 11 unit tests green (paste pytest -v output)
- Files changed (list with absolute paths)
- Any deviation from §10.D / §10.F / §5.E (should be none — flag anything)
```

### Template 2 — `meesell-api-routes-builder`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-backend-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Author the 5 catalog routes (POST create / PATCH autosave / GET preview / DELETE soft-delete / GET draft) per `BACKEND_ARCHITECTURE.md §10.B.1 / .2 / .4 / .5 / .6`. Author the Pydantic v2 schemas per §10.E. Autofill route §10.B.3 is OUT — owned by `ai-autofill` feature dispatch.

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-api-routes-builder/MEMORY.md`
2. `.claude/agent-memory/meesell-api-routes-builder/feature_catalog-form.md` (per O3; create if missing)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan)
4. `docs/BACKEND_ARCHITECTURE.md` §10.B (all 6 endpoints — read .3 to know what NOT to ship) + §10.E (schemas) + §4.B (`get_current_user` seam) + §4.G (per-route rate-limit decorator pattern)
5. `docs/V1_FEATURE_SPEC.md` §F3 (acceptance criteria the routes must satisfy)
6. `docs/plans/repo_management/MASTER_PLAN.md` §5.2 (backend PR template — your PR will be graded against it)
7. `backend/app/modules/catalog/service.py` after services-builder has shipped it (or stub against the signatures in §10.C — coordinate with services-builder via the lead)

## Acceptance criteria
- 5 routes match §10.B.1 / .2 / .4 / .5 / .6 **verbatim** for: request-body shape, response-body shape, status codes, rate-limit decorator config.
- **`PATCH /products/{id}` rate limit is PER-IP, NOT per-user** per §10.B.2. A per-user limit would degrade autosave UX.
- `POST /products` decorated with both `@rate_limit(scope="create_product", limit="20/h", key="user_id")` AND plan_guard check inside the service per §10.B.1.
- `DELETE /products/{id}` returns 204 (no body); ownership-assertion seam scopes `deleted_at IS NULL` so a re-delete returns 404 NOT 204.
- `GET /products/{id}/draft` returns 200 with body if draft exists, **204 if no draft** (rare case — programmatic create + immediate status=ready). Status code distinction MUST be honored per §10.B.6.
- 5 Pydantic schemas (`CreateProductRequest`, `PatchProductRequest`, `ProductResponse`, `ProductPreviewResponse`, `ProductDraftResponse`) match §10.E **verbatim**. Use Pydantic v2 `Field()` constraints; no `BaseModel.Config` (deprecated in v2 — use `model_config = ConfigDict(...)`).
- OpenAPI regenerated. `/openapi.json` includes all 5 routes with their full shape.
- `Depends(get_current_user)` on every route per §4.B.

## Hard constraints
- The `assert_product_ownership` cross-module signature is the contract — every sibling feature will call this method. NO rename. NO signature variation. Cite §10.A + §10.C in commit body.
- NO import of `adapters/gemini.py` directly — autofill is OUT and the import would be wrong even if it were in scope (must go via `ai_ops.client` per §16.A).
- NO touch to `service.py` business logic — call the service surface, do not reimplement. The router is a thin shim per `BACKEND_ARCHITECTURE.md §3.C`.
- NO touch to other modules' routers.
- `schemas.py` is PRIVATE wire-shape per §16.C — NOTHING outside `catalog/` may import from it.
- The `POST /products/{id}/autofill` route MUST NOT be added (autofill is owned by ai-autofill feature per D1).

## Files you MAY touch
- `backend/app/modules/catalog/router.py` (NEW)
- `backend/app/modules/catalog/schemas.py` (NEW)
- `backend/app/modules/catalog/__init__.py` (MODIFY)
- `backend/tests/test_catalog_routes.py` (NEW — happy-path + error-status code per endpoint)

## Files you must NOT touch
- `service.py`, `repository.py`, `domain.py`, `exceptions.py` (services-builder)
- Any other module
- `app/main.py` (services-builder owns the router include + feature-flag guard)
- `frontend/**`

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session entry recording the locked rate-limit decorators and per-route audit posture you implemented.
2. Update `MEMORY.md` index.

## Final report format
- PR URL (`feature/catalog-form/backend` → `feature/catalog-form`)
- 5 route signatures (paste the `@router.post` / `@router.patch` etc. lines)
- OpenAPI before/after diff for `/openapi.json`
- Test results (paste pytest -v output)
- Files changed (absolute paths)
- Any deviation from §10.B.* (should be none — flag anything)
```

### Template 3 — `meesell-services-builder`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-backend-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Author the 10-method `app/modules/catalog/service.py` surface per `BACKEND_ARCHITECTURE.md §10.C`. Author the `repository.py`, `domain.py`, `exceptions.py`. Extend `core/middleware/audit_mw.py` (or `core/audit.py`) with the 5-min autosave coalescing helper per `MVP_ARCH §11.4`. Wire the `FEATURE_CATALOG_FORM_ENABLED` flag in `app/main.py` per D2.

Skip the `autofill_product` route-internal method — that is the 6th and it belongs to `ai-autofill` per D1. Ship the 5 route-internal + 4 cross-module surfaces = 9 methods (10 minus autofill).

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-services-builder/MEMORY.md`
2. `.claude/agent-memory/meesell-services-builder/feature_catalog-form.md` (per O3; create if missing)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan)
4. `docs/BACKEND_ARCHITECTURE.md` §10.A (preamble — the central spine framing) + §10.C (service signatures — VERBATIM) + §10.D (repository) + §10.G (exception hierarchy) + §5A.B-F (presentation contract: schema_jsonb envelope, 11 primitives, is_advanced allowlist, compliance_shape) + §10.B.2 step sequence (autosave + 5-min coalescing) + §16.A-C (cross-module call rules + file-level public/private)
5. `docs/MVP_ARCHITECTURE.md` §11.4 (autosave coalescing window math) + §11.6 (draft recovery semantics)
6. `backend/app/core/middleware/audit_mw.py` current state — you are extending, not replacing
7. `docs/plans/repo_management/MASTER_PLAN.md` §3.2 (feature flag posture)

## Acceptance criteria
- `app/modules/catalog/service.py` exposes **9 of 10** locked signatures from §10.C verbatim (skip `autofill_product` per D1):
  - 5 route-internal: `create_product`, `patch_product`, `get_preview`, `soft_delete`, `get_draft`
  - 4 cross-module PUBLIC: `assert_product_ownership`, `get_product_for_export`, `list_products`, `get_validation_summary`
- **`assert_product_ownership(product_id: UUID, user_id: UUID) -> None`** matches §10.C verbatim. Raises `ProductNotFoundError` mapped to 404 if not owned OR if `deleted_at IS NOT NULL`. **NO rename, NO signature variation.**
- `repository.py` matches §10.D verbatim (8 methods). Every method takes `user_id` per §4.C `scope_to_user` rule. Method-private — no other module imports from this file.
- `domain.py` defines `ExportSnapshot`, `ValidationSummary`, `PaginatedProducts`, `ProductDraft` as frozen dataclasses per §10.F. These are the cross-module exchange currency per §16.C.
- `exceptions.py` defines `CatalogError` base + `ProductNotFoundError`, `CatalogNotFoundError`, `ValidationFailedError` with `validation_message_id` per §5A.H convention.
- **`patch_product` autosave coalescing**: when called with `is_autosave=True`, additionally upserts `product_drafts` per `MVP_ARCH §11.6`. The audit-event coalescing happens in middleware; the service surface does NOT manage the audit window itself.
- **Audit coalescing helper** in `core/middleware/audit_mw.py`: 5-min rolling window keyed `audit:coalesce:{user_id}:{product_id}` in Valkey DB 0. First PATCH in window writes a new `audit_events` row; subsequent PATCHes update `payload_jsonb.coalesced_count += 1` and `payload_jsonb.last_seen_at`. Test passes the 5-min window math in `backend/tests/test_audit_coalescing.py`.
- **`FEATURE_CATALOG_FORM_ENABLED` flag**: `app/main.py` includes `catalog.router` ONLY if `settings.FEATURE_CATALOG_FORM_ENABLED`. When disabled, requests return 404. Add `FEATURE_CATALOG_FORM_ENABLED: bool = True` to `app/config.py` Settings.
- Cross-tenant `assert_product_ownership` leak test passes: two users, user A creates product, user B requests it → 404 with `catalog.product_not_found`.
- Concurrent-edit race test passes: two tabs editing same product, PATCH twice within 100ms → last-write-wins on `fields_jsonb || :patch`; no row corruption; both autosave snapshots end up in `product_drafts` (autosave_count = 2).

## Hard constraints
- The `assert_product_ownership` cross-module signature is the contract — NO rename, NO signature variation. Cite §10.A + §10.C in commit body.
- **NO direct `adapters/gemini.py` import** in the catalog module. Autofill is OUT, but even if it were in, the AI seam is `ai_ops.client.call_gemini` per §16.A.
- **`schemas.py` is PRIVATE wire-shape per §16.C** — cross-module exchange goes through `domain.py` frozen dataclasses.
- **Cross-module calls** to `customer.service` and `category.service` go via PUBLIC `service.py` surfaces per §16.A. NEVER import another module's `repository.py` or `schemas.py`.
- Service methods are all `async`. NO sync queries.
- NO direct touch to other modules' files.
- NO touch to `frontend/**`.
- `repository.py` methods all use `core.tenancy.scope_to_user(user_id)` per §4.C — every owned-table read or write carries `user_id`. The §19 import-linter audits this.

## Files you MAY touch
- `backend/app/modules/catalog/service.py` (NEW)
- `backend/app/modules/catalog/repository.py` (NEW)
- `backend/app/modules/catalog/domain.py` (NEW)
- `backend/app/modules/catalog/exceptions.py` (NEW)
- `backend/app/modules/catalog/__init__.py` (MODIFY)
- `backend/app/core/middleware/audit_mw.py` (MODIFY — add coalescing helper)
- `backend/app/main.py` (MODIFY — feature-flag-guarded router include)
- `backend/app/config.py` (MODIFY — add `FEATURE_CATALOG_FORM_ENABLED`)
- `backend/tests/test_catalog_unit.py` (NEW)
- `backend/tests/test_audit_coalescing.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/catalog/router.py` (api-routes-builder)
- `backend/app/modules/catalog/schemas.py` (api-routes-builder)
- `backend/app/shared/models/*` (database-builder)
- `backend/alembic/versions/*` (database-builder)
- Any other module
- `frontend/**`

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session entry recording: the 9 method signatures shipped, the audit-coalescing helper Valkey key format, the feature-flag wiring file paths.
2. Update `MEMORY.md` index.

## Final report format
- PR URL (`feature/catalog-form/backend` → `feature/catalog-form`)
- 9 service method signatures (paste from `service.py`)
- Audit coalescing test result (paste pytest output)
- Cross-tenant leak test result (paste pytest output)
- Concurrent-edit race test result (paste pytest output)
- Files changed (absolute paths)
- Any deviation from §10.C / §10.D / §10.F / §10.G (should be none — flag anything)
```

### Template 4 — `meesell-angular-component-builder`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-frontend-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Author `CatalogFormComponent` (page, standalone, OnPush) + `FieldRendererComponent` (presentational, 11-primitive dispatcher) + `AutosaveDirective` at `frontend/src/app/features/catalog-form/`. Compulsory-fields validator. Change-category warning dialog using `mee-confirm-dialog`. Advanced-fields expander using only `mee-*` UI Kit primitives.

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-angular-component-builder/MEMORY.md`
2. `.claude/agent-memory/meesell-angular-component-builder/feature_catalog-form.md` (per O3; create if missing)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan)
4. `docs/FRONTEND_ARCHITECTURE.md` Layer 4 features (`features/catalog-form/` location), Layer 2 `mee-*` UI Kit primitives (the 17 PrimeNG wrappers — your abstraction wall)
5. `docs/V1_FEATURE_SPEC.md` §F3 (acceptance criteria — ≤50 fields, <500ms first-paint, compulsory red-asterisk, autosave every 10s + on blur, browser-reload resume, change-category warning, Advanced-fields toggle for `group_id`)
6. `docs/BACKEND_ARCHITECTURE.md` §5A.B (schema_jsonb 6-key envelope), §5A.C (per-field 9-key shape), §5A.D (11-primitive mapping), §5A.F (is_advanced allowlist `{group_id}` + compliance_shape standard/collapsed), §5A.H (validation_message_id convention)
7. `frontend/src/app/ui/` (the 17 `mee-*` components — read the public API of `mee-input`, `mee-select`, `mee-textarea`, `mee-confirm-dialog` before authoring)
8. `frontend/src/app/features/catalog-form/services/catalog.service.ts` (or stub against the planned signatures — coordinate with angular-service-builder via the frontend lead)

## Acceptance criteria
- **11-primitive dispatch coverage**: `FieldRendererComponent` covers every primitive in `BACKEND_ARCHITECTURE.md §5A.D` (text_short, text_long, integer, number, boolean, date, url, dropdown_static, dropdown_category, multiselect_static, multiselect_category). For **unknown primitives** (V1.5 will add a 12th), the component MUST **throw a typed error** (NOT silent skip). A unit test confirms this.
- **50-field render <500ms** first-paint. Measured via Angular DevTools Profile on a synthetic 50-field schema. Use `trackBy` on the field-renderer `*ngFor`; OnPush change detection on `FieldRendererComponent`.
- **Compulsory-field validator** blocks `status="ready"` transition with `validation_message_id="validation.completeness.missing_compulsory"`. Form-cannot-proceed UX is wired to the "Save" / "Submit" button.
- **Red-asterisk styling** on every field whose schema entry has `compulsory: true`. Drives off `mee-input[required]` (and `mee-select[required]` etc.) — no inline asterisk markup.
- **`AutosaveDirective`** debounces on the **form-group `valueChanges`** (NOT individual field blur). Window: 10s per V1 spec. Additional trigger on `blur` of any field. Calls `CatalogService.autosave(productId, fieldsPatch)` with `X-Autosave: true`.
- **Change-category warning dialog** uses `mee-confirm-dialog`. Confirm button label = "Discard fields and switch category" (explicit per Risk R3 — no default-confirm). Cancel reverts the category selection.
- **Advanced-fields expander** wraps all fields with `is_advanced: true`. V1 = `group_id` only per §5A.F + D2 — but the component MUST be schema-driven (read `is_advanced` from the per-field shape), not hardcoded.
- **Schema-fetch → reactive-form-build** flow: on init, fetch schema via `CategoryService.getSchema(categoryId)` → build `FormGroup` from `schema.fields[*]` → fetch draft via `CatalogService.getDraft(productId)` → patch the FormGroup with draft fields if present.
- **Browser-reload resume** test: simulate page reload after 5 fields filled; on remount, the form pre-populates from `GET /products/{id}/draft`.

## Hard constraints
- **PrimeNG imports are FORBIDDEN outside `src/app/ui/`** — use `mee-*` primitives only. The frontend lead reviews this strictly per FRONTEND_ARCHITECTURE.md Layer 4 enforcement rule #1.
- **NO Angular Material imports** — Angular 21 + PrimeNG 21 + Tailwind 4 stack, NOT Material per FRONTEND_ARCHITECTURE.md Technology Decisions LOCKED.
- NO autofill UI work: no `AutofillButton`, no `FieldDiff`, no yellow-highlight overlay. Those are owned by `ai-autofill`. If a task drifts into autofill, flag it and stop.
- `CatalogFormComponent` MUST be `standalone: true` with `ChangeDetectionStrategy.OnPush` per CLAUDE.md Angular conventions.
- Forms MUST be reactive (`FormBuilder`, `FormGroup`) — NO template-driven forms.
- NO token reads from localStorage. Tokens are in-memory only per Decision 14 FE-D5 amendment.

## Files you MAY touch
- `frontend/src/app/features/catalog-form/catalog-form.component.ts` (NEW)
- `frontend/src/app/features/catalog-form/catalog-form.component.html` (NEW)
- `frontend/src/app/features/catalog-form/components/field-renderer/field-renderer.component.ts` (NEW)
- `frontend/src/app/features/catalog-form/components/field-renderer/field-renderer.component.html` (NEW)
- `frontend/src/app/features/catalog-form/directives/autosave.directive.ts` (NEW)
- `frontend/src/app/features/catalog-form/models/catalog-form.types.ts` (NEW)
- `frontend/src/app/features/catalog-form/catalog-form.component.spec.ts` (NEW)
- `frontend/src/app/features/catalog-form/components/field-renderer/field-renderer.component.spec.ts` (NEW)

## Files you must NOT touch
- `frontend/src/app/ui/**` (Layer 2 abstraction wall; if a `mee-*` primitive is missing for a primitive you need, escalate to frontend lead — do not add to `ui/`)
- `frontend/src/app/features/catalog-form/services/catalog.service.ts` (angular-service-builder)
- `frontend/src/app/features/catalog-form/catalog-form.component.scss` (angular-ui-styler)
- Any other feature directory
- `backend/**`

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session entry recording: the 11 primitives covered, the unknown-primitive throw behavior, the autosave debounce target (form-group `valueChanges` not field blur).
2. Update `MEMORY.md` index.

## Final report format
- PR URL (`feature/catalog-form/frontend` → `feature/catalog-form`)
- 11-primitive coverage test result (paste karma/jest output)
- 50-field first-paint timing (paste DevTools profile screenshot description)
- Files changed (absolute paths)
- Any deviation from FRONTEND_ARCHITECTURE.md Layer 4 rules (should be none — flag anything)
```

### Template 5 — `meesell-angular-service-builder`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-frontend-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Author `CatalogService` with `create`, `autosave`, `getDraft`, `softDelete`, `getPreview` methods. Wire HttpClient against the generated OpenAPI client. Implement offline queue with exponential backoff on reconnect. Register `/catalogs/:id/edit` route in `app.routes.ts` behind `featureFlagGuard`. Extend `feature-flags.service.ts` with `FEATURE_CATALOG_FORM_ENABLED`.

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-angular-service-builder/MEMORY.md`
2. `.claude/agent-memory/meesell-angular-service-builder/feature_catalog-form.md` (per O3; create if missing)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan)
4. The generated OpenAPI client (location per `frontend/openapi-codegen` config — read CLAUDE.md HttpClient conventions + the generated `ProductResponse` / `ProductDraftResponse` types)
5. `frontend/src/app/core/services/feature-flags.service.ts` current state
6. `frontend/src/app/core/interceptors/auth.interceptor.ts` (must not duplicate auth wiring — the interceptor handles JWT attach globally)
7. CLAUDE.md (HttpClient + `provideHttpClient(withInterceptors([...]))` pattern)
8. `docs/plans/repo_management/MASTER_PLAN.md` §3.2 (feature flag posture)

## Acceptance criteria
- `CatalogService.create(payload)` → `POST /api/v1/products` returning `ProductResponse`.
- `CatalogService.autosave(productId, fieldsPatch)` → `PATCH /api/v1/products/{id}` with **`X-Autosave: true` header** per §10.B.2.
- `CatalogService.getDraft(productId)` → `GET /api/v1/products/{id}/draft`. Returns `ProductDraftResponse | null` (null when backend returns 204).
- `CatalogService.softDelete(productId)` → `DELETE /api/v1/products/{id}` returning void on 204.
- `CatalogService.getPreview(productId)` → `GET /api/v1/products/{id}/preview` returning `ProductPreviewResponse`.
- **Offline queue**: autosave failures (network drop, 5xx) enqueue the patch to a Valkey-of-the-frontend (in-memory queue tied to `productId`). On `online` event, drain queue with **exponential backoff with jitter, capped at 30s** per Risk R2.
- **`featureFlagGuard`** on `/catalogs/:id/edit` route. When `FEATURE_CATALOG_FORM_ENABLED` is `false`, redirect to `/dashboard` with a toast "Feature unavailable".
- **`FEATURE_CATALOG_FORM_ENABLED`** added to `core/services/feature-flags.service.ts` runtime boolean (build-time env in V1 — read `environment.FEATURE_CATALOG_FORM_ENABLED`).
- **NO token in localStorage** per Decision 14 FE-D5 amendment. Access token is in-memory; refresh is in HttpOnly cookie.
- HttpClient uses the generated OpenAPI types — NO `any` typings on response shapes.
- Service is `providedIn: 'root'` standalone DI per CLAUDE.md.

## Hard constraints
- NO `Authorization` header manipulation in the service — the global `auth.interceptor.ts` handles JWT attach.
- NO direct PrimeNG imports.
- NO direct `HttpHeaders` mutation patterns from pre-19 Angular; use the `HttpContext` / inline headers pattern.
- Offline queue MUST NOT retry indefinitely — cap at 5 attempts then surface a "draft not saved" toast.
- `withCredentials: true` ONLY for `/api/v1/auth/*` calls (per Decision 14 FE-D5 amendment cookie Path=/api/v1/auth) — NOT for `/api/v1/products/*` calls.
- NO autofill service methods. `autofillProduct(...)` is owned by `ai-autofill`. Do not add a stub.

## Files you MAY touch
- `frontend/src/app/features/catalog-form/services/catalog.service.ts` (NEW)
- `frontend/src/app/features/catalog-form/services/catalog.service.spec.ts` (NEW)
- `frontend/src/app/features/catalog-form/guards/feature-flag.guard.ts` (NEW)
- `frontend/src/app/app.routes.ts` (MODIFY — register route)
- `frontend/src/app/core/services/feature-flags.service.ts` (MODIFY — add flag)
- `frontend/src/environments/environment.ts` + `.development.ts` + `.staging.ts` (MODIFY — set `FEATURE_CATALOG_FORM_ENABLED` per env per D2)

## Files you must NOT touch
- `frontend/src/app/features/catalog-form/catalog-form.component.ts` (angular-component-builder)
- `frontend/src/app/features/catalog-form/**.scss` (angular-ui-styler)
- `frontend/src/app/core/interceptors/*` (auth chain — owned by auth posture, not catalog-form)
- `backend/**`

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session entry recording: the 5 service method signatures, the autosave header (`X-Autosave: true`), the offline-queue backoff curve.
2. Update `MEMORY.md` index.

## Final report format
- PR URL (`feature/catalog-form/frontend` → `feature/catalog-form`)
- 5 service method signatures (paste from `catalog.service.ts`)
- Offline-queue test result under simulated network flap (paste jest output)
- Files changed (absolute paths)
- Any deviation from CLAUDE.md HttpClient conventions or Decision 14 FE-D5 amendment (should be none — flag anything)
```

### Template 6 — `meesell-angular-ui-styler`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-frontend-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Style the catalog-form: `mee-*` field-error / saved / advanced states with WCAG-AA contrast. Advanced-fields expander animation without layout shift. Autosave "Saved" indicator visible at 360px and 1280px breakpoints. Red-asterisk styling for compulsory fields.

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-angular-ui-styler/MEMORY.md`
2. `.claude/agent-memory/meesell-angular-ui-styler/feature_catalog-form.md` (per O3; create if missing)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan)
4. `docs/FRONTEND_ARCHITECTURE.md` Layer 1 (Design System: tokens, typography, motion, elevation) + Layer 2 (`mee-*` UI Kit — how component states are themed)
5. `frontend/src/app/design-system/_tokens.scss` + `_typography.scss` + `_motion.scss` + `_elevation.scss`
6. `frontend/tailwind.config.js` (Tailwind 4 config — extended with design-system tokens)
7. `frontend/src/app/features/catalog-form/catalog-form.component.html` and `field-renderer.component.html` after angular-component-builder ships them

## Acceptance criteria
- **Compulsory-field red-asterisk** matches the design-system tokens for `--color-danger`. Contrast ratio against the surface background meets WCAG-AA (≥4.5:1 for text).
- **Field error state** (red border + 4px outline + error message below) at WCAG-AA contrast. Uses `mee-input` error slot — no custom error markup.
- **Field saved state** (subtle green tick + "Saved" tooltip on hover) at WCAG-AA contrast. Animates in within 200ms per `_motion.scss` standard.
- **Field advanced state** (grey expander chevron + softer field background) using design-system surface-secondary token.
- **Advanced-fields expander animation**: expand/collapse without layout shift on the 50-field schema. Use CSS `grid-template-rows: 0fr / 1fr` pattern (or equivalent) — NOT `display: none` toggles.
- **Autosave "Saved" indicator** (small badge top-right of the form) visible at 360px (mobile) and 1280px (desktop) breakpoints. Animates from "Saving…" → "Saved" → fades after 1.5s. NO layout shift on transitions.
- All styles in `.scss` files alongside their components. NO inline `[ngStyle]` or `style="..."`. NO `!important` overrides.

## Hard constraints
- NO new tokens added to `design-system/_tokens.scss`. Use existing tokens only. If a token is missing (e.g., a new shade of green), escalate to frontend lead — do not invent.
- NO direct PrimeNG class overrides (e.g., `.p-button { ... }` is forbidden). Theme via the `mee-*` host component's documented CSS variable surface.
- NO Tailwind arbitrary values for tokens that exist in the design system. E.g., use `text-danger`, NOT `text-[#dc2626]`.
- NO touch to `.ts` or `.html` files (those are angular-component-builder).

## Files you MAY touch
- `frontend/src/app/features/catalog-form/catalog-form.component.scss` (NEW)
- `frontend/src/app/features/catalog-form/components/field-renderer/field-renderer.component.scss` (NEW)

## Files you must NOT touch
- `.ts` files in `features/catalog-form/`
- `.html` files in `features/catalog-form/`
- `frontend/src/app/design-system/**` (Layer 1 governance)
- `frontend/src/app/ui/**` (Layer 2 governance)
- `frontend/tailwind.config.js`
- `backend/**`

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session entry recording: the design-system tokens used (compulsory-asterisk, error, saved, advanced), the expander animation technique (grid-rows pattern), the "Saved" badge breakpoint behavior.
2. Update `MEMORY.md` index.

## Final report format
- PR URL (`feature/catalog-form/frontend` → `feature/catalog-form`)
- Contrast test results (paste axe / Lighthouse output for each state)
- Layout-shift CLS measurement on Advanced expand/collapse (paste DevTools Performance)
- Screenshots at 360px and 1280px showing the "Saved" indicator
- Files changed (absolute paths)
- Any deviation from FRONTEND_ARCHITECTURE.md Layer 1 / Layer 2 rules (should be none — flag anything)
```

### Template 7 — `meesell-xlsx-parser` (CONDITIONAL)

This template **only dispatches** if the `help_text` sweep returns gaps. The data lead runs the sweep before authoring.

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.

SESSION: mesell-catalog-form-data-session-{N}
Working on feature: catalog-form. Memo file: feature_catalog-form.md.

## Your mission
Extend `backend/app/data/field_aliases.json` with missing `help_text` entries for any category referenced by the smart-picker shipped surface. Sweep precondition: verify each `fields[].canonical_name` in every shipped category schema has a `help_text` row before adding.

DISPATCHED ONLY IF the data lead's pre-sweep returned gaps. If the sweep returned NO gaps, this template is NOT dispatched and the catalog-form feature ships without a data-track contribution.

## Mandatory reads (in this order)
1. `.claude/agent-memory/meesell-xlsx-parser/MEMORY.md`
2. `.claude/agent-memory/meesell-xlsx-parser/feature_catalog-form.md` (per O3; create if missing)
3. `docs/plans/features/catalog-form/FEATURE_PLAN.md` (this plan)
4. `backend/app/data/field_aliases.json` current schema + version field
5. `docs/V1_FEATURE_SPEC.md` §F3 (the help_text UX requirement: "Inline help text from XLSX")
6. The smart-picker shipped categories list (read the smart-picker feature's per-feature memo: `.claude/agent-memory/meesell-data-engineer/feature_smart-picker.md`)
7. The XLSX template parser current state (`backend/scripts/parse_xlsx_template.py` or equivalent)

## Acceptance criteria
- Every `fields[].canonical_name` in every smart-picker-shipped category schema has a corresponding `help_text` row in `field_aliases.json`.
- `field_aliases.json` schema version bumped by 1 (e.g., `v3` → `v4`).
- The sweep delta is recorded in the PR body: which categories had gaps, which canonical_names received new help_text rows.
- Data lead `MEMORY.md` records the version bump.
- No existing `help_text` rows modified — append-only.

## Hard constraints
- NO modification to existing rows. Append-only sweep.
- NO modification of any `canonical_name` value — only `help_text` entries are added.
- NO change to the XLSX template parser logic — this is a data-only patch.
- Help text MUST be the verbatim XLSX-sourced text. NO paraphrasing.
- NO touch to any other JSON file in `backend/app/data/`.

## Files you MAY touch
- `backend/app/data/field_aliases.json` (MODIFY — append-only)

## Files you must NOT touch
- Any code file
- Any other data file
- Any test file
- `backend/**` outside `app/data/field_aliases.json`
- `frontend/**`

## Per-feature memory protocol
1. Open `feature_catalog-form.md` with a session entry recording: which categories had gaps, the version bump, the row count added.
2. Update `MEMORY.md` index.

## Final report format
- PR URL (`feature/catalog-form/data` → `feature/catalog-form`)
- Sweep delta (paste a list of added canonical_names by category)
- Schema version before / after
- Files changed (absolute paths)
- Any deviation from append-only constraint (should be none — flag anything)
```

---

## Review + iteration protocol

For each specialist, the lead reviews the PR against the master plan §5.2 backend PR template (frontend / data have their own templates but the same lifecycle applies). The acceptance gate is locked; the failure modes that trigger a re-dispatch are enumerated below with concrete re-dispatch language.

### `meesell-database-builder` review

**Backend lead checks (must pass to approve):**
- Migration is reversible: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` produces no row loss on the seed-data fixture (evidence pasted in Migration evidence section of the PR per master plan §5.2).
- Migration parent revision matches `develop` head at PR-open time. **`alembic heads` on dev AND staging shows convergence** before merge — if staging has diverged, refuse the PR, escalate to infra lead via memo per master plan §7.5.
- `product_drafts.UNIQUE (user_id, product_id)` present per `MVP_ARCH §11.6`.
- All new indexes specified in Template 1 are present.
- 11 unit tests in `test_database.py` green.

**Failure modes → re-dispatch language:**
- **Migration not reversible** (downgrade leaves orphaned rows or constraints): "Previous run failed: downgrade leaked `product_drafts` rows or left a stale UNIQUE constraint. Fix by re-implementing `downgrade()` to DROP in dependency-correct order (constraints → indexes → table → columns). Read `MVP_ARCH §2.6` migration ordering before re-authoring."
- **Migration head divergence** (dev head ≠ staging head after PR-open): "Previous run failed: alembic heads diverged between dev and staging at merge time. STOP. Coordinate with infra lead via memo to converge staging to dev's head BEFORE rebasing the migration; do NOT force-merge."
- **`UNIQUE (user_id, product_id)` missing** on `product_drafts`: "Previous run failed: product_drafts schema permits duplicate (user_id, product_id) rows; `MVP_ARCH §11.6` requires UNIQUE. Fix by adding the constraint at create-table time, NOT as a separate index."

### `meesell-api-routes-builder` review

**Backend lead checks:**
- 5 routes match §10.B.1 / .2 / .4 / .5 / .6 verbatim for request/response/status-codes/rate-limit decorators.
- **`PATCH /products/{id}` rate limit is per-IP, NOT per-user** per §10.B.2.
- `POST /products/{id}/autofill` is NOT present (per D1).
- OpenAPI regenerated; `/openapi.json` shapes match the FieldRendererComponent's expected schema.
- 5 Pydantic schemas use Pydantic v2 syntax (`model_config = ConfigDict(...)`, NOT `class Config:`).

**Failure modes → re-dispatch language:**
- **Autosave PATCH uses per-user rate limit**: "Previous run failed: PATCH /products/{id} has `key='user_id'` on the rate-limit decorator; §10.B.2 requires `key='ip'`. Per-user would degrade autosave UX. Fix by changing to per-IP."
- **Autofill route accidentally added**: "Previous run failed: `POST /products/{id}/autofill` route present. Per D1, autofill is owned by ai-autofill feature. Remove the route, the request schema, the response schema, and any service signature stubs. Re-read FEATURE_PLAN.md §1 D1."
- **OpenAPI shape mismatch**: "Previous run failed: regenerated /openapi.json shows `ProductResponse.fields_jsonb` as `dict[str, str]` but §10.E specifies `dict[str, Any]`. Fix Pydantic v2 schema to use `Any` value type."

### `meesell-services-builder` review

**Backend lead checks:**
- 9 of 10 method signatures from §10.C match verbatim (`autofill_product` skipped per D1).
- `assert_product_ownership(product_id: UUID, user_id: UUID) -> None` signature matches §10.C exactly. **This is the contract; verify byte-for-byte.**
- Autosave coalescing helper passes 5-min window test in `test_audit_coalescing.py`.
- Cross-tenant `assert_product_ownership` leak test passes (user B cannot read user A's product).
- Concurrent-edit race test passes (two tabs PATCHing within 100ms → last-write-wins on JSONB-merge, both writes captured in `product_drafts.autosave_count`).
- `FEATURE_CATALOG_FORM_ENABLED` flag in `app/main.py` returns 404 when disabled.
- All repository methods use `core.tenancy.scope_to_user(user_id)` per §4.C — `tests/lint/import_rules.toml` audit clean.

**Failure modes → re-dispatch language:**
- **`assert_product_ownership` signature drift**: "Previous run failed: signature is `async def assert_product_ownership(self, product_id, user_id)` but §10.C is `async def assert_product_ownership(product_id: UUID, user_id: UUID) -> None`. This is the cross-module contract; image / pricing / dashboard / export will fail to import. Fix verbatim per §10.A + §10.C."
- **Draft recovery returns stale `fields_jsonb`**: "Previous run failed: `GET /products/{id}/draft` returns `products.fields_jsonb` instead of the most-recent `product_drafts.fields_snapshot`. The whole point of `product_drafts` is to capture autosaves that haven't been committed to `products`. Fix by reading from `product_drafts`, NOT `products`. Re-read §10.B.6."
- **Change-category leaves orphaned fields**: "Previous run failed: when category_id changes mid-edit, the old `fields_jsonb` keys persist. V1 behavior per D1 is to RESET `fields_jsonb`. Fix `patch_product` to atomically clear `fields_jsonb` in the same transaction when `request.category_id != product.category_id`."
- **Cross-tenant leak**: "Previous run failed: `assert_product_ownership` returned a product even when `deleted_at IS NOT NULL` for the requesting user. Fix the repository query to scope `deleted_at IS NULL AND user_id = :uid`."
- **Coalescing window math wrong**: "Previous run failed: 5-min window test produced 2 audit_events rows for 3 PATCHes within 4 minutes. Per `MVP_ARCH §11.4`, only the FIRST PATCH writes a new row; subsequent same-window PATCHes update `payload_jsonb.coalesced_count`. Fix the Valkey window key TTL and the UPSERT pattern."

### `meesell-angular-component-builder` review

**Frontend lead checks:**
- 11-primitive coverage test passes; unknown-primitive throws a typed error (NOT silent skip).
- 50-field first-paint <500ms (DevTools Profile screenshot in PR).
- Compulsory-field validator blocks `status=ready` with `validation_message_id="validation.completeness.missing_compulsory"`.
- `AutosaveDirective` debounces on form-group `valueChanges`, not individual field blur.
- Change-category dialog uses explicit "Discard fields and switch category" button — no default-confirm.
- NO PrimeNG imports outside `src/app/ui/`.
- NO autofill UI files added.

**Failure modes → re-dispatch language:**
- **Autosave fires more than once per debounce window**: "Previous run failed: AutosaveDirective debounce is on individual field `blur`, causing multiple fires per 10s window. Fix by moving the debounce to `formGroup.valueChanges.pipe(debounceTime(10000))`. Re-read Acceptance Criteria item 5 in the dispatch template."
- **FieldRenderer fails on a primitive**: "Previous run failed: FieldRendererComponent throws on `text_long` because the case branch is missing. Add the missing branch; cite `BACKEND_ARCHITECTURE.md §5A.D` row for `text_long` in your fix commit message."
- **Unknown-primitive silent skip**: "Previous run failed: FieldRendererComponent returns null on unknown primitives, masking V1.5 schema additions. Fix by `throw new UnknownPrimitiveError(primitive)` — this matches Risk R4 mitigation."
- **PrimeNG import leak**: "Previous run failed: `import { ButtonModule } from 'primeng/button'` found in `catalog-form.component.ts`. Layer 4 rule #1 forbids this. Replace with `mee-button` from `@mee/ui`."
- **Change-category default-confirm**: "Previous run failed: change-category dialog uses a default-confirm button labeled 'OK'. Per Risk R3, the confirm MUST be explicit: 'Discard fields and switch category'. Fix the dialog config."

### `meesell-angular-service-builder` review

**Frontend lead checks:**
- 5 service method signatures match the dispatch template.
- `autosave` sends `X-Autosave: true` header per §10.B.2.
- `getDraft` returns null on backend 204 (no draft).
- Offline queue retries with exponential backoff with jitter, capped at 30s, max 5 attempts.
- `featureFlagGuard` redirects to `/dashboard` when disabled.
- NO localStorage token writes (per Decision 14 FE-D5 amendment).

**Failure modes → re-dispatch language:**
- **Offline queue retries indefinitely**: "Previous run failed: simulated network flap produced 100+ retries within 60s. Per acceptance, cap at 5 attempts. Fix the queue's max-attempts counter."
- **Missing `X-Autosave` header**: "Previous run failed: PATCH calls do not include `X-Autosave: true`. Backend §10.B.2 reads this header to decide whether to upsert `product_drafts`. Fix by adding the header in `autosave()` only (not in manual save)."
- **Token in localStorage**: "Previous run failed: `localStorage.setItem('access_token', ...)` found. Decision 14 FE-D5 amendment forbids this — access token is in-memory only. Fix by storing in the AuthService signal/BehaviorSubject."

### `meesell-angular-ui-styler` review

**Frontend lead checks:**
- WCAG-AA contrast on field error / saved / advanced states (axe report green).
- Advanced expander animates with CLS ≤ 0.05.
- "Saved" indicator visible at 360px and 1280px.
- NO new tokens in `design-system/_tokens.scss`.
- NO `!important` overrides.

**Failure modes → re-dispatch language:**
- **WCAG-AA fail on error state**: "Previous run failed: axe reports contrast 3.8:1 on field-error text. Fix by using `--color-danger-dark` token instead of `--color-danger` (already defined). NO new tokens."
- **Layout shift on expander**: "Previous run failed: CLS 0.22 on Advanced expand. Replace `display: none ↔ display: block` with the grid-rows `0fr ↔ 1fr` pattern."
- **New token added**: "Previous run failed: `design-system/_tokens.scss` shows a new `--color-saved-tick` variable. Layer 1 is sole-writer (governance). Revert and use the existing `--color-success` token; if shade is wrong, escalate to frontend lead via memo."

### `meesell-xlsx-parser` review (conditional)

**Data lead checks:**
- Append-only patch — no existing `help_text` rows modified.
- Every smart-picker-shipped category covered.
- Schema version bumped by exactly 1.
- Help text is verbatim XLSX source — no paraphrasing.

**Failure modes → re-dispatch language:**
- **Existing rows modified**: "Previous run failed: diff shows modifications to existing `help_text` entries. Append-only. Revert the existing rows; re-add only the gap rows."
- **Paraphrased help text**: "Previous run failed: help text 'Color of the product' does not match XLSX source 'Primary color shade'. Use the verbatim source per the dispatch template."

### Maximum iteration count + escalation

**Maximum 3 re-dispatches per specialist** before escalating to founder via `STATUS_BACKEND.md` blockers section + a `BLOCKED` flag on `feature_board_backend.md`. The 48-hour SLA from master plan §7.5 applies. If a specialist hits 3 re-dispatches, the lead opens a memo at `.claude/agent-memory/meesell-{lead}/handoff_catalog-form_blocker.md` describing the failure shape and proposed founder intervention.

---

## Acceptance gate

The catalog-form feature is "done" when **ALL** of the following are true:

### V1_FEATURE_SPEC.md §F3 acceptance criteria (verbatim from spec lines 145-150)

- [ ] **§F3.AC1** — Form renders ≤50 fields without lag (<500 ms first paint after schema fetch)
- [ ] **§F3.AC2** — Every field shows the XLSX help text on hover/tap
- [ ] **§F3.AC3** — Compulsory fields marked with red asterisk; form cannot proceed if any blank
- [ ] **§F3.AC4** — Autosave writes to `products.fields_jsonb` and shows "Saved" indicator
- [ ] **§F3.AC5** — Browser reload resumes from last saved state

### Specialist PR completion

- [ ] All 6 specialists' PRs merged to `feature/catalog-form` (3 backend: database-builder, api-routes-builder, services-builder; 3 frontend: angular-component-builder, angular-service-builder, angular-ui-styler; data: xlsx-parser conditional — only if `help_text` sweep returns gaps).

### Integration tests green on `feature/catalog-form`

- [ ] Command: `cd backend && pytest tests/test_catalog_form_integration.py -v` returns 3/3 green:
  - `TestFullProductLifecycle` (create → autosave 3× → preview → mark ready → soft-delete)
  - `TestDraftRecoveryAfterSimulatedClose` (autosave 2× → kill connection → reopen → GET /draft returns latest)
  - `TestCrossModuleOwnershipAssertion` (user A creates; user B 404s on every endpoint)
- [ ] Frontend spec command: `cd frontend && ng test --include='**/catalog-form/**'` returns green including 11-primitive renderer coverage + unknown-primitive throw assertion.

### Feature-flag staging soak criteria (from D2)

- [ ] (a) Autosave network-flap test passes on staging.
- [ ] (b) Draft-recovery test passes on browser-reload simulation.
- [ ] (c) Cross-tenant `assert_product_ownership` leak test passes (user A → user B receives 404).
- [ ] (d) Concurrent-edit race test passes (two tabs PATCHing same product within 100ms; last-write-wins on JSONB merge; both writes captured in `product_drafts.autosave_count`).
- [ ] (e) 48-hour dev soak with no P0/P1 alerts before flipping `FEATURE_CATALOG_FORM_ENABLED=true` on staging.

### CI gates (per master plan §2.1)

- [ ] CI gate 1 (unit tests) green on `feature/catalog-form`.
- [ ] CI gate 2 (smoke tests) green on `feature/catalog-form`.
- [ ] CI gate 3 (lint — ruff + ESLint + `tests/lint/import_rules.toml` audit) green on `feature/catalog-form`.
- [ ] CI gate 4 (integration tests — advisory but reviewed) green on `feature/catalog-form`.
- [ ] CI gate 5 (golden_roundtrip — advisory but reviewed) green on `feature/catalog-form`.

### Documentation deliverables (cross-reference §4)

- [ ] OpenAPI regenerated; `/openapi.json` reviewed by backend lead; includes the 5 mounted catalog routes per §10.B.1 / .2 / .4 / .5 / .6.
- [ ] V1_FEATURE_SPEC.md §F3 stamped `implemented YYYY-MM-DD` with PR link.
- [ ] BACKEND_ARCHITECTURE.md §10 sentinel flipped from `spec` to `implemented YYYY-MM-DD with PR #<num>` (append-only).
- [ ] Cross-module signature docstrings on the 4 PUBLIC methods of `app/modules/catalog/service.py` per §16.A consumer-reference convention.
- [ ] `tests/lint/import_rules.toml` entries added for the 4 new cross-module call sites (image, pricing, dashboard, export).
- [ ] `docs/MVP_ARCHITECTURE.md §11.4` cross-link to the merged `catalog.service.patch_product` coalescing helper implementation.
- [ ] `docs/status/STATUS_BACKEND.md` Updates Log entry with PR URL.

### Status board + memory hygiene

- [ ] `feature_board_backend.md`, `feature_board_frontend.md`, and (if data fired) `feature_board_data.md` all show MERGED for catalog-form with PR links in Notes.
- [ ] Each agent's `feature_catalog-form.md` memo updated with session-close learnings per O3.

### Founder merge gate

- [ ] PR `feature/catalog-form` → `develop` opened by backend lead, approved by founder, merged (per master plan §6 reviewer rule).

---

## Risk register

Top 5 risks specific to catalog-form, plus one bonus (R6) governance caveat. Summary table follows the canonical pattern v2 shape; the per-risk `### R{N}` subsections below give the full rationale.

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Migration head divergence between dev and staging blocks merge to `develop` | Medium | High (P0 — blocks merge) | Backend lead requires services-builder to run `alembic heads` against BOTH dev AND staging clones before authoring; on divergence open memo to infra lead per master plan §7.5; converge staging → dev (NEVER reverse). Rebase migration before opening PR. See `MVP_ARCH §2.6`. |
| R2 | Autosave hammers Postgres under network-flap retry storms after reconnect burst | Medium | Medium (P1 — pool saturation at scale) | Frontend exponential backoff with jitter, cap 30s, max 5 attempts; backend per-IP rate limit 600/h on PATCH per §10.B.2; 5-min audit coalescing per `MVP_ARCH §11.4` bounds audit_events writes. |
| R3 | Change-category UX loses seller fields_jsonb data on accidental default-confirm | Medium | High (P1 — user-trust risk) | Confirm button MUST be labeled "Discard fields and switch category" (explicit, no default-confirm); component-builder dispatch template enforces this. One-time snapshot to `product_drafts` BEFORE reset gives 5-min support recovery window. |
| R4 | FieldRendererComponent fails silently on unmapped primitive in V1.5 category additions | Low | Medium (P2 — V1.5 risk) | `FieldRendererComponent` MUST `throw new UnknownPrimitiveError(primitive)` on unknown primitives (NEVER silent skip); spec test covers all 11 V1 primitives PLUS the unknown-primitive throw case. §5A.D amendment is the V1.5 unblock path. |
| R5 | Downstream sibling features race the catalog-form merge and lock conflicting `assert_product_ownership` signatures | High | High (P1 — cross-feature contract drift) | Backend lead publishes the locked `assert_product_ownership` signature in `feature_board_backend.md` Notes column AS SOON AS services-builder PR opens; sibling-feature planners cite the locked form; lead reviews every sibling services-builder template before approving. §10.A + §10.C cited verbatim in dispatch templates. |
| R6 | `feature/catalog-form/planning` group token "planning" violates master plan §1.2 taxonomy `{backend, frontend, ai, data, infra}` | High (already occurred) | Low (P3 — governance debt) | Flag as candidate for §1.2 amendment after this plan ships (add `planning` + `docs` as 6th/7th tokens); OR future features use `docs-only` PRs to `docs/<feature>/planning` branch without group-style suffix. Founder rules on standardization. |

### R1 — Migration head divergence between dev and staging

**Risk:** The catalog migration's parent revision must be the same on dev and staging. If staging has drifted (e.g., a hotfix migration applied to staging but not dev), the catalog migration cannot apply cleanly.

**Severity:** P0 — blocks merge to `develop` until resolved.

**Mitigation:**
- Backend lead requires services-builder to run `alembic heads` against **both dev AND staging clones** before authoring the migration.
- If divergence detected, the lead opens a memo to infra lead via the §7.5 protocol; resolution is to converge staging to dev's head (NEVER the reverse — dev must lead per master plan §1.2).
- Rebase the catalog migration against the converged head immediately before opening the PR.

### R2 — Autosave hammering Postgres under network-flap retry storms

**Risk:** The frontend offline queue retries aggressively after reconnect. If a seller's tab spent 2 minutes offline, the queue could send 12 autosaves in a burst.

**Severity:** P1 — Postgres connection pool saturation possible at scale.

**Mitigation:**
- Frontend: exponential backoff with jitter on the autosave retry, **capped at 30s**, **max 5 attempts**.
- Backend: per-IP rate limit on PATCH at **600/h** per §10.B.2 acts as a structural safety net.
- The 5-min audit coalescing per `MVP_ARCH §11.4` keeps `audit_events` write volume bounded even under burst.

### R3 — Change-category UX loses seller data

**Risk:** V1 behavior is to RESET `fields_jsonb` on category change. If the seller dismisses the warning by accident (a default-confirm dialog), they lose 50 fields of work.

**Severity:** P1 — user-trust risk.

**Mitigation:**
- The warning dialog confirm button MUST be labeled **"Discard fields and switch category"** (explicit). NO default-confirm. The component-builder dispatch template enforces this.
- **One-time snapshot** to `product_drafts` BEFORE resetting `fields_jsonb` — gives the seller a 5-min window to recover by clicking "Undo category change" (V1.5 backlog item; for V1 the snapshot is silent insurance for support cases).

### R4 — FieldRendererComponent fails on unmapped primitive in V1.5 category additions

**Risk:** V1.5 schema seed could add a 12th primitive (e.g., `currency`, `phone_e164`, `gtin14`) without a `BACKEND_ARCHITECTURE.md §5A.D` amendment first. A silently-skipped unknown primitive in the renderer would render a blank cell — seller never notices, ships an invalid product.

**Severity:** P2 — V1.5 risk; V1 ships with 11 primitives covered.

**Mitigation:**
- `FieldRendererComponent` MUST **throw a typed error** (`UnknownPrimitiveError`) on unknown primitives. NEVER silent skip.
- A unit test in `field-renderer.component.spec.ts` covers all 11 V1 primitives **plus** an unknown-primitive case that asserts the throw.
- §5A.D amendment is the V1.5 unblock path; the schema-seed PR must include the §5A.D amendment for the new primitive.

### R5 — Downstream sibling features race the catalog-form merge

**Risk:** `ai-autofill`, `image-precheck`, `live-preview`, `xlsx-export` all consume `assert_product_ownership`. If their planning sessions advance in parallel, they may lock conflicting signatures (e.g., one assumes `user_id: UUID`, another assumes `user_id: str`).

**Severity:** P1 — cross-feature contract drift.

**Mitigation:**
- **Backend lead publishes the locked `assert_product_ownership` signature in the `feature_board_backend.md` Notes column AS SOON AS the services-builder PR opens** — well before merge. Sibling-feature planners cite this locked form in their own FEATURE_PLAN.md.
- The dispatch templates in §9 of this plan cite §10.A + §10.C verbatim and forbid signature variation.
- The lead reviews every sibling feature's services-builder template before approving — looking for `assert_product_ownership` mentions that drift.

### R6 — "planning" group token violates master plan §1.2

**Risk:** `feature/catalog-form/planning` uses `planning` as a 6th pseudo-group, but master plan §1.2 locks the taxonomy at `{backend, frontend, ai, data, infra}`. This sets a precedent that may dilute the §1.2 guarantees.

**Severity:** P3 — governance debt, not a blocker.

**Mitigation:**
- Flag as candidate for a master plan §1.2 amendment after this plan ships. The amendment would add `planning` (and `docs`) as a legitimate 6th and 7th group token.
- Alternative for future features: use `docs-only` PRs to a `docs/<feature>/planning` branch off `develop` without a group-style branch name. The founder rules on which path to standardize.

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 (v1) | 2026-06-10 | meesell-backend-coordinator (planning-session-1/2) | Initial DRAFT authored. 6 founder-locked decisions (D1/D2/D3 scope + O1/O2/O3 operational). 7 dispatch templates (3 backend + 3 frontend + 1 conditional data). Awaiting founder review. |
| v2 | 2026-06-10 | mesell-catalog-form-amendment-session-1 | Pattern v2 conformance — heading normalization (`Branch creation playbook` → `Branch setup`, `Per-feature memory protocol` → `Memory protocol`); ad-hoc `Why this feature plan exists` relocated to preamble paragraphs (content preserved verbatim with cross-references updated §9→§7, §10→§8, §12→§10); Risk register restructured to canonical summary table (R1-R6 details preserved as `### R{N}` subsections below the table); Acceptance gate expanded with V1_FEATURE_SPEC.md §F3.AC1-AC5 verbatim bullets, integration-test command, frontend spec command, and explicit CI gate 1-5 + documentation deliverable rollup. 11 sections in canonical order; no content removed. |
