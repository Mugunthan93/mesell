# Chore — backend follow-ups batch (2 items) — mesell-backend-chores-session-1 (2026-06-12)

Branch `chore/backend-followups` off origin/develop @ eb84779, worktree /tmp/mesell-wt/backend-chores.
STEP 1 (audit + SPECs) done by lead; master dispatches the 2 specialists; lead gates after.
Board+STATUS commit `af7ef7e` pushed.

## Item 1 — Celery task routing (infra inter-lead unblock)
- REAL task name = `image.precheck` — explicit `@shared_task(name="image.precheck", ...)` at
  `backend/app/modules/image/tasks.py:416`. NOT a dotted-module default. Infra's cited mapping is
  CORRECT verbatim. (Always audit the real `name=` — do not trust the memo's cited name blindly;
  this time it matched, but the audit is the contract.)
- As-built `workers/celery_app.py` has NO task_routes/task_queues; image.precheck → default `celery`
  queue; worker --concurrency=4 no -Q → consumes default. export.xlsx is the OTHER V1 task (also
  default queue) per include list L103-105. Default-queue invariant MUST be preserved (export runs
  on the same worker, no -Q) → route maps ONLY image.precheck.
- Owner: services-builder (celery_app.py is §3.I / §18 services territory).

## Item 2 — _GLOBAL_TABLES drift (from smart-picker gate PR #72)
- KEY FINDING: `core/tenancy.py` exports ONLY {TenantViolationError, assert_owned, scope_to_user}.
  NO `_GLOBAL_TABLES`. The symbol is named in docs §9.D (L3245), §9.J (~L3461) + `category/
  repository.py:17` docstring — but the as-built §19 linter `tests/lint/check_scope_to_user.py`
  enforces the global-table carve-out by MODULE-NAME ALLOWLIST (`ALLOWLISTED_MODULES =
  {"category","dashboard","iam"}` L61), NOT by reading the frozenset. So _GLOBAL_TABLES has ZERO
  runtime/linter consumer — pure doc-vs-code drift.
- §4.C LOCKED text (L938) names the 4 global tables in PROSE only — does NOT reference the symbol →
  adding the frozenset does not alter a LOCKED required shape. Safe additive reconcile.
- Fix = add documentation-sentinel frozenset({"categories","templates","field_enum_values",
  "field_aliases"}) to core/tenancy.py. Owner: database-builder (tenancy-foundation; matches queue).
- GOTCHA for the gate: do NOT let database-builder re-point the linter to consume the frozenset
  WITHOUT founder R1 sign-off — that changes §19 linter behaviour. Default = sentinel only.

## Founder rulings flagged (R1 sentinel-only vs linter-repoint; R2 one-PR vs two). Defaults: R1 sentinel-only, R2 one PR.

## Reusable patterns
- "Audit the real Celery task name via the `name=` kwarg" — registered name can diverge from the
  module path; the `@shared_task(name=...)` literal is authoritative for task_routes keys.
- "Doc references a symbol the code never grew" is a real drift class — grep the symbol across BOTH
  .py and docs; if the only consumers are docstrings, the fix is a sentinel (not a refactor), and
  confirm no LOCKED section requires the symbol's *shape* before adding it.

## STEP 3 — MERGE-GATE VERDICT: PASS (both items) — 2026-06-12
- Branch tip d262c95 (code) + 62e754c (gate-verdict docs). 4 code/doc files, +153 -0, all additive.
- Item 1 (services-builder 26261ce): GATE evidence `image.precheck -> {'queue':'image-tasks'}`,
  `export.xlsx routed? False` (default-queue invariant — load-bearing check PASSED). §11.E body +
  4 worker invariants untouched. ruff clean.
- Item 2 (database-builder d262c95): GATE evidence `_GLOBAL_TABLES` importable + in __all__; §19
  `python -m tests.lint.check_scope_to_user` Contract 8 PASS (module-name allowlist intact — sentinel
  did NOT alter enforcement; R1 sentinel-only honored). BACKEND_ARCHITECTURE.md untouched. ruff clean.
- 0 route decorators (§17 stays 28), 0 alembic (no head divergence), §2.D unchanged.
- PR #143 (chore/backend-followups → develop) opened with full gate verdict; founder's gate per D1,
  left OPEN. R1 (sentinel-only) + R2 (ONE PR) defaults applied + FLAGGED in PR body.
- Infra hand-off live: post-#143-merge, infra uncomments `-Q image-tasks` in k8s/worker.yaml.

## GATE-RUN GOTCHA (reusable)
- The worktree has NO `.venv`; the interpreter lives in the MAIN checkout at
  `/Users/.../mesell/backend/.venv/bin/python`. To gate worktree code: run that interpreter with
  `PYTHONPATH=/tmp/mesell-wt/<wt>/backend`. Settings boot requires the FULL CI dummy-env set INCLUDING
  `APP_ENV=development` (NOT "dev" — Literal), `MSG91_TEMPLATE_ID`, `RAZORPAY_WEBHOOK_SECRET`
  (the §5.D guard fails-fast and names the missing vars one batch at a time).
