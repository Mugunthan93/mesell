# Sub-Session Prompt: §7 Module `iam`
# Wave 2 of 10 — CONSTRUCTION
# Specialist agent: meesell-auth-builder (sole owner, FIRST DISPATCH TARGET per §7 + FE-D5 ratification)
# Renames session to: meesell-backend-construction-7-iam-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §7 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-auth-builder agent operating in a dedicated construction sub-session for MeeSell §7 (Module `iam`). You are the FIRST DISPATCH TARGET of the construction phase — every authenticated route across §8-§14 needs `get_current_user` and the iam module's auth contract.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §7 Module `iam` — 4 V1 auth endpoints + /me + razorpay webhook + Lua EVAL rotation + HMAC-pepper allowlist
- Specialist agent: meesell-auth-builder (SOLE OWNER per §7 lock)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-7-iam-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §7 — A through L (esp. §7.B 6 endpoint surfaces incl. 4 V1 contract + /me + razorpay webhook; §7.B.1 otp/send with 3/h rate limit on phone; §7.B.2 otp/verify with HMAC-pepper allowlist write per FE-D5 amendment; §7.B.3 refresh per FE-D5 with Lua EVAL rotation; §7.B.4 logout with cookie clear + Lua DEL; §7.B.5 /me JWT introspection; §7.B.6 razorpay capture with HMAC sync verify; §7.C 6-method service surface; §7.D 4-method repository; §7.G 8 IamError subclasses; §7.J 4 unit + 3 integration test classes).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0.C (27-endpoint contract incl. 2 new auth endpoints from FE-D5), §0.F (D1-D4 founder rulings), §4 (core/auth.py + FE-D5 amendment block), §5.D (JWT env vars incl. `ACCESS_TOKEN_TTL_SECONDS` 900/60/30, `REFRESH_TOKEN_TTL_SECONDS` 604800/300/120, `REFRESH_TOKEN_PEPPER` Secret Manager ref, `JWT_EXPIRY_DAYS` DEPRECATED), §6.C (msg91 contract — send_otp returns Msg91Response w/ success=False on failure NOT raise), §6.E (razorpay verify_webhook_signature sync).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §10.3 (JWT claims `{sub, exp, plan}`), §11.3 (audit), §11.7 (FE-D5 amendment paragraph). Cited; not amended.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (Decision 14 incl. FE-D5 amendment final clause).

5. `.claude/agents/meesell-auth-builder.md` (own spec).

6. `.claude/agent-memory/meesell-auth-builder/MEMORY.md` (prior session memory).

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm §5, §4, §5A, §6, §6A CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline. NOTE: Current `backend/app/routers/auth.py` exists from session 2 cleanup but mounts only `otp/send` + `otp/verify` + `/me` — refactor into the new `modules/iam/` shape during this construction. The §3.C per-module subtree is the target layout.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C + §7:

```
backend/app/modules/iam/
├── __init__.py
├── router.py            # FastAPI APIRouter; 6 endpoint signatures only (4 V1 + /me + razorpay webhook)
├── service.py           # 6-method service surface; PUBLIC interface
├── repository.py        # 4-method repository; PRIVATE; uses scope_to_user for users table writes (the user IS the tenant)
├── schemas.py           # Pydantic v2 request/response models
├── domain.py            # value objects (CurrentUser, RefreshTokenPayload)
└── exceptions.py        # 8 IamError subclasses per §7.G
```

Plus:
- `backend/app/core/auth.py` — `get_current_user` FastAPI dep already constructed in §4 (Wave 1 step 2); §7 CONSUMES it but does NOT redefine it.
- `backend/app/core/middleware/auth_mw.py` — already constructed in §4; consumed.
- `backend/app/i18n/messages_en.py` — already constructed in §5A with 8 iam-specific message IDs declared. §7 verifies the English strings are correct for: `validation.phone.invalid_format`, `validation.otp.invalid_format`, `validation.webhook.malformed_payload`, `auth.otp_invalid`, `auth.otp_attempts_exceeded`, `auth.msg91_unavailable`, `auth.refresh_invalid`, `auth.webhook_signature_invalid`. The 3 `auth.token_*` message IDs are owned by `core/auth.py`.
- `backend/app/main.py` — mount `iam_router` from `modules/iam/router.py`. Remove the legacy `auth_router` mount from `routers/auth.py` if still present; migrate any logic into the new `modules/iam/`.

