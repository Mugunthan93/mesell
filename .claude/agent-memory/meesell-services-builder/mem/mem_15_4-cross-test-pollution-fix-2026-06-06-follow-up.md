## §4 cross-test pollution fix (2026-06-06 follow-up)

### Symptom
After `test_database.py`'s seeded-data tests ran (session-scoped `dev_engine`),
the next test that called `get_valkey_otp()`/`get_valkey_cache()` raised
`RuntimeError: Task got Future attached to a different loop`. 10 tests in
test_core_cache/plan_guard/rate_limit_mw affected when the full suite ran.

### Root cause
The old `use_live_valkey` fixture pivoted module-level singletons in
`app.shared.valkey._otp_client`/`_cache_client`. Those clients had connection
pools bound to whatever loop ran the fixture setup. When pytest-asyncio's
session-loop-scoped fixture (`dev_engine`) forced its loop into scope, the
singleton's pool was bound to that loop. Function-scoped tests that ran
later in a different loop hit the cross-loop Future error.

### Fix (tests/conftest.py)
Replaced singleton-pivot with **monkeypatch of `get_valkey_otp` /
`get_valkey_cache`** in (a) `app.shared.valkey`, (b) every consumer module
in `app.core.*` that did `from app.shared.valkey import ...` at module load
(`cache`, `plan_guard`, `middleware.rate_limit_mw`, `middleware.audit_mw`),
and (c) the test modules `test_core_cache` + `test_core_plan_guard` (pytest
loads tests as TOP-LEVEL modules, not `tests.test_core_*`, when there is no
`tests/__init__.py`). Each patched factory returns a FRESH Redis client
built inside the CURRENT loop on every call. All clients are tracked in a
local list and `aclose`d in teardown before the loop dies. The fixture also
defensively nukes any pre-existing `_otp_client` / `_cache_client` singletons
at entry — no shared state survives.

### Why per-call fresh client (not singleton pivot)
- `redis.asyncio` Connection pools attach to whatever loop is running on first
  await on a connection. Singletons built in a session loop are unusable in a
  function loop.
- monkeypatch teardown is automatic — zero leak risk; no need to restore.

### Acceptance after fix
- Reproducer `pytest tests/test_database.py tests/test_core_cache.py::test_versioned_key_format` → 43 PASS (was 42 PASS + 1 cross-loop error).
- Full §4 suite `pytest tests/test_app_boot_integration.py tests/test_database.py tests/test_core_*.py tests/test_shared_*.py` → **149 PASS, 3 skip, 0 fail**.
- `ruff check app/core/ app/main.py tests/conftest.py tests/test_core_*.py` → All checks passed (also cleaned pre-existing `import uuid` unused-import from conftest).

### Files touched
- `backend/tests/conftest.py` — fixture body rewritten lines ~119–230 (was 119–162); pre-existing `import uuid` removed line 7.
- **NO** consumer file changes — every consumer already calls through `app.shared.valkey.<name>` via `from app.shared.valkey import …` at module load; the monkeypatch of those captured names covers the call sites.

### Pattern locked for future tests
When introducing a new core/middleware module that calls `get_valkey_*`,
append its import path to the consumer-patch tuple in
`use_live_valkey` (currently 4 entries). When introducing a new test
module that imports `get_valkey_*` by name at module load, append it to
the test-module-patch tuple (currently 2 entries).

---
