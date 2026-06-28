# conftest patterns & fixture pitfalls

Reusable fixture patterns and the pitfalls observed while writing backend tests.
Append a note whenever a fixture surprises you (event-loop scope, NullPool
behaviour, Valkey DB isolation, mock-adapter wiring, JWT minting).

## Seeded from prior project memory (2026-06-22)
- Mint test JWTs with `app.core.auth.issue_access_token(user_id, plan)`; send as
  `Authorization: Bearer ...`.
- Seed via direct ORM INSERT helpers co-located in the test module (no live OTP flow).
- Multi-tenant isolation tests should assert 404 (preferred per §15.B "leaks no
  info") OR 403; a 200/204 is a Layer-1/Layer-2 breach.
- The `db` fixture is on `NullPool` (one conn per test) — do not assume pool reuse.
- Valkey tests use DB 15, never the app DBs 0–3.

## Pitfalls
- `pytest-asyncio` event-loop misuse causes `no current event loop` (the catalog-form
  gate failures) — use the shared async fixtures, never hand-roll loop handling.

## Wave-1 pitfalls (2026-06-22, PR #380)
Nine pitfalls hit while authoring/extending the Wave-1 suite:
1. `TEST_VALKEY_URL` is `redis://localhost:6379/15` (DB 15) — NOT `:6381`. Pointing at
   `:6381` (a non-running port) silently breaks rate-limit/Valkey tests.
2. `POST /auth/otp/send` returns **202** (Accepted), not 200. Asserting 200 fails.
3. `CurrentUser` exposes `user_id` and `plan` (not `id`/`tier`). Reference those field
   names when building the auth dependency override / mock.
4. ASGI transport stub for `httpx.AsyncClient` must be wrapped with
   `@asynccontextmanager` — a bare async def fixture won't enter/exit correctly.
5. `catalog_repo.find_by_id` signature is `find_by_id(db, user_id, product_id)` —
   positional order matters; passing `(db, product_id)` returns the wrong row / None.
6. `_validate_single_field` takes **4 positional args** — call it positionally; kwargs
   or a 3-arg call raises TypeError.
7. `enforce_plan_limit` must be patched as an **AsyncMock** (it is awaited); a plain
   `MagicMock` yields a coroutine-never-awaited warning and wrong control flow.
8. Python 3.11 forbids a backslash inside an f-string expression — build the string
   outside the f-string (assign to a var first) to avoid a SyntaxError on the gate.
9. A fresh worktree has **no `.venv`** — run pytest with the master tree's `.venv`
   interpreter, not a per-worktree env that doesn't exist.

## Wave-3 pitfalls (2026-06-22, PR #396 — scribed by meesell-qa-coordinator)

Five further pitfalls hit while authoring the Wave-3 catalog-vertical suite (continuing the Wave-1 list 1-9):
10. **`auth_client` + the catalog conftest `db` fixture are incompatible** (two-connection visibility). The catalog `db` fixture runs inside a SAVEPOINT/ROLLBACK transaction on `db_engine`; the HTTP client's `override_get_db` does NOT commit, so rows seeded via `db`/`user` are invisible to the client's request sessions, and `get_current_user`'s DB lookup 403s on the uncommitted user row. SOLUTION: a local `_preview_client` / `_delete_client` fixture modelled on the IAM suite's `iam_client` — a fresh NullPool engine against `DATABASE_URL` (the `_test` DB), seed with a REAL commit, override BOTH `get_current_user` (returns a pre-built `CurrentUser`, no request-time DB lookup) AND `get_db` (commit-on-success), mint a JWT and pin it as Bearer, then clean up all FK-dependent child tables in dependency order via raw SQL at teardown.
11. **Route-level integration tests that short-circuit `get_current_user`** do not need a live OTP/Valkey flow — the auth dependency override removes the Valkey dependency for the happy/cross-tenant/autosave cases. The unauthenticated 401 case uses a bare `client` with a wrong/absent token — the 401 fires at the auth dep before any DB lookup.
12. **A fresh worktree's `backend/` dir needs a `.env` symlink** — Pydantic Settings reads `.env` from cwd; without it the test app fails to construct Settings. Symlink the master tree's `backend/.env` (or run from a dir that has one).
13. **The conftest defaults `VALKEY_URL` to `redis://localhost:6381/15` (the CI Valkey port).** Locally only `:6379` runs, so any test that exercises the rate-limit / plan-guard Valkey path (e.g. `test_flag_gate.py`) 500s with connection-refused. This is an ENV limitation, not a test defect — disclose it (the file is unchanged at the integration base and fails identically there). For local green, point `TEST_VALKEY_URL`/`VALKEY_URL` at a running Valkey OR scope the run to non-Valkey files.
14. **PIL boundary tests must import the REAL check functions** (`app.modules.image.tasks._check_jpeg`, `_check_resolution`, `_check_white_background`, color-space detection) and assert pass AND fail at the threshold — not re-implement the check in the spec. The module import requires several env vars; set DUMMY values at import time so the import succeeds hermetically without a live config.

## Wave A pitfalls (2026-06-22, PR #432)

15. **Never pass a JWT token via `Authorization: Bearer` for stub-only route tests.** The auth middleware (`auth_mw.py`) validates the JWT then queries the DB for the user row — if the user doesn't exist (stub UUID) the middleware returns 403 `auth.user.not_found` BEFORE the route stub fires. ALWAYS use `app.dependency_overrides[get_current_user] = async_stub_fn` to bypass the DB lookup entirely. The `stub_apply_client` in `test_apply_price_route.py` is the canonical example.

16. **`patch()` target for catalog route service calls** is `"app.modules.catalog.router.catalog_service.patch_product"` (where `catalog_service` is the alias used in `router.py`). Using `"app.modules.catalog.service.patch_product"` patches the module but not the already-bound name in the router module — the stub never fires.

17. **`_package_images_zip` has keyword-only args** — call it as `_package_images_zip(image_refs=..., user_id=..., db=...)`. A positional-style call raises `TypeError`. Check the exact signature before calling.

18. **File-level `pytestmark = pytest.mark.asyncio` applied to sync unit tests** produces `PytestWarning` ("marked with asyncio but not async function"). For files that mix async fixtures + sync unit tests, prefer applying `pytest.mark.asyncio` on the async tests only (or accept the warning — it does NOT fail the test). All 36 Wave A tests pass despite the 7 warnings.

19. **Asserting a route is NOT mounted (flag-OFF 404)** — never use the shared `app` singleton (route may be mounted from a prior test) — build a separate minimal `FastAPI()` with only the needed routers + `ASGITransport`.

20. **plan-guard two-user fixtures** — seed free+pro users in ONE lifespan context and yield `(client, Session, free_token, pro_token)`; nested `lifespan_context` calls conflict on `app.state`.

## D2 pitfall — `get_valkey_otp()` module singleton is loop-bound (2026-06-28)

21. **`get_valkey_otp()` (and `get_valkey_broker()` etc.) return a module-level singleton client
    created in a prior event-loop.** In a combined `pytest -m integration` run, the first
    test that calls this inside an `async def` body silently binds the singleton to that loop;
    subsequent tests in a different function-scoped event-loop hit
    `RuntimeError: Event loop is closed`. The `valkey` conftest fixture (`loop_scope="function"`,
    built from `_valkey_base()` per-call, flushed before+after) is the correct replacement.
    Always use `valkey["otp"]` (the DB-0 OTP client) rather than the singleton accessor.
