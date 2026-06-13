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

### MS-B session entry — 2026-06-13 — `mesell-ms-dashboard-session-1` (Phase C, founder gate open)
**Dashboard is the SECOND validated extraction. The recipe held VERBATIM** — same step sequence (branch+F3 → Phase A ∥ infra → Phase B services+routes → Phase C lead → gates), same §16.G AST recursive-strip diff-proof, same `model_json_schema()` wire-shape method, same frozen shim transport (`Timeout(5.0,connect=2.0)`, 1-retry-503/504, JWT+X-Request-ID, httpx.MockTransport in tests). Merge-gate PASSED — both group PRs (#195 backend, #196 infra) squash-merged into `feature/microservices-dashboard/integration`; integration→develop left OPEN as the FOUNDER gate (D1, I do NOT approve). svc-dashboard = 35 app files + 30 svc test cases all green; monolith 698 `def test_` monotonic (branch touches ZERO `backend/app|backend/tests`). 5 doc deliverables landed (board, STATUS, this recipe, MASTER_PLAN §4 row-B + §1.C prose fix, `CI_HYBRID_MODE_dashboard.md`). `BACKEND_ARCHITECTURE.md §13` extraction note carried to founder gate (LOCKED, NOT self-applied per §7.3). New infra dep: SM secret `dev-dashboard-db-password`.

**Dashboard VARIATION vs SP01 export (the per-wave deltas, §8 row B confirmed in practice):**
- **Owns ZERO tables → database-builder is VERIFY-ONLY, NO schema-split.** No `ALTER TABLE … SET SCHEMA`, no `version_table_schema`, no Risk#5 orphan pre-scan, no standalone Alembic chain. The §13.D structural exception (NO `repository.py` in the dashboard subtree) carries into the extracted service verbatim — absence is intentional design.
- **NO Celery.** Dashboard has no `tasks.py`. Single-task Celery app step is SKIPPED entirely; requirements.txt carries no celery; sys.modules check confirms zero celery import. Lightest service of the program (api-only, 50m/128Mi, 1 replica, NO worker).
- **LEAF CONSUMER → exposes NO `/internal/*`.** Dashboard is called by nobody (only `main.py` imports it). It has 2 OUTBOUND shims and ZERO inbound. Contrast export (which also exposes none) — dashboard is purer: zero tables AND zero inbound surface.
- **The customer shim is MOCK-tested, not live-tested.** `get_onboarding_completeness` → `GET /internal/seller-profile/{user_id}/onboarding-completeness` is mocked with `httpx.MockTransport` because that `/internal/*` endpoint is NOT live until customer extracts at MS-3/E. The catalog `list_products` shim is likewise mock-tested (catalog is MS-5/H, still in-monolith). During the dashboard window BOTH shims point at the monolith ClusterIP; the mock stands in for it. No live round-trip is possible yet (and the audit round-trip that SP01 ran is N/A — dashboard owns no schema, its audit_mw path is INERT on a read-only GET, so there is no cross-schema INSERT to prove; the I5 grant exists only so the vendored audit import-chain wires).
- **§1.C plan-prose typo caught + corrected.** MASTER_PLAN §1.C named the call `get_profile_completeness`; AS-BUILT is `get_onboarding_completeness` (cited customer/service.py:682). Corrected as a plan-PROSE fix (NOT a §13 LOCKED §13 amendment) and flagged in the PR body. GROUND-TRUTH-against-LIVE-tree (recipe step 0) paid off again — same class of plan-text drift SP01 found.
- **CI hybrid-mode: callees docker-composed = NONE** (same as export). Both dashboard callees (catalog, customer) are in-process in the monolith; shims point at the monolith ClusterIP; hybrid-mode tests mock the transport. No callee container exists.

### MS-D session entry — 2026-06-13 — `mesell-ms-pricing-backend-session-1` (Phase C, MERGE GATE REJECTED)
**Pricing is the FOURTH extraction attempt; the recipe held — and the merge gate did its job: it REJECTED.** Step sequence, §16.G AST recursive-strip, `model_json_schema()` wire-shape, frozen shim transport all VERBATIM. The Phase-C gate found a runtime-breaking defect the four specialists' self-reports did NOT surface, proving HYBRID rule-7 (the gate is a real gate, not a rubber stamp).

**THE REJECT (the lesson — FLAG-PARITY × TRIMMED-SETTINGS, novel vs prior waves):**
- svc-pricing `router.py:99` correctly carried the monolith flag guard `if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:` VERBATIM (flag-parity discipline = right). BUT the services-builder's **trimmed Settings** (`app/shared/config.py`) DROPPED the `FEATURE_PRICE_CALCULATOR_ENABLED` field the monolith defines (`config.py:223 bool=True`). `model_config=extra="ignore"` → the attr does not exist → `AttributeError` on EVERY request, 500 before the service runs. The single mounted route is 100% broken.
- **WHY NO PRIOR WAVE HIT THIS:** export/dashboard/image routes either had no feature-flag guard or their trimmed Settings happened to keep the referenced field. Pricing is the first wave where a vendored route references a config field that the "trim the Settings to remove vendor cruft" step silently dropped. **The trim is NOT free — every `settings.<X>` referenced by ANY vendored file (router, service, mw) MUST survive the trim.**
- **NEW PERMANENT GATE STEP (add to §6 validation floor):** *grep the vendored tree for `settings\.[A-Z_]+` and assert every referenced attr exists on the trimmed Settings (boot the app OR probe `settings`).* A vendored route/mw referencing a trimmed-away config field is a P1 reject-class defect — it is invisible to §16.G (that covers service.py executable lines, not config-field existence) and invisible to a docstring grep. The LEAD test now encodes this as `test_feature_flag_exists_on_trimmed_settings` — copy that guard into every future wave's Phase-C test.

**Row-D VARIATION vs prior waves (§8 row-D confirmed in practice):**
- **DETERMINISTIC, no AI, no Celery, no vendor** — smallest+simplest service tree (43 files). svc requirements: fastapi/uvicorn/pydantic-settings/sqlalchemy/asyncpg/redis/pyjwt/httpx/prometheus only.
- **LEAF-ish consumer: 2 OUTBOUND shims (catalog + category), ZERO inbound `/internal/*`.** Unlike export (also zero inbound) pricing has a NON-TRIVIAL outbound surface AND owns a table (unlike dashboard which owns none) — so it exercises BOTH the shim-mock path AND a real cross-schema audit round-trip.
- **§0.6 OPTION-B shim-WIDENING is the novel delta.** The monolith did a SHARED-ORM `db.get(ProductORM, product_id)` read of a catalog-owned table to get `category_id`. Option B widened the catalog `/internal/products/{id}/ownership-check` shim to ALSO return `category_id`; the §16.G executable delta is exactly 3 monolith stmts (db.get + soft-delete-if + `category_id=product.category_id`) → 1 svc stmt (`category_id=await catalog_service.get_category_id(...)`). **The §16.G AST parity test must NORMALISE this one block out of BOTH twins** (I collapse the run between the `assert_product_ownership` call and the `get_commission` assign to a single `Pass` in each), THEN assert byte-identity on the rest — plus a companion test that asserts the un-normalised trees DIFFER (so the normaliser isn't masking real drift / making parity vacuous). This "normalise the ONE allowed hunk + prove the hunk is real" pattern is the row-D recipe addition for any wave with an allowed executable delta beyond imports.
- **category `/internal/categories/{id}/commission` is a NEW shim** (pricing is the first caller of `get_commission` — not in the MS-A export contract). Frozen contract: returns `{"commission_pct":"<decimal-string>"}` NEVER null (`"0.00"`=unseeded); Sub-Plan F must implement.
- **T6 cross-schema audit round-trip RAN LIVE** (PG16 localhost, role `mugunthansrinivasan`, db `meesell`) — pricing's POST route fires audit_mw on 2xx → real `public.audit_events` INSERT while `pricing_calcs` is in schema `pricing`. (Dashboard's was N/A — read-only GET, inert audit.) Env: the master-tree venv `/Users/mugunthansrinivasan/Project/mesell/backend/.venv` is Py3.11 with all deps; system python3 is 3.9 (too old for some union syntax at runtime without `from __future__`). PG is at localhost:5432 (NOT a tunnel this session). `psql` only at `/opt/homebrew/opt/postgresql@16/bin/`.
- **Cross-wave TLS finding (carry, don't reject):** svc-image + svc-export ingressroutes reference nonexistent TLS secret `api-mesell-xyz-tls`; the live dev secret is `api-tls`. svc-pricing's infra correctly uses `api-tls`. Their cutover would fall back to Traefik default cert. Informational to infra+master at the founder gate.
- **Pending founder asks (carry to founder gate after the fix):** §12 BACKEND_ARCHITECTURE.md "Extracted to svc-pricing V1.5" amendment (LOCKED, NOT self-applied per §7.3); `dev-pricing-db-password` SM secret at deploy.
- **GATE OUTCOME:** REJECT — group PRs NOT opened, founder gate NOT opened. LEAD test (14 tests; 13 PASS + 1 FAIL=the guard) committed to feature/microservices-pricing/backend (`f6a80b2`) so it validates the services-builder fix on re-run. NEXT: re-dispatch services-builder (1-field config add) → re-run LEAD test (expect 14/14) → THEN author the 5 docs + open the PRs.
