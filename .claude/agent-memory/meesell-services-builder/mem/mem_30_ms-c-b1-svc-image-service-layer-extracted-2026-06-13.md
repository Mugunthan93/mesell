## MS-C B1 — svc-image service layer EXTRACTED (2026-06-13)

### Scope
HYBRID Phase-2 B1 (HEAVY-LIFT). Built `backend/services/svc-image/` (52 files) on branch
`feature/microservices-image/svc` (worktree `/tmp/mesell-wt/msC-svc`, cut from
`feature/microservices-image/integration` @ 3dc0f91). PR #204 → integration (LEAD squash gate, NOT merged).
Authority: `spec_msC_backend_EXECUTION.md` §1 B1 + `recipe_ms_extraction.md` (svc-export template).

### Reusable extraction recipe (copy for MS-D pricing / MS-E customer / etc.)
- **Scaffold by cloning svc-export's `app/` tree**, then surgically replace the module-specific files
  (service/tasks/repository/domain/exceptions/schemas/models/extracted_clients/ai_ops/requirements). The
  vendored `core/*` + `shared/{database,valkey}` + middleware + i18n/resolver are ~identical across services
  — copy verbatim, fix only docstrings + the trimmed bits (config fields, metrics, messages_en IDs).
- **§16.G AST-parity check** (the gate the lead re-runs): parse both twins, strip module docstring (first
  string-Expr) + ALL Import/ImportFrom nodes RECURSIVELY via `ast.NodeTransformer` (visit_Import/visit_ImportFrom
  → None — top-level-only strip FALSE-FAILS on lazy in-body imports), compare `ast.dump`. PASS = byte-identical
  executable. My service.py + tasks.py both PASS.
- **Harness gotcha**: `cp -R` scaffolded files must be Read before Edit/Write (harness "File has not been read"
  error). Easiest: Write the whole file fresh after a 2-line Read to satisfy the gate.

### Image-specific decisions
- **Option-B repository (§16.G EXEMPT, founder-RULED d4aa572/PR#197)**: repository.py is the ONE file whose
  BODIES change. Removed `scope_to_user` + `Product as ProductORM` imports + `_owned_product_ids_subquery`; every
  method scopes by `product_id`/`image_id` DIRECT (no products join, no read-grant). Tenancy = upstream
  `assert_product_ownership` HTTP shim. Worker path (`update_precheck_result`) scopes by `image_id` alone — SAFE
  (payload validated at enqueue + task_prerun JWT re-val); documented in code comment for the reviewer. AST scan
  confirmed ZERO live scope_to_user/ProductORM/products refs (docstring-only mentions OK).
- **ORM `product_image.py`** → schema `image` (table `image.product_images`), products FK + relationship DROPPED.
- **ai_ops VENDORED whole-package** (client/cost_tracker/guardrail/budget_cap/prompt_registry/eval + watermark_v1
  prompt) + gemini + langfuse adapters. prompt_registry resolves via `importlib` LAZILY → trimming
  autofill_v1/smart_picker_v1 prompts is SAFE (only docstring refs remain). **Budget brake keyspace
  `ai:cost:daily`/`ai:cost:pending`/`ai:budget:reservation` is UN-prefixed + SHARED on Valkey DB 0** (via
  `get_valkey_otp` = `_make_client(0)`) — global ₹500/day cap per D6, do NOT namespace. Only the Celery broker
  (DB1) + results (DB2) keys get the `svc-image:` prefix.
- **`core/metrics` must re-add** `AI_OPS_BUDGET_ALARM` (budget_cap) + `AI_OPS_COST_INR` (cost_tracker) vs the
  export-trimmed version — ai_ops imports them at module load. `adapters/__init__` must re-add `GeminiAdapterError`
  (gemini adapter imports it) + `LangfuseAdapterError`.
- **Celery `task_prerun` JWT re-validation handler**: svc-export did NOT carry it; image's spec §1.G REQUIRES it.
  Carried scoped to `image.precheck` only (existence check vs public.users via make_worker_session NullPool;
  Reject(requeue=False) on miss; fail-open on DB error).
- **Router import path** (NOT pinned by spec): used svc-export precedent `from app.router import router as
  image_router` in main.py. B2 (api-routes-builder) owns router.py; flagged for lead verification.
- **rembg DEFERRED** — declared in monolith requirements, zero call sites; NOT carried into svc-image (cheapest
  D3 VM-fit mitigation).

### Validation posture in the sandbox worktree
- ruff at `/opt/homebrew/bin/ruff` (NOT in a venv); NO `backend/.venv` in this worktree; system py = 3.9 (can't run
  pydantic-v2 / `str|None` runtime / schema-qualified PG). So: ruff + AST-parity + py_compile (parse) + an
  import-graph resolver scan (all app.* imports resolve within the tree, only app.router B2-owned unresolved). The
  actual unit-test run + cross-schema PG round-trip are Phase-C (lead `test_image_extraction.py`).
- git: stage EXACT paths (`git add backend/services/svc-image/ docs/status/STATUS_BACKEND.md`) — never `-A`.
  F3 protection via `gh api -X PUT .../protection --input -` with a PROPER JSON body (`-f field=null` sends the
  STRING "null" and fails — use `--input -` with real JSON null).

### Hand-offs queued
- B2 (api-routes-builder): build router.py (2 public + /internal list-images); schemas.py already vendored;
  ImageSummary field names = FROZEN §2.6 5 keys + additive extras (do not rename the 5).
- LEAD: §16.G CI parity (service.py+tasks.py, EXEMPT repository.py) + Option-B no-products-read assertion +
  ai_ops DB-0 budget coherence + cross-schema audit round-trip + /internal shim JWT-forward parity; merge-gate.
- infra(A2)+db(A1): SOLE cross-schema grant = GRANT INSERT ON public.audit_events TO image_user (NO products SELECT).

---
