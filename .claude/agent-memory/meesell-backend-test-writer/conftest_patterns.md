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
