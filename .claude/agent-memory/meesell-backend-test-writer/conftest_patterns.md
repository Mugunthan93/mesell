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