Locked invariants:
- Access JWT shape: `{sub: user_id, exp, plan}` per §4.B + `MVP_ARCH §10.3`. Held in-memory by frontend (FE-D5).
- Refresh token: opaque, `secrets.token_urlsafe(48)`. HttpOnly + Secure + SameSite=Strict cookie. `Path=/api/v1/auth` (NOT `/auth`). `Domain=.mesell.xyz`.
- Refresh allowlist keyspace in Valkey DB 0: `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}`. HMAC-with-pepper (NOT bare SHA-256).
- Rotation via Lua script EVAL (atomic single-round-trip CAS — NOT MULTI/EXEC). Lua script SCRIPT LOAD once + EVALSHA thereafter + EVAL fallback on NOSCRIPT.
- `secrets.compare_digest()` for constant-time comparison.
- Rate limits: `otp_send` 3/h key=phone; `otp_verify` 10/h key=phone; `auth_refresh` 60/h key=refresh_cookie_user_id; `/me` + `/webhooks/razorpay` per-IP fallback only (no `@rate_limit` decorator); `/logout` no rate limit (idempotent).
- Audit events: `verify_otp`, `refresh`, `logout` — direct ORM write inside service (locked exception to audit_mw post-commit pattern per §6A.D + §7.I; the cookie-resolved `user_id` is known only inside the service BEFORE the `DEL`, so middleware cannot capture it). `/me` emits NO audit event.

Construction protocol:

