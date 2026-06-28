## Export validation aggregation — fail-fast → collect-all (2026-06-18, PR #291, branch feat/export-validation-aggregation, worktree /private/tmp/mesell-wt/export-validation off origin/develop@86dfb86)

### What I did
Reworked `export/service.py initiate_export` from raise-first-failing to gather-all-then-raise-once.
- NEW `ExportValidationFailedError(ExportError)`: code `export.validation_failed`, status 422, msg-id
  `export.validation.failed`. Carries `failed_checks: list[dict[str,str]]` (each `{check_id, message_key}`).
  Added to `__all__`. Did NOT overload `ProductNotReadyForExportError`/`FrontImageMissingError` — the worker
  pipeline `_run_export_pipeline` STILL raises those two standalone in its except clause (so the two imports
  stay live in service.py — verified via grep before assuming unused-import).
- Step 1 ownership gate (`catalog_service.assert_product_ownership`) stays FAIL-FAST 404 — NOT aggregated.
  Two checks aggregated IN ORDER: `quality_status` (snapshot.validation_summary.status != "ready") then
  `front_image_missing` (only when fmt=="xlsx_with_images" AND no image with idx==1/status=="ready").
- core/errors.py `_meesell_error_handler`: ADDITIVE — `getattr(exc, "failed_checks", None)`; append only when
  present. Mirrors the existing `_pydantic_validation_handler` "errors" append. Locked §4.F keys
  (detail/code/validation_message_id/request_id) untouched; field name is `code` NOT `error_code`.
- 3 new i18n keys in messages_en.py export block (Contract-10 3-segment clean).

### Test-run recipe (no-.venv worktree pattern + NEW gotcha)
Worktree has no .venv → toolchain = `/Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/python3.11`.
NEW GOTCHA for pure-unit tests: conftest has a `scope="session", autouse=True` fixture `_provision_test_schema`
that CONNECTS to Postgres (asyncpg) + runs `alembic upgrade head` WHEN `TEST_DATABASE_URL` is set. For pure-unit
no-DB tests you must **`unset TEST_DATABASE_URL`** so it no-ops. BUT conftest line 13 does
`DATABASE_URL = os.environ.get("TEST_DATABASE_URL", <fallback>)` AND lines 23-27 guard the DB name ends in
`_test` — so set `DATABASE_URL=postgresql+asyncpg://x:x@localhost:5433/meesell_test` explicitly and
`unset TEST_DATABASE_URL` (NOT `TEST_DATABASE_URL=` empty — empty string overrides DATABASE_URL to "" and trips
the non-test-db guard). Plus the ~13 dummy REQUIRED_FIELDS exports. ruff at /opt/homebrew/bin/ruff.
Result: 5/5 aggregation + 8/8 test_core_errors + 104/104 i18n-id-regex (Contract 10 covers the 3 new keys) PASS.

### Mock pattern for initiate_export unit tests (reusable)
service.py uses MODULE-LEVEL names `catalog_service`, `image_service`, `export_repo` (patch via
`monkeypatch.setattr(export_service, "<name>", SimpleNamespace(method=AsyncMock(...)))`). The Celery enqueue is a
LAZY import inside the fn body (`from app.modules.export.tasks import export_xlsx_task`) — patch it on the SOURCE
module `app.modules.export.tasks.export_xlsx_task` (SimpleNamespace with `.delay` MagicMock), NOT on export_service.
`_set_format_hint` is best-effort Valkey — AsyncMock it. Snapshot shape for the quality check =
`SimpleNamespace(validation_summary=SimpleNamespace(status=...))`. Image summaries = objects with `.idx`/`.status`.

### CRITICAL test-marker note (from PR #290 blocker, re-confirmed)
`pytestmark = pytest.mark.unit` MUST sit at module top or CI Gate 1 `pytest -m "unit"` SILENTLY SKIPS the file.

### Worktree note
guard-master-tree-git blocks `git checkout -b` in the master tree — must `git worktree add -b <branch>
/tmp/mesell-wt/<name> origin/develop`. Also: this session was isolated to the design-figma worktree, so my
canonical memory at the shared-checkout path was un-writable; the harness routed Edit to the worktree copy of
MEMORY.md. The two memory copies may now diverge — reconcile on next shared-checkout session.
