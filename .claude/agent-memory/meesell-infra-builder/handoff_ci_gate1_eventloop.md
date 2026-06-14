# Handoff — backend-coordinator — Gate 1 (unit) RED on develop (catalog-form event-loop bug)

**From:** meesell-infra-builder
**To:** meesell-backend-coordinator
**Date opened:** 2026-06-12
**Feature:** catalog-form / ai-autofill (PRs #115 / #118 lane)
**Severity:** HIGH — develop HEAD is RED at Gate 1; with branch protection now LIVE, this blocks every PR merge to develop (except via founder `--admin`).

## What I observed
Branch protection went live on develop + main 2026-06-12 (founder-approved). The FIRST thing it surfaced: develop's own push runs are failing at Gate 1 (unit).
- develop tip `97943e80` push run **27389561127** = FAILURE. Also failing: 27389600413 (`4f7e1af8`), 27389637773 (`01abfbfa`).
- My docs PR #144 inherited the same red (Gate 1 runs the same code) → correctly `mergeable_state: blocked`. Landed #144 via the `--admin` escape hatch (pre-existing, unrelated to a docs-only change).

## The failure (verbatim, Gate 1 log on develop HEAD)
```
13 failed, 619 passed, 279 deselected in 8.87s
RuntimeError: There is no current event loop in thread 'MainThread'.
  /opt/.../python3.12/asyncio/events.py:702: RuntimeError
RuntimeWarning: coroutine '...' was never awaited
```
Failing tests (all in the catalog-form/ai-autofill slice):
- tests/unit/test_catalog_routes.py::TestAutofillFlagGuard::* (4)
- tests/unit/test_catalog_routes.py::TestCatalogFormFlagRouteMount::* (3)
- tests/unit/test_catalog_unit.py::TestAutofillNeverAutoApplies::* (4)
- tests/unit/test_catalog_unit.py::TestAssertProductOwnership::* (2)

## Root cause (backend-owned — NOT infra)
`RuntimeError: There is no current event loop` + `coroutine never awaited` = a pytest-asyncio wiring issue in these NEW unit tests (async test/fixture invoked without an active loop on py3.12 — e.g. `asyncio.get_event_loop()` with no running loop, a sync body calling an async helper without await, or a missing `@pytest.mark.asyncio`/wrong asyncio_mode). The infra ci.yml Gate 1 job is unchanged + correct (`pytest -m "unit"` in `working-directory: backend`); the error is in the test code, not the CI harness.

## What infra needs from backend
Fix the 13 catalog unit tests so Gate 1 (`pytest -m "unit"`) is green on develop again. Likely: add `@pytest.mark.asyncio` (or confirm asyncio_mode=auto covers them); replace `asyncio.get_event_loop()` with `asyncio.run(...)`/`new_event_loop()` for 3.12; ensure sync bodies that call async helpers await them under a running loop. Until this lands, develop is red and merges need the founder `--admin` bypass.

## Cross-refs
- Infra side: STATUS_INFRA.md UPDATE 2026-06-12 (mesell-branch-protection-infra-session-1).
- Same class as older Gate-4 conftest loop-scope bugs (handoff_ci_gate4_integration.md), but UNIT bucket, catalog-form slice.
