---
name: meesell-backend-testing
description: >-
  MeeSell's conventions and coverage taxonomy for writing pytest tests against the
  FastAPI backend. Use this skill WHENEVER you are writing or editing backend tests
  (anything under backend/tests/), adding a conftest fixture, mocking a vendor
  adapter (Gemini / MSG91 / Razorpay / GCS) in a test, or the user says "write
  tests for the backend", "add unit/integration tests", "cover this route", or
  "QA the backend" — even if they don't say "pytest" explicitly. Apply it before
  authoring any backend test so the TEST_DATABASE_URL safety guard is never
  bypassed and no test makes a real external call. Do NOT use it for Angular specs
  (defer to meesell-frontend-testing) or Playwright E2E (defer to
  meesell-e2e-testing).
---

# MeeSell Backend Testing — Conventions & Coverage Taxonomy

These are the locked rules for writing pytest tests for the MeeSell backend
(Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, Celery,
Valkey 8, PostgreSQL 16). They exist so a test never drops the dev database,
never makes a real Gemini/MSG91/Razorpay/GCS call, and never passes while
asserting nothing. They derive from `CLAUDE.md` (Python conventions + Decisions)
and `BACKEND_ARCHITECTURE.md`, which win if anything here disagrees.

## Conventions

- **`TEST_DATABASE_URL` points at a `*_test` database — the conftest safety guard
  (`_resolved_db.endswith("_test")`) must NEVER be bypassed.** A real session
  once `drop_all`'d the dev DB and lost 3,772 seeded categories. The guard is the
  thing standing between you and that. If a test needs the live DB, it is the
  wrong test.
- **Use the shared `conftest.py` fixtures**, do not hand-roll your own engine:
  - ephemeral DB engine on `NullPool` (one connection per test, no pool reuse),
  - in-memory / dedicated Valkey on **DB 15** (never the app DBs 0–3),
  - FastAPI `AsyncClient` via `ASGITransport` (in-process, no network socket).
- **No real external calls.** Mock the vendor at the **adapter boundary**, not
  deep inside a service: `GeminiAdapter`, `MSG91Adapter`, `RazorpayAdapter`,
  `GCSAdapter`. The AI seam is `ai_ops/client.py` — mock there, never reach into
  `adapters/gemini.py` from a service test.
- **`pytest-asyncio` with `asyncio_mode = "auto"`** — every test function is
  `async def`. (A missing/incorrect event-loop fixture is exactly how the
  catalog-form "no current event loop" gate-failures happened — use the shared
  async fixtures, don't invent loop handling.)
- **File placement** mirrors the module layout:
  - `tests/unit/` — models, schemas, utils (no DB, no HTTP),
  - `tests/integration/` — route flows, cross-module flows (DB + AsyncClient),
  - `tests/modules/{domain}/` — domain-scoped suites,
  - `tests/eval/` — AI golden fixtures.
- **AAA per test** (Arrange → Act → Assert), one logical assertion per test. A
  test that asserts nothing (no `assert`, or only `assert True`) is a defect —
  the merge gate rejects it.
- **Determinism.** Seed via direct ORM INSERT helpers (no live OTP flow); mint
  JWTs with `app.core.auth.issue_access_token(user_id, plan)`; never depend on
  wall-clock time, network, or test execution order.
- **Run evidence.** Paste the `pytest` invocation + summary line in the PR.

## Coverage Taxonomy

The mandatory test cases per domain. "Happy path" is never enough on its own —
every route needs at least one error path too (the recurring builder omission).

| Domain | Mandatory test cases |
|---|---|
| IAM | OTP send/verify happy path; OTP bypass `000000` accepted in dev, rejected in prod; JWT issuance + rotation; refresh cookie HttpOnly + Secure + SameSite=Strict attrs; plan-guard rejects on plan limit; rate-limit sliding window triggers 429; Google verify + auto-link on `email_verified` match; Google verify + 409 on `google_sub` collision |
| Catalog | CRUD happy path; dependency rules (SKU requires catalog); autofill AI call mocked returns expected shape; quality-gate score thresholds (pass / fail boundary) |
| Category | Browse tree returns nodes; schema shape per category id; smart-picker top-3 contract (returns exactly 3 with confidence scores); ETag cache hit returns 304 |
| Pricing | Apply-price P&L calc (commission = 0%, shipping = constant per category, offline mode); negative-margin detection |
| Export | Full pipeline happy path (catalog → ZIP); blocked-by-failed-precheck returns 422; round-trip validation failure surfaces a field error; ZIP structure contains the expected files |
| Billing | Razorpay webhook signature verify (valid + tampered); subscription state transitions (created → active → cancelled); mock-mode passthrough for dev |
| AI Ops | Budget-cap hard-stop raises at the ceiling; cost tracker increments per call; guardrail rejects disallowed content; prompt-registry key lookup returns the pinned template |

## Quick checklist before finishing a backend-test task

- [ ] `TEST_DATABASE_URL` ends with `_test`; conftest guard untouched
- [ ] Shared fixtures used (NullPool engine, Valkey DB 15, ASGITransport client)
- [ ] Every external vendor mocked at the adapter boundary; zero real calls
- [ ] Every new route has ≥1 happy-path AND ≥1 error-path test
- [ ] AAA structure; no assertion-free tests
- [ ] `pytest` output pasted in the PR description