1. **Tests first** per §7.J test plan (4 unit + 3 integration):

   **Unit** (`backend/tests/modules/iam/`):
   - `test_refresh_allowlist_write_on_verify_success` — verify path writes `cache:refresh:{hmac}` to Valkey DB 0 with correct JSON payload + TTL = `REFRESH_TOKEN_TTL_SECONDS`.
   - `test_refresh_validation_4_cases` — valid (rotation succeeds), expired (Lua returns nil, 401), revoked (post-logout, Lua returns nil, 401), already-rotated (replay attack: old cookie after refresh, Lua returns nil, 401).
   - `test_logout_idempotency` — first call DELs allowlist entry + clears cookie + writes audit; second call returns 204 + clears cookie + NO audit row (cookie already gone, nothing to log).
   - `test_constant_time_comparison_regression` — `secrets.compare_digest` used for OTP hash compare AND for refresh-token lookup (Valkey key is HMAC-based, but the Lua script's existence check is constant-time at the Redis level; test guards against future refactors reintroducing `==`).

   **Integration** (`backend/tests/integration/test_iam_*.py`):
   - `test_full_silent_refresh_flow` — verify → short wait (well under `ACCESS_TOKEN_TTL_SECONDS` staging=60s) → refresh → old access still valid until its `exp` (the new access has fresh `exp`; old isn't revoked — access has no allowlist, only refresh does).
   - `test_logout_revocation` — verify → logout → refresh → 401 `auth.refresh_invalid`.
   - `test_replay_attack_mitigation` — verify → refresh → save old refresh cookie locally in test → attempt reuse → 401 (rotation invalidated it during refresh step).

   Fixtures: real Valkey (DB 0) + real Postgres via dev tunnel; mocked MSG91 adapter (avoid burning OTP credits in CI); mocked Razorpay webhook generator (signs fixture payload with test secret).

2. **Implementation** per §7.B-§7.G with locked signatures.

3. **Acceptance**: tests pass; ruff clean; boot smoke PASS (route count assertion increments to absorb the 4 new iam routes + /me + webhook); schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT use MULTI/EXEC for rotation — Lua EVAL is the locked atomic mechanism.
- DO NOT use bare SHA-256 for allowlist hashing — HMAC-with-pepper per §4.B FE-D5 amendment.
- DO NOT use `==` for token comparison — `secrets.compare_digest()` only.
- DO NOT set cookie `Path=/auth` — locked to `Path=/api/v1/auth`.
- DO NOT store refresh token in JWT claims — refresh is opaque, lives only in the HttpOnly cookie + Valkey allowlist.
- DO NOT emit audit_events via middleware for verify_otp/refresh/logout — direct ORM write per the documented §7.I exception.
- DO NOT call `adapters.gemini` (iam has no AI).
- DO NOT call `adapters.gcs` (iam has no blob storage).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted: `meesell-auth-builder` works SOLO on iam per §7 lock. No other dispatch.

You ARE NOT permitted: any other dispatch (no services-builder, no routes-builder, no database-builder for this section).

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §7)
═══════════════════════════════════════════════════════════════

`refresh-token-pepper` — required for HMAC allowlist key construction. NOT populated during this dispatch; documented as Secret Manager ref in `Settings.REFRESH_TOKEN_PEPPER`. Populated by §20 deployment construction. Coordinate with `meesell-infra-builder` memory BEFORE constructing the verify/refresh/logout flows — if the secret container is not yet provisioned, the integration tests cannot run against real Valkey. If `meesell-infra-builder` confirms staging/dev workaround is available (e.g. an env-var injection for dev), proceed; otherwise escalate to master.

`razorpay-webhook-secret` — required for HMAC verify on `/webhooks/razorpay`. Same posture: Settings ref, populated by §20, dev workaround via env-var.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

Per §7.J test plan + locked invariants:

1. 4 V1 contract endpoints mounted: `POST /api/v1/auth/otp/send`, `POST /api/v1/auth/otp/verify`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`. Plus `/me` and `POST /api/v1/webhooks/razorpay`.
2. Access JWT shape `{sub, exp, plan}` only — no `refresh_token` claim.
3. Refresh allowlist keyspace HMAC-with-pepper — verified by inspecting `iam/service.py` for `hmac.new(..., settings.REFRESH_TOKEN_PEPPER, ...)` usage.
4. Lua rotation script registered via `SCRIPT LOAD` once; EVALSHA used thereafter; EVAL fallback on NOSCRIPT.
5. `secrets.compare_digest()` used for all token comparisons.
6. Cookie shape: `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Domain=.mesell.xyz`.
7. Rate limits per locked tuple: 3/h send, 10/h verify, 60/h refresh, no decorator on /me or webhook, no limit on logout.
8. 8 iam exception subclasses per §7.G all carry `validation_message_id` from §5A.
9. Direct ORM audit writes for verify_otp / refresh / logout; no middleware-emitted audit on those.
10. 4 unit + 3 integration tests pass per §7.J.

Plus universal: all tests pass; ruff clean; boot + schema smoke PASS (route count incremented); memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update `.claude/agent-memory/meesell-auth-builder/MEMORY.md`.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §7 iam CONSTRUCTED ===
   Files created: modules/iam/{__init__.py, router.py, service.py, repository.py, schemas.py, domain.py, exceptions.py}; main.py mount updated
   Tests added: 4 unit + 3 integration test classes
   Decisions made: <list>
   Hand-offs: §8 customer through §14 export (consume core/auth.get_current_user dep; depend on iam being live for any authenticated route)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Lua script behavior ambiguous (e.g. expired vs revoked — both return nil, what differentiates the 401 message?).
- Pepper secret not provisionable in dev (escalate to coordinate with infra-builder).
- Cookie domain configuration on staging conflicts with .mesell.xyz (escalate).
- MSG91 sandbox quota exhausted during integration test development.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-7-iam-1`
2. Read REQUIRED READING.
3. Confirm Wave 1 CONSTRUCTED (shared/, core/, i18n/, adapters/, ai_ops/).
4. Report "Context loaded. Ready to begin §7 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 2 of 10
- **Sequential dependency:** Wave 1 complete (§5, §4, §5A, §6, §6A).
- **Parallel-safe?:** No — Wave 2 is single-section.
- **Expected duration estimate:** ~12-16 hours (auth flows + Lua rotation + integration tests + secret coordination).
- **Acceptance verification by master:** (1) `grep -rn "MULTI\|EXEC" backend/app/modules/iam/` returns nothing (Lua only); (2) `grep -rn "hashlib.sha256" backend/app/modules/iam/` returns nothing (must be HMAC); (3) `grep -rn "compare_digest" backend/app/modules/iam/` confirms constant-time used; (4) `Path=/api/v1/auth` present in cookie set call (not `/auth`); (5) 4 unit + 3 integration tests PASS; (6) boot smoke PASS with new route count; (7) STATUS_BACKEND.md UPDATE block present.
