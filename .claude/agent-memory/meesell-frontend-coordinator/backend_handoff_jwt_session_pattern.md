---
name: backend-handoff-jwt-session-pattern
description: Deltas the founder must take to the meesell-backend-coordinator session 2026-06-05 to implement the FE-D5+FE-D6 split-token + server-side-revocation auth pattern
metadata:
  type: project
---

# Backend handoff — JWT session pattern (founder-locked FE-D5 + FE-D6, 2026-06-05)

## Context

The frontend coordinator surfaced JWT storage as a Section 1 review concern. The founder rejected the original `localStorage` plan and locked the **split-token + server-side-revocation** pattern. The frontend doc (`docs/FRONTEND_ARCHITECTURE.md`) was updated immediately (FE-D5 + FE-D6 added to §0.F, §1.F rewritten, §4 expanded to 4 interceptors, §22A risk 4 amended, §23 endpoints expanded). The frontend Section 1 stays DRAFT until the backend coordinator ratifies these deltas.

The founder will take this memo to the backend coordinator session.

## The pattern (one paragraph)

Access JWT is short-lived (15 min prod default, env-overridable), Bearer-attached, held in-memory only on the frontend. Refresh token is long-lived (7 day prod default), opaque, delivered as `HttpOnly; Secure; SameSite=Strict; Path=/auth` cookie, allowlist-tracked in Valkey DB 0 with **server-side revocation on logout**. Refresh rotates on every use (replay-attack mitigation). Frontend never touches the refresh token (cannot — HttpOnly).

## What changes in BACKEND_ARCHITECTURE.md

### 1. Section §0.C — endpoint contract count

```diff
- The founder ruling 2026-06-05 (recorded in coordinator memory, session 2 close-out) is that
- §3 + §7.7 + §11.6 = 25 endpoints is the authoritative contract; §11.1's "20" is dead.
+ The founder ruling 2026-06-05 (recorded in coordinator memory, session 2 close-out) is that
+ §3 + §7.7 + §11.6 + the 2 FE-D5 auth endpoints = 27 endpoints is the authoritative contract.
+ The 2 new endpoints (POST /auth/refresh and POST /auth/logout) are added per the frontend
+ FE-D5 founder ruling 2026-06-05 (split-token pattern with HttpOnly refresh cookie and
+ server-side Valkey allowlist with logout revocation).
```

### 2. Section §7 (`iam` module) — adds 2 endpoints, modifies 1

**New: `POST /api/v1/auth/refresh`**
- Reads `refresh_token` cookie (browser auto-attaches, Path=/auth)
- Validates against Valkey allowlist `cache:refresh:{sha256(token)}`
- If valid:
  - Rotates: `DEL cache:refresh:{sha256(old)}` + `SET cache:refresh:{sha256(new)} <user_id> EX REFRESH_TOKEN_TTL_SECONDS`
  - Issues new access JWT with TTL = `ACCESS_TOKEN_TTL_SECONDS` env var (prod: 900)
  - Returns `{access_token, expires_in: 900, token_type: "bearer"}`
  - Sets new refresh cookie via `Set-Cookie: refresh_token=<new>; HttpOnly; Secure; SameSite=Strict; Path=/auth; Max-Age=<REFRESH_TOKEN_TTL_SECONDS>`
- If invalid/expired/revoked → `401 Unauthorized`, clear cookie (`Max-Age=0`)
- No body in request — the cookie is the sole input
- Rate limit: 60/h/user (sliding window, Valkey DB 0)
- No JWT required to call this endpoint (refresh cookie IS the auth)

**New: `POST /api/v1/auth/logout`**
- Reads `refresh_token` cookie
- `DEL cache:refresh:{sha256(token)}` from Valkey DB 0
- Returns `204 No Content`
- Sets `Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Strict; Path=/auth; Max-Age=0` to clear browser cookie
- Idempotent — calling twice returns 204 both times
- No body, no JWT required (cookie is auth)

**Modified: `POST /api/v1/auth/otp/verify`** — response shape changes
- Body: `{access_token: <JWT>, expires_in: 900, token_type: "bearer"}` (was `expires_in: 604800`)
- Response header: `Set-Cookie: refresh_token=<opaque>; HttpOnly; Secure; SameSite=Strict; Path=/auth; Max-Age=604800`
- Refresh token is opaque (`secrets.token_urlsafe(48)`), not a JWT — JWTs in cookies are an anti-pattern (size, no rotation)
- On verify success: write `cache:refresh:{sha256(refresh_token)}` to Valkey DB 0 with value `{"user_id": <uuid>, "issued_at": <ts>, "ip": <addr>}` and TTL = REFRESH_TOKEN_TTL_SECONDS

