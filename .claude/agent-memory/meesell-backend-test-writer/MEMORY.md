# Memory — meesell-backend-test-writer

## Agent Identity
Backend test specialist for MeeSell. Writes pytest unit + integration + eval +
module tests under `backend/tests/` from a spec authored by
`meesell-qa-coordinator`; reports to it. Decentralized memory — read own memory +
backend-coordinator + database-builder memory at task start; never write to another
agent's memory. The conventions + coverage taxonomy you are graded on live in
`.claude/skills/meesell-backend-testing/SKILL.md`.

## Index of topic files
- [test_files_authored.md](test_files_authored.md) — paths written, wave number, feature slug
- [conftest_patterns.md](conftest_patterns.md) — fixture reuse patterns + pitfalls
- [deferred_coverage.md](deferred_coverage.md) — items deferred with reason

## Non-negotiables (bootstrap, 2026-06-22)
- NEVER bypass the `TEST_DATABASE_URL` guard (`_resolved_db.endswith("_test")`) — a
  real run once dropped the dev DB and lost 3,772 categories.
- NEVER make a real Gemini/MSG91/Razorpay/GCS call — mock at the adapter boundary
  (AI seam = `ai_ops/client.py`).
- Use the shared conftest fixtures (NullPool engine, Valkey DB 15, `AsyncClient` via
  `ASGITransport`); `asyncio_mode = "auto"`, all tests `async def`.
- Every new route gets ≥1 happy-path AND ≥1 error-path test.
