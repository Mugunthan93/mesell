---
name: meesell-auth-and-billing
description: >-
  MeeSell's canonical conventions for authentication (MSG91 phone OTP, Google Sign-In,
  PyJWT issuance/refresh/revocation) and Razorpay subscription billing. Use this skill
  WHENEVER you are creating or editing anything touching login, OTP, JWT/tokens, refresh
  cookies, logout/revocation, the dual-identity user model, auth/rate-limit/plan-guard
  middleware, DPDP consent, or Razorpay subscriptions/webhooks in the MeeSell backend
  (backend/app/services/otp_service.py, backend/app/middleware/, auth routers) — even if
  the user only says "fix login", "the OTP isn't working", "users get logged out", "add
  Google sign-in", "gate this by plan", or "wire up payments" without naming the provider.
  Do NOT use it for unrelated route shapes (defer to meesell-fastapi-router) or table DDL
  (defer to meesell-alembic-migration) — call those skills for the mechanics, this one for
  the auth/billing rules.
---

# MeeSell Auth & Billing Conventions

These are the locked rules for identity, sessions, and payments in MeeSell. They exist so
no token ever leaks, no session survives a logout, no seller is charged or gated wrongly,
and the dual phone/Google identity model stays consistent. They derive from `CLAUDE.md`
Key Decisions #5 (+ 2026-06-18 google-auth amendment), #14 (+ FE-D5 amendment), #15, and
the locked auth docs — which win over any other guidance.

## The non-negotiables (and why each matters)