### 3. Section §15 (Cross-Cutting Systems Walkthrough) — adds session management subsection

**New subsection: Session management (refresh-token allowlist)**
- Valkey DB 0 keyspace `cache:refresh:{sha256(token)}` is the refresh allowlist
- `secrets.compare_digest()` (NOT `==`) for token comparison — constant-time, prevents timing attacks
- Storing sha256 of the token (not the token itself) so a Valkey breach does not expose live refresh tokens
- Rotation on every refresh — old hash deleted, new hash stored in single MULTI/EXEC transaction
- Logout deletes the hash → next refresh attempt with the cookie returns 401 (server-side revoked)
- TTL on the Valkey key matches `REFRESH_TOKEN_TTL_SECONDS` — natural expiry without cron sweep

**New subsection: CSRF posture (V1)**
- Refresh cookie is `SameSite=Strict` → cross-site requests do not send it → CSRF on `/auth/refresh` and `/auth/logout` is impossible from another origin
- Access token is in `Authorization: Bearer` header → not CSRF-vulnerable (browsers don't auto-attach custom headers from other origins)
- All other endpoints use the Bearer header → no CSRF surface
- V1: NO CSRF token middleware needed
- V1.5 (when we add HttpOnly session cookies for any reason) → revisit

### 4. Env vars — new

Add to backend env contract (`backend/.env.example` and Secret Manager):

```bash
# Access JWT lifetime — seconds
ACCESS_TOKEN_TTL_SECONDS=900       # prod: 900 (15 min)
                                    # staging: 60 (test silent refresh)
                                    # dev: 30 (test refresh + interceptor loop)

# Refresh token lifetime — seconds
REFRESH_TOKEN_TTL_SECONDS=604800   # prod: 604800 (7 days)
                                    # staging: 300 (5 min — test refresh expiry path)
                                    # dev: 120 (2 min — test refresh expiry path)
```

These are env-overridable so dev/staging can exercise the refresh path without waiting in real time. **Frontend has no env coupling** — it reads `expires_in` from each response and trusts it.

### 5. Documentation amendments (V1_FEATURE_SPEC.md + MVP_ARCHITECTURE.md)

**V1_FEATURE_SPEC.md §F1 step 4** — currently says:
> "Frontend stores JWT in localStorage, attaches as `Authorization: Bearer` on every call"

Amend to:
> "Frontend holds the access JWT in memory (signal); refresh token delivered as HttpOnly+Secure+SameSite=Strict cookie owned by backend. Frontend attaches `Authorization: Bearer <access>` on every call. On access expiry, RefreshInterceptor silently refreshes via `POST /auth/refresh` (refresh cookie auto-sent). Server-side revocation on logout via Valkey allowlist DEL."

**V1_FEATURE_SPEC.md §F1 acceptance criteria** — currently says:
> "JWT valid for 7 days, refreshed silently on call within 24 h of expiry"

Amend to:
> "Access JWT valid for 15 min (prod default; env-overridable). Refresh token valid for 7 days; rotated on every use; revoked on logout (server-side Valkey allowlist DEL). Frontend's RefreshInterceptor silently refreshes within 30s of access-token expiry."

**MVP_ARCHITECTURE.md §11.7** — JWT claims unchanged (`{sub, exp, plan}`); add a paragraph noting "the access-token TTL is env-driven (ACCESS_TOKEN_TTL_SECONDS); the refresh token is opaque and lives in Valkey DB 0 not in any JWT".

**CLAUDE.md Decision 14** — currently:
> "MSG91 OTP + JWT (PyJWT), not GoTrue / Supabase Auth — full control over OTP flow, no external auth dependency, JWT issued by our own FastAPI"

This is still accurate — MSG91 + PyJWT remain. Amend to add a final clause:
> "Access JWT held in-memory by the frontend; refresh token in HttpOnly+Secure+SameSite=Strict cookie owned by backend; server-side revocation via Valkey allowlist on logout. No tokens in localStorage."

### 6. CORS — verify the Set-Cookie path works cross-subdomain

Frontend is served from `dev.mesell.xyz` (and `www.mesell.xyz` in prod). Backend is at `api.mesell.xyz`. CORS already allows cross-subdomain (per `INFRASTRUCTURE_ARCHITECTURE.md` §11). The refresh cookie's `Set-Cookie` header should set `Domain=.mesell.xyz` so the cookie is sent to `api.mesell.xyz` from a `dev.mesell.xyz`-loaded page. Verify backend CORS responds with `Access-Control-Allow-Credentials: true` and the frontend's HttpClient calls use `withCredentials: true` for `/auth/*` only.

**Action for backend coordinator:** confirm `Set-Cookie: refresh_token=...; Domain=.mesell.xyz; Path=/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=<ttl>` is the correct header set on otp/verify and on refresh. (Path=/auth restricts cookie attachment to /auth/* endpoints — minimises exposure.)

### 7. Test additions (BACKEND_ARCHITECTURE.md §19)

Per-module unit tests for `iam`:
- Refresh allowlist write on verify
- Refresh validation on /auth/refresh (valid / expired / revoked / rotated)
- Logout deletes allowlist entry + clears cookie
- Constant-time comparison for refresh-token lookup
- Rotation idempotency on concurrent /auth/refresh calls (lock or use Valkey MULTI/EXEC)

Backend integration tests:
- Full silent-refresh flow: verify → wait < 15 min → refresh → access-token rotated → old access still works until TTL
- Logout revocation: verify → logout → /auth/refresh → 401
- Replay attack mitigation: verify → refresh → save old refresh cookie → try to use old refresh cookie → 401 (because rotation invalidated it)

## What frontend has already updated

`docs/FRONTEND_ARCHITECTURE.md`:
- §0.F — added FE-D5 (no client-side token storage) and FE-D6 (env-driven lifetimes, frontend trusts response)
- §1.B — ASCII diagram core/ box updated: 4 interceptors (added LocaleInterceptor + RefreshInterceptor explicitly), AuthService methods listed (bootstrap, scheduleRefresh, logout), added "Cookie flow" appendix
- §1.C — request flow walkthrough rewritten for the bootstrap-on-reload + silent-refresh path
- §1.F — full split-storage table + security boundary reasoning replacing the old localStorage paragraph
- §4 — 4 interceptors specified with chain order, token storage paragraph rewritten per FE-D5, refresh scheduling paragraph per FE-D6, logout flow paragraph added
- §7 — auth feature AuthApiService expanded to wrap refresh + logout
- §22A risk 4 — mitigation updated for transparent refresh
- §23 — endpoint count notation updated (24 contract + 2 new = 26 frontend consumes; backend total 25→27 pending ratification)

**Section 1 stays DRAFT** until backend coordinator confirms the 7 amendments above. Once confirmed, the founder flips Section 1 to LOCKED.

## Action items for the founder (in order)

1. **Send this memo to `meesell-backend-coordinator` session.** Ask backend coordinator to amend BACKEND_ARCHITECTURE.md per items 1-7 above.
2. **Wait for backend coordinator confirmation** that the deltas are accepted (or push back). Most likely point of contention: refresh-rotation atomicity under concurrent requests — backend may propose a slightly different lock strategy, that's fine.
3. **Optionally bring this to `meesell-database-builder`** — the Valkey DB 0 keyspace addition (`cache:refresh:*`) is additive, no migration needed, but the keyspace map should be updated in `DATABASE_ARCHITECTURE.md` (or `INFRASTRUCTURE_ARCHITECTURE.md` Valkey section) for completeness.
4. **Return to frontend coordinator** with backend confirmation. I will then flip FRONTEND_ARCHITECTURE.md §1 from DRAFT to LOCKED.

## Why this isn't blocking on me

The frontend doc is already updated. Specialists who eventually consume the auth feature spec will read the FE-D5/FE-D6 rulings and the refreshed §4 interceptor chain — they have everything they need to implement the frontend side. The only thing waiting on backend coordinator is the LOCK on §1 (because §1 references the cookie flow which must match what the backend implements).

If backend coordinator pushes back substantively on any of the 7 items, I will revise FRONTEND_ARCHITECTURE.md accordingly. The current draft assumes backend accepts items 1-7 verbatim.
