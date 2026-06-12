# RECIPE — Microservices Module Extraction (validated SP01 pilot, copy for MS-2..5)

**Status:** VALIDATED 2026-06-12 by Sub-Plan A (`export`) end-to-end. This is the proven step sequence; waves B–H copy it with the per-wave variation points in §7.
**Author:** meesell-backend-coordinator. **Authority:** `spec_msA_backend.md`, `SUB_PLAN_01_export_extraction.md`, `BACKEND_ARCHITECTURE.md §16.G/§16.H`, `MASTER_PLAN.md §2/§3`.

---

## 1. The proven step sequence

```
0. Re-verify GROUND TRUTH against the LIVE tree, not the plan text.
   (The plan was authored against an older develop. SP01 found 2 mis-named
   shims + a stale test-count baseline + a diverged local develop. ALWAYS
   re-cite call sites file:line from source; correct the plan in the spec.)

1. Branch cut + F3 protection
   git fetch origin
   git checkout -b feature/microservices-<mod>/integration origin/develop   # NOT local develop
   # cut backend + infra branches FROM integration
   # apply F3 (PR-only, review-count 0, checks=[], no force-push, enforce_admins false)

2. PHASE A (parallel, no inter-dependency):
   - database-builder: standalone Alembic chain, ALTER TABLE … SET SCHEMA <mod>,
     version_table_schema="<mod>", Risk#5 orphan pre-scan, TESTED downgrade.
     dev applied BEFORE staging — NEVER reverse (head divergence = P0).
   - infra lane (handoff memo, NOT a backend specialist): Dockerfile, k8s,
     Traefik, Postgres schema/role + cross-schema audit grant, GCS SA, secrets,
     MS-DB-3 pool right-size + max_connections=200.

3. PHASE B (depends on A):
   - services-builder (heavy lift): vendor service.py/tasks.py/repository.py/
     domain.py/exceptions.py BYTE-FOR-BYTE; rewrite ONLY import lines; build the
     HTTP shims under core/extracted_clients/; trimmed Settings; single-task
     Celery app (queue <mod>, DB1/DB2, <mod>: prefix); standalone main.py.
   - api-routes-builder (once service signatures frozen — near-parallel):
     move router.py + schemas.py; regenerate OpenAPI; count MOUNTED APIRoutes.

4. PHASE C (LEAD-owned, this recipe's author):
   - hybrid-mode integration test (§16.G AST parity + wire-shape JSON-schema
     parity + shim JWT-forward/real-deserialize + cross-schema audit round-trip)
   - frozen shim-contract doc (program-level — callee sub-plans consume it)
   - CI hybrid-mode note + rollback runbook + MASTER_PLAN §4 row flip
   - board + STATUS + recipe append
   - merge-gate review (SEPARATE dispatch — do NOT pre-approve in the build dispatch)

5. GATES: group → integration (LEAD squash) → develop (FOUNDER merge-commit).
   I do NOT approve integration → develop (D1).
```

## 2. The §16.G diff-proof method (difflib/AST classifier) — VALIDATED

Do NOT trust the services-builder's one-time diff report. Re-prove it in CI on every run:
- Parse BOTH `service.py` twins with `ast`.
- Strip (a) the module docstring (first `Expr`/`Constant`/`str` node) and (b) ALL `Import`/`ImportFrom` nodes **recursively** — use an `ast.NodeTransformer` (`visit_Import`/`visit_ImportFrom` → `None`), NOT just a top-level filter. **GOTCHA:** the export pipeline has LAZY imports inside function bodies (`app.tasks`, `app.domain`, category-client exceptions) — a top-level-only strip leaves these and the parity test fails on a false positive. The recursive transformer is mandatory.
- Compare `ast.dump(...)` of the stripped trees. Identical dump ⇒ zero executable-line drift. SP01: PASSED (23 top-level nodes, byte-identical after recursive strip).

## 3. Wire-shape parity — use model_json_schema(), NOT model_fields repr

- Compare `model.model_json_schema()` of the svc vs monolith Pydantic twins — it is the REAL serialization contract (properties/types/enums/defaults/required/additionalProperties).
- **GOTCHA 1:** `from __future__ import annotations` makes annotations strings → standalone-loaded monolith models raise "not fully defined". FIX: register the importlib-loaded module in `sys.modules[name]` BEFORE `exec_module`, then `model.model_rebuild(_types_namespace=vars(mod))`.
- **GOTCHA 2:** the `description` JSON-schema key carries the class docstring, which legitimately differs (SP01: monolith docstring says `{id}`, svc says `{product_id}` per §0.6 path-param correction). STRIP `description` recursively before comparing — it is doc prose, not wire contract.
- `model_fields` annotation-repr comparison is the WRONG method — it shows `ForwardRef('UUID')` vs `<class 'uuid.UUID'>` false diffs.

## 4. Shim transport pattern (frozen, copy verbatim)