- **MSG91 OTP + PyJWT, never GoTrue / Supabase Auth (Decision #14).** We own the OTP flow
  and issue our own JWTs from FastAPI. The trimmed self-hosted Supabase is Postgres ONLY —
  GoTrue/Realtime/Storage stay disabled (Decision #15). Don't introduce an external auth
  dependency.

- **Access token in memory, refresh token in an HttpOnly cookie — never localStorage
  (Decision #14 + FE-D5 amendment).** The short-lived access JWT is held in-memory by the
  frontend. The refresh token lives in an `HttpOnly; Secure; SameSite=Strict` cookie owned
  by the backend. localStorage is an XSS exfiltration vector — nothing auth-related goes there.

- **Server-side revocation via a Valkey allowlist on logout.** Refresh tokens are tracked
  in a Valkey allowlist keyed in an HMAC-with-pepper keyspace; logout removes the entry so
  the token is dead server-side immediately. A stateless-only JWT that can't be revoked is
  not acceptable for a paid product.

- **Dual identity: phone OR Google (Decision #5 amendment).** A user may have phone only,
  Google only (`email` + `google_sub`, `phone = NULL`), or both. Account-linking is
  AUTO-LINK on a Google `email_verified` match: `google_sub` match → login; else verified
  `email` match → link `google_sub` onto the existing user; else create a Google-only user;
  return 409 if the email belongs to a different `google_sub`. The phone-OTP path is unchanged.

- **Google verify is feature-flag gated.** `POST /api/v1/auth/google/verify` lives in the
  `iam` module behind `FEATURE_GOOGLE_AUTH_ENABLED` (default `False`). When off, the route is
  NOT mounted (OpenAPI surface stays at the locked count). Never mount it unconditionally.

- **Every Valkey key has a TTL and a namespaced name.** OTP/session/rate-limit keys live in
  Valkey DB 0, named `{namespace}:{entity}:{id}` (e.g. `otp:+919876543210`,
  `ratelimit:user123:generate:60`). A key without a TTL is a leak.

- **DPDP consent is captured at signup.** India's DPDP Act requires explicit consent; record
  it on the user/consent row, don't treat it as implied.

- **Structured logging, never log a token, OTP, or secret.** `logging.getLogger(__name__)`;
  mask anything sensitive. Logs are aggregated centrally.

## OTP flow (MSG91)

```python
# Request: generate a 6-digit code, store hashed in Valkey with a short TTL, send via MSG91.
OTP_TTL_SECONDS = 300  # 5 min
await valkey.setex(f"otp:{phone}", OTP_TTL_SECONDS, hash_otp(code))
await msg91.send_sms(phone, code)

# Verify: compare, then issue tokens. In DEV ONLY, bypass code "000000" is accepted
# (local-dev convenience) — this MUST be disabled outside the dev namespace.
if settings.ENV == "dev" and code == "000000":
    pass  # dev bypass
else:
    stored = await valkey.get(f"otp:{phone}")
    if stored is None or not verify_otp(code, stored):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")
await valkey.delete(f"otp:{phone}")  # one-time use
```

Never let an OTP be reused — delete on success. Never extend the TTL on retry without a cap.

## Token issuance, refresh, revocation

```python
# On successful auth: short access JWT (in-memory on FE) + refresh token (HttpOnly cookie).
access = issue_access_jwt(user_id=user.id, ttl=settings.ACCESS_TTL)      # minutes
refresh = issue_refresh_token(user_id=user.id, ttl=settings.REFRESH_TTL)  # days
await valkey.setex(allowlist_key(refresh), settings.REFRESH_TTL, "1")     # HMAC-pepper keyspace

response.set_cookie(
    "refresh_token", refresh,
    httponly=True, secure=True, samesite="strict", max_age=settings.REFRESH_TTL,
)
return {"access_token": access}  # access token NEVER set as a cookie; returned for in-memory use

# Refresh: only honour a token still present in the allowlist (rotation-safe).
if not await valkey.exists(allowlist_key(presented_refresh)):
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session expired")

# Logout: delete the allowlist entry -> token is dead server-side.
await valkey.delete(allowlist_key(presented_refresh))
response.delete_cookie("refresh_token")
```

Beware refresh **stampedes** — the frontend interceptor must single-flight refreshes; a
multi-source race can hammer the endpoint into a 401 cascade and force-logout the user.

## Middleware

- **`auth.py`** — validates the access JWT, loads the `User`, exposes `get_current_user`.
- **`rate_limit.py`** — Valkey sliding-window limiter; key `ratelimit:{subject}:{action}:{window}`.
- **`plan_guard.py`** — enforces ₹499–1,999 plan limits (catalog count, generations/month).
  Exceeding a limit returns a clear 402/403 with `{"detail": ...}`, never a silent failure.

## Razorpay subscriptions

```python
# Create: use Razorpay Subscriptions (not one-off orders) — MeeSell is recurring SaaS.
sub = razorpay.subscription.create({"plan_id": plan_id, "customer_notify": 1, ...})

# Webhook: ALWAYS verify the signature before trusting the event, and be idempotent —
# Razorpay retries, so process each event id at most once.
verify_razorpay_signature(raw_body, headers["X-Razorpay-Signature"], settings.RAZORPAY_WEBHOOK_SECRET)
if await already_processed(event["id"]):
    return {"status": "ok"}  # idempotent no-op
await apply_subscription_event(event)
await mark_processed(event["id"])
```

A webhook handler that skips signature verification or isn't idempotent is a billing bug —
treat both as mandatory. Secrets (`RAZORPAY_KEY_ID/SECRET`, `RAZORPAY_WEBHOOK_SECRET`,
`MSG91_AUTH_KEY`, `JWT_SECRET`) come from env/K8s Secrets, never hard-coded.

## Quick checklist before you finish an auth or billing task

- [ ] OTP via MSG91; code hashed in Valkey with a TTL; one-time use; dev `000000` bypass dev-only
- [ ] Access JWT in-memory; refresh token in `HttpOnly; Secure; SameSite=Strict` cookie
- [ ] No token/OTP/secret in localStorage or logs
- [ ] Refresh honoured only if present in the Valkey allowlist; logout deletes it
- [ ] Dual-identity rules respected; Google verify behind `FEATURE_GOOGLE_AUTH_ENABLED`
- [ ] Every Valkey key namespaced + TTL'd (DB 0)
- [ ] `plan_guard` returns a clear 402/403 on limit; `rate_limit` sliding window applied
- [ ] DPDP consent captured at signup
- [ ] Razorpay = Subscriptions; webhook signature verified + idempotent
- [ ] Secrets from env/K8s Secrets, never inline
