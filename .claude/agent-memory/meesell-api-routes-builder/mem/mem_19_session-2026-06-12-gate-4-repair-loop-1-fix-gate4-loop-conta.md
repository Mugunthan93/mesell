## Session: 2026-06-12 — Gate-4 repair loop 1 (fix/gate4-loop-contamination, PR #159)

### Task summary
Repaired 3 defects (D1/D2/D3) rejected by coordinator's STEP 3 merge-gate.
PR #159 Gate-4 went from `5f/13e` to `180p/17s/0f/0e` (PASS). CI run 27394517680 GREEN.
Commits: 0059272 + b9d1557 on fix/gate4-loop-contamination.

### D1: SAVEPOINT on iam_client was a net regression
Root cause: split-engine tests (`test_customer_cross_module_eligibility`,
`test_customer_full_onboarding_flow`) create user via `iam_client` then read it back
via a SEPARATE NullPool engine on `os.environ["DATABASE_URL"]`. With SAVEPOINT isolation
the user row is inside an uncommitted outer transaction → invisible to the second engine
→ ForeignKeyViolationError.
Fix: remove SAVEPOINT from `iam_client`. Use plain commit-for-real `async_sessionmaker(engine)`.
The function-loop NullPool engine ALONE kills the cross-loop error; SAVEPOINT not needed for
iam_client because `_cleanup_users_by_phone_prefix` handles teardown.
Key distinction: `customer_client` / `export_client` CAN use SAVEPOINT because they are
self-contained (no split-engine pattern). `iam_client` MUST NOT use SAVEPOINT.

### D2: _otp_client module singleton bypasses DI — must patch explicitly
Root cause: `rate_limit_mw._check_window` calls `await get_valkey_otp()` as a plain
function (not through FastAPI DI). `dependency_overrides[get_valkey_otp]` has ZERO effect
on middleware. When test N's function loop closes, `_otp_client.connection._writer._transport._loop`
is the closed loop. Test N+1 fixture setup boots a new lifespan and the rate_limit_mw pipeline
call invokes `loop.call_soon(self._call_connection_lost, None)` on the closed loop →
`RuntimeError: Event loop is closed`.
Fix: patch `_valkey_module._otp_client` at module level in ALL fixtures that boot a lifespan
and make requests (including `unauth_client`!). Same pattern as `_cache_client` patching.
The `unauth_client` erroneously documents "does NOT require Valkey" — FALSE: rate_limit_mw
always runs before auth rejection in the middleware chain.
Affected fixtures: iam_client (integration/conftest.py), customer_client (test_customer_routes.py),
export_client (modules/export/test_router.py), unauth_client (modules/export/test_router.py).

### D3: G7 auto-apply test was stale at 2 assertion points
Root cause: G7 FOUNDER RULING 2026-06-11 (ai-autofill D1) removed auto-apply from
`autofill_product`. Service is correct (applied always False, writes only ai_suggestions_jsonb).
Two test assertions were stale:
1. `autofill_result.applied.get("product_name") is True` → `is False` (direct assertion)
2. `patch_product(status="ready")` fails with ValidationFailedError (3 compulsory fields empty)
   because G7 means autofill no longer writes to `fields_jsonb`.
Fix: (1) change `is True` → `is False`. (2) add a PATCH step that manually accepts the
suggested field values (simulates seller accepting autofill suggestions in UI), THEN transitions
to `status=ready`. Both fixes cite `BE-CATALOG-G7-AUTOAPPLY-1` in comments.
Lesson: when G7 (or any ruling) changes behavior, ALL downstream test steps that depended on
the OLD behavior must also be updated — not just the direct assertion.

### Key insight: always interrogate ALL assertions in a lifecycle test
When a ruling removes behavior (e.g. auto-apply), a multi-step test will cascade failures:
- Step N: assertion against the removed behavior → fixed
- Step N+2: downstream step that was predicated on step N's OLD behavior → also broken
Both must be fixed. Do not stop after fixing the first visible assertion.

### Rate limit middleware always runs before auth rejection
`AuthContextMiddleware` sets `request.state.user = None` — it does NOT short-circuit the
request. The 401 is raised inside the route handler's `get_current_user` dependency, which
runs AFTER all middleware. So `RateLimitMiddleware` always runs for every request, including
unauthenticated ones. Any fixture that boots the lifespan and makes ANY request must patch
`_otp_client`.

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| Gate-4 repair-1 COMPLETE 2026-06-12 | project | 5 files fixed; 2 commits; CI 27394517680 GREEN 180p/17s/0f/0e |
| SAVEPOINT vs commit-for-real | reference | iam_client MUST NOT use SAVEPOINT (split-engine); customer/export CAN. |
| _otp_client singleton patch | reference | ALL lifespan-booting fixtures must patch _otp_client; DI override alone insufficient |
| unauth_client also needs _otp_client patch | reference | rate_limit_mw runs before auth rejection; unauth requests hit _check_window |
| G7 cascade lesson | reference | Ruling that removes behavior breaks ALL downstream steps predicated on it; fix all |
