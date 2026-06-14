# Hybrid-Mode CI Configuration — `svc-iam` extraction window

**Status:** ACTIVE for the Sub-Plan G strangler window (2026-06-14 → +7 green days)
**Owner:** meesell-backend-coordinator (backend lead)
**Authority:** `spec_msG_backend.md §4` (validation floor) + `SUB_PLAN_0G_iam_extraction.md §"Hybrid-mode CI config note"` + `CI_HYBRID_MODE_export.md` / `CI_HYBRID_MODE_dashboard.md` / `CI_HYBRID_MODE_pricing.md` (the equivalents this mirrors)

---

## 0. The question this answers

> Which services must be docker-composed for `svc-iam`'s HTTP-mode CI?

**Answer: NONE — and this is the SIMPLEST hybrid-CI surface of the entire program.** iam is **all-✗** in the cross-module call matrix (SUB_PLAN_0G §0.4): it has **ZERO outbound shims** (it calls no other module) AND **ZERO inbound `/internal/*`** (no service calls it). iam's contract to other services is two artifacts already in every service image — the vendored `core/auth.py` + the shared `JWT_SECRET` (A2/D7/G1) — NOT an HTTP call. So:

- **There is NO callee to compose** (unlike export's 4, pricing's 2, customer's). iam calls nobody.
- **There is NO caller to stand up either.** Every other service validates JWTs LOCALLY; none calls iam to validate a token (the G1/Risk #2 mitigation). svc-iam's HTTP-mode CI tests iam **in isolation** — OTP send/verify, refresh rotation, logout, `/me`, and the razorpay webhook against its OWN `iam`-schema DB + the shared Valkey DB 0 allowlist.

Contrast every prior wave: dashboard/export mocked their callees with `httpx.MockTransport`; pricing/customer did too. **iam mocks nothing — it has no transport to mock.** The only live substrates its richest tests touch are a real Valkey (the FE-D5 allowlist round-trip) and a real PG (the cross-schema audit round-trip), both PG/Valkey-gated.

---

## 1. How the svc-iam suite is invoked

The service is a self-contained package rooted at `backend/services/svc-iam/`:

```bash
cd backend/services/svc-iam
PYTHONPATH=. python -m pytest -v                 # 71 cases (55 specialist + 16 LEAD test_iam_extraction.py)
PYTHONPATH=. python -m ruff check app tests      # lint (clean — app + tests)
```

- `pytest.ini` is local to the service tree (own rootdir; `asyncio_mode = auto`).
- `tests/conftest.py` populates dummy-but-well-formed env BEFORE any `app.*` import (the trimmed `Settings` SystemExits on a missing REQUIRED field). It `os.environ.setdefault("DATABASE_URL", ...)` to the local PG `meesell` db and `VALKEY_URL` to local DB 0 — so where a developer/CI runner HAS connectable Valkey/PG, the LIVE round-trips exercise the real keyspace + cross-schema write; where they do not, those tests skip cleanly (`pytest.skip`), and every other assertion still runs.
- **Interpreter floor: Python 3.11/3.12.** SQLAlchemy 2.0 `Mapped[str | None]` PEP-604 unions need ≥3.10; the host's 3.9 false-fails ORM-boot. The merge gate ran on `backend/.venv` (Py 3.11.14) — the same interpreter the auth-builder used.

Test composition (16 LEAD cases — the merge-gate proof; the 55 specialist cases cover route/schema/scaffolding detail):

| Group | Count | Substrate |
|---|---|---|
| §16.G AST parity (service.py byte-identical after recursive import-strip + companion "raw twins differ" anti-vacuity) | 2 | none (AST of both service.py twins) |
| router.py import-only-delta proof | 1 | none (unified diff classifier) |
| `core/auth.py` byte-identical vendor vs monolith (R5/A2/D7) | 1 | none (byte compare) |
| FE-D5 cookie attributes (Path=/api/v1/auth, Domain, Secure/HttpOnly/SameSite=Strict) | 1 | none (source assert) |
| Allowlist key format (HMAC-with-pepper, versioned `v{N}`, NOT bare SHA-256) | 1 | none (`refresh_allowlist_key`) |
| Lua `REFRESH_ROTATE_LUA` verbatim vs §0.6 | 1 | none (constant compare) |
| **FE-D5 LIVE round-trip** (issue→validate→rotate→old-key-GONE/new-PRESENT→replay-returns-0→revoke) | 1 | live Valkey DB 0 (gated) |
| **Dual-pepper grace-window read** (entry under PREVIOUS pepper at v{N-1} found via fallback) | 1 | live Valkey DB 0 (gated) |
| **Local-JWT cross-service validation** (iam-issued JWT decodes with shared secret + vendored auth — no callback) | 1 | none (pyjwt decode) |
| ORM schema binding (User→iam, AuditEvent→public, User relationship-free) | 1 | none (`__table__.schema`) |
| **LIVE cross-schema audit round-trip** (row in public keyed to a user in iam) | 1 | live PG 16 (gated) |
| Structural guards (6 mounted iam APIRoute objects + NO /internal/* + NO celery import + flag-parity all settings reads resolve) | 3 | none (app boot + sys.modules + source scan) |
| Self-referential monotonic floor (≥13 test_ funcs in this file) | 1 | none |

> **The flag-parity guard is the MS-D regression pin, generalised.** Pricing's round-1 REJECT was a trimmed `Settings` that dropped a field a route read. iam's `test_flag_parity_every_settings_read_resolves` greps the WHOLE vendored tree for `settings.<X>` and asserts every one resolves on the trimmed Settings — the general form of the pricing-specific guard. iam passed it on the first pass (all 20 distinct reads, incl. both `MSG91_*`, resolve).

---

## 2. Where it hooks into the existing CI gates

The monolith CI (`.github/workflows/ci.yml`) defines gates 1 (unit) / 2 (smoke) / 3 (lint) — blocking — and 4 (integration) / 5 (golden_roundtrip) — advisory per MASTER_PLAN §2.1. svc-iam adds a NEW job lane that runs alongside, not inside, those monolith gates (the service tree is a separate rootdir):

- **svc-iam lint** → folds into the existing Gate-3 lane (`ruff check backend/services/svc-iam/` added to the lint step's path set). Currently CLEAN (app + tests).
- **svc-iam unit/contract** → a new job mirroring the Gate-1 shape but rooted at `backend/services/svc-iam/` with `PYTHONPATH=.`. **No callee OR caller service containers** (iam couples with nothing on the request path). The env block is the svc's trimmed set: `DATABASE_URL`, `VALKEY_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, the FE-D5 fields (`ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_PEPPER`, `REFRESH_TOKEN_PEPPER_PREVIOUS`, `REFRESH_TOKEN_PEPPER_VERSION`), `MSG91_AUTH_KEY`, `MSG91_TEMPLATE_ID`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `AUDIT_PII_SALT`, `CORS_ALLOWED_ORIGINS`, `APP_ENV` — explicitly **NO GEMINI/LANGFUSE/GCS/CELERY** (iam has no AI/storage/Celery).
- **Live-substrate gates (optional, Valkey + PG backed).** If the svc-iam CI lane provisions a Valkey service container (for DB 0) and/or a PG 16 service container (with the `iam` schema + `public.audit_events`) and points `VALKEY_URL`/`DATABASE_URL` at them, the FE-D5 round-trip + dual-pepper read + cross-schema audit tests run LIVE. Where no Valkey/PG is provisioned, those three skip — the contract is still fully covered by the unconditional AST/vendor/cookie/key/Lua/binding/structural/flag assertions. The merge gate ran ALL of them LIVE (local Valkey PONG + local PG `meesell`).

> **Infra dependency (handoff_msG_infra):** iam's Postgres need is an `iam_user` role owning the `iam` schema (where `users` now lives), plus `INSERT ON public.audit_events` for the cross-schema audit write (the verify-OTP audit path; the webhook path logs rather than writes, audit_event_id=0). The one NEW Secret Manager entry is `dev-iam-db-password` (the `iam_user` password). The peppers (`refresh-token-pepper`), `razorpay-webhook-secret`, and the shared `JWT_SECRET` already exist. CI's optional Valkey+PG containers exercise the allowlist + cross-schema paths; deploy needs `dev-iam-db-password` populated.

---

## 3. Strangler-window note

During the green window both trees coexist:
- The monolith's in-process `iam` module + its tests stay live (the monolith Gate-1/2/3 still run `tests/modules/iam/` + `tests/integration/test_iam_*`). **`core/auth.py` is NEVER deleted from the monolith — it stays the vendored source-of-truth every service imports.**
- svc-iam's suite runs in parallel.

The monolith `def test_` count must stay MONOTONIC (≥ baseline 705 as re-counted at develop tip `ebb700e`) for the whole window — the extraction ADDS the svc-iam suite, removes none from the monolith until cutover. At cutover (post-window, a SEPARATE founder gate), the monolith iam module + tests are deleted in one strangler commit and the `main.py:114` `include_router(iam_router)` mount is removed — that is the ONLY sanctioned decrease, and `core/auth.py` survives it. Until then, **the monolith `/api/v1/auth/*` endpoints stay LIVE and authoritative** — Traefik routes `/api/v1/auth/*` + `/api/v1/webhooks/razorpay` to svc-iam only at the cutover flip, which is NOT taken at this gate.

---

## 4. Callees / callers docker-composed for iam's CI: NONE (both directions)

| Direction | Surface | Status | Composed in CI? |
|---|---|---|---|
| Outbound (iam → other) | NONE — iam is all-✗, calls no module (§0.4) | n/a | NO — nothing to compose |
| Inbound (other → iam) | NONE — no service calls iam; JWT validation is LOCAL via vendored `core/auth.py` + shared `JWT_SECRET` (G1/A2/D7) | every service self-validates | NO — nothing to compose |

iam is the ONLY extraction with no shim contract in either direction. There is no `SHIM_CONTRACT_iam_callees.md` and there never will be — its absence is intentional (§0.4) and is stated explicitly so a future reader does not mistake it for an omission.
