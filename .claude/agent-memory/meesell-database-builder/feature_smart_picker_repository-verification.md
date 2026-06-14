# feature_smart_picker_repository-verification.md

## Session header
- Session name: mesell-smart-picker-backend-session-1
- Date: 2026-06-11
- Branch: feature/smart-picker/backend
- Worktree: /tmp/mesell-wt/smart-picker-backend

## Files touched
- `backend/tests/modules/category/test_trigram_p95.py` — NEW (benchmark fixture)
- `backend/app/modules/category/repository.py` — VERIFY only (not modified)
- `backend/app/core/tenancy.py` — VERIFY only (not modified; drift reported)

## What was done
1. **§9.D conformance check — repository.py:**
   - `search_via_trigram(db: AsyncSession, q: str | None, super_id: str | None, limit: int, offset: int) -> tuple[list[CategoryRow], int]` — MATCHES §9.D verbatim.
   - `assert_category_exists_uncached(db: AsyncSession, category_id: UUID) -> bool` — MATCHES §9.D verbatim.
   - No method is missing; no signature drift found for the two §9.D methods specified in the acceptance criteria.

2. **`_GLOBAL_TABLES` carve-out check — tenancy.py:**
   - DRIFT FOUND: `core/tenancy.py` does NOT have a `_GLOBAL_TABLES` set.
   - The file exports only `TenantViolationError`, `assert_owned`, `scope_to_user`.
   - BACKEND_ARCHITECTURE.md §9.D says: "categories, templates, field_enum_values, field_aliases are listed in core/tenancy.py's _GLOBAL_TABLES set."
   - repository.py's module docstring references `core/tenancy._GLOBAL_TABLES` but the object does not exist.
   - Reported as DRIFT in final report. Did NOT patch without lead approval.

3. **Benchmark fixture authored:**
   - `backend/tests/modules/category/test_trigram_p95.py` (290 LOC)
   - Two tests:
     a. `test_trigram_p95_explain_hits_gin_index` — EXPLAIN ANALYZE asserting Bitmap + GIN index name in plan
     b. `test_trigram_p95_100_iterations` — 100-iteration benchmark with full histogram (min/P50/P90/P95/P99/max/stdev), super_id secondary path (25 iters)
   - Infra gate: `PYTEST_RUN_SLOW=1` env var + `skip_unless_slow_enabled()` function (inline, mirrors `tests/perf/conftest.py` pattern without cross-conftest import)
   - Markers: `pytestmark = [pytest.mark.slow, pytest.mark.perf]`
   - Complements (does not duplicate) existing `test_trigram_search_uses_gin_index.py`
   - Budget: P95 < 200 ms per §9.J + MVP_ARCH §7.5 (no 10% noise band — budget is loose enough without it)

4. **Commit:**
   - SHA: `075f162` on branch `feature/smart-picker/backend`
   - Staged explicitly by filename: `git add backend/tests/modules/category/test_trigram_p95.py`
   - NOT pushed (lead pushes at gate time)

## Test results
- pytest collection: 17/17 tests in `tests/modules/category/` collected cleanly (no import errors)
- ruff: 0 issues on the new file
- EXPLAIN/benchmark execution: NOT run — dev tunnel (localhost:5433) is DOWN (Connection refused confirmed via `nc -zv localhost 5433`)

## Open items
- `_GLOBAL_TABLES` drift in `core/tenancy.py` — awaits lead decision on whether to add the set as a pure documentation/linter-convention set. It has no runtime impact (the repository already doesn't call `scope_to_user` — the absence of the set doesn't break anything). But the §9.D spec text and the repository.py module docstring both reference it as if it exists.
- EXPLAIN/benchmark execution deferred to when dev tunnel is restored.

## Cross-feature gotchas
- `_GLOBAL_TABLES` drift affects all modules that read global reference tables (categories, templates, field_enum_values, field_aliases). If an §19 import-linter rule is added that checks "every owned-table query is exempt if table in _GLOBAL_TABLES", the rule will fail until this set is added. Relevant for ai-autofill and image-precheck features if they add category reads.

## Next-session brief
This session's scope is complete (benchmark authored, §9.D verified, drift reported). If the lead approves patching `core/tenancy.py`, the next database-builder session should add `_GLOBAL_TABLES: frozenset[str] = frozenset({"categories", "templates", "field_enum_values", "field_aliases"})` to `core/tenancy.py` and update the module `__all__` list. No migration needed.