`core/extracted_clients/_transport.py`: `httpx.AsyncClient`, `Timeout(timeout=5.0, connect=2.0)`, EXACTLY ONE retry ONLY on `{503,504}`, JWT + X-Request-ID from contextvars (`set_request_context` API path / `set_worker_context` worker path). Each `<callee>_client.py` re-exports the monolith `<callee>_service` symbol name (`import … as <callee>_service`) so the consumer call sites are byte-for-byte unchanged. 404 → typed exception per callee. Mock with `httpx.MockTransport` in tests (factory patches `_transport.httpx.AsyncClient`, records requests + timeouts).

## 5. Schema-split recipe pointer

The DDL/migration recipe (ALTER TABLE SET SCHEMA, version_table_schema, Risk#5 pre-scan, tested downgrade) is owned by the database-builder — see its memory `.claude/agent-memory/meesell-database-builder/MEMORY.md` (SP01 entry, migration `e7a3c1f9b42d`). The audit table stays in `public` and the moved table goes to the `<mod>` schema → the terminal audit write is a CROSS-SCHEMA INSERT (bind the vendored AuditEvent model to `{"schema": "public"}` explicitly).

## 6. Worktree / isolation-guard relay pattern

- Master tree files are isolation-guard-blocked for WRITES. Do ALL writes (docs, board, STATUS, even own agent-memory files) INSIDE THE WORKTREE and commit them — they are tracked and flow to develop through the gates.
- Spec/handoff files authored in a prior session may live ONLY in the master tree (untracked there) — READ them from the master path (read is allowed), but author NEW deliverables in the worktree.
- NEVER `git add -A` in a symlinked worktree — stage exact `backend/services/svc-<mod>/...` + `docs/...` paths.

## 7. Validation floor (run, report real output)

- svc-<mod> full suite green (count it).
- Full monolith `def test_` MONOTONIC ≥ baseline — quote LIVE count (SP01: baseline 649 in spec → live 698 because the branch cut from a newer develop tip; +49 are NOT from this branch, which touches zero monolith code — prove via `git diff --stat origin/develop...HEAD -- backend/app backend/tests` = EMPTY).
- Monolith unit suite: any failures must pre-exist (zero monolith code changed → mathematically impossible to be caused by the branch). SP01 local: 634 passed, 4 known local-macOS-Py3.11-vs-CI-Linux-Py3.12 teardown artifacts (`got 500` flag-guard + `Event loop is closed`) — documented in MEMORY.md gotcha #1; green on CI Linux Py3.12.
- ruff clean on the svc tree (ruff is at `/opt/homebrew/bin/ruff`, NOT in backend/.venv).
- PG substrate: local Homebrew PG 16 at localhost:5432 works. Roles are bare (running as `root` in sandbox → use role `mugunthansrinivasan` or `meesell` as bootstrap superuser; create the `<mod>_user` role + test DB + grant ALL on schema public for the round-trip). SQLite is NOT acceptable for schema-qualified assertions — PG-gate with documented skips (auth-otp no-tunnel pattern) when no connectable PG.
- venv: master tree `backend/.venv` (Py3.11) has fastapi/httpx/sqlalchemy/openpyxl/asyncpg/pytest. Run svc tests with `PYTHONPATH=. <venv>/bin/python -m pytest`.

## 8. Per-wave variation points

| Wave | Variation vs SP01 export |
|---|---|
| B dashboard | owns NO tables (no Alembic schema-split — §13.D); calls catalog+customer; the OPTIONAL export.summary surface may be HTTP-callable now that svc-export exists. |
| C image | implements `/internal/products/{id}/images` (the export shim's frozen target — SHIM_CONTRACT §2.6); Celery worker extraction; GCS path; **ai_ops VENDORED** for watermark (A1/D6). |
| D pricing | deterministic (no AI); HTTP shims for category + catalog (frozen targets §2.1–2.4). |
| E customer | implements `/internal/seller-profile/{user_id}/compliance-block` (frozen §2.5); seller_profile schema migration. |
| F category | implements `/internal/categories/{id}/schema` + `/field-enum/{field}` (frozen §2.3–2.4); heaviest cache (Valkey DB 3); 4 global tables; **ai_ops VENDORED** (A1/D6); single-flight on 291 brand enums. |
| G iam | every other svc already has local JWT validation (vendored core/auth.py, D7/A2); **cookie-path `/api/v1/auth` preservation** (FE-D5 / A2/D7); refresh-allowlist Valkey contract. |
| H catalog | implements `/internal/products/{id}/ownership-check` + `/export-snapshot` (frozen §2.1–2.2); the spine; last extraction; program NOT complete until §5.G compliance audit. |

---

### SP01 session entry — 2026-06-12 — `mesell-ms-export-backend-session-1` (Phase C)
Built `backend/services/svc-export/tests/test_export_extraction.py` (11 tests, all green incl. live cross-schema PG round-trip). 5 doc deliverables: SHIM_CONTRACT (FROZEN), CI_HYBRID_MODE note, svc-export-rollback runbook, MASTER_PLAN §4 row-A IN EXECUTION flip, this recipe. svc-export suite 37 passed; ruff clean; monolith 698 def test_ (≥649 monotonic); §16.G AST parity + wire-shape JSON-schema parity PROVEN in CI form. §14 LOCKED amendment carried to founder-gate notes (NOT self-applied). Merge-gate review is a SEPARATE later dispatch.
