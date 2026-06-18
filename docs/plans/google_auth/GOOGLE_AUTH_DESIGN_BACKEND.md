# Google Sign-In — Backend Design (svc-iam)

**Status:** DESIGN / PLAN ONLY — awaiting founder review. No code is written from this document until ratification.
**Author:** meesell-backend-coordinator
**Date:** 2026-06-18
**Feature vertical:** V1 Feature 1 (Auth) — additive identity provider.
**Specialist that will implement (after sign-off):** `meesell-auth-builder` (token issuance + adapter + linking rules) with a thin `meesell-database-builder` slice (the migration + ORM column adds). `meesell-api-routes-builder` adds the one new route + schema.
**Scope of this doc:** the svc-iam standalone tree at `backend/services/svc-iam/` AND the monolith `backend/app/modules/iam/` (the two are kept byte-parity per the svc-iam vendor note). Every change below lands in **both trees**.

---

## 0. Summary (read this first)

We add **Google Sign-In via Google Identity Services (GIS) ID-token flow**:

1. Frontend obtains a Google ID-token (a JWT) using GIS in the browser.
2. Frontend POSTs `{ "credential": "<id_token>" }` to a **new** endpoint `POST /api/v1/auth/google/verify`.
3. Backend verifies the ID-token against Google's public certs (signature, `iss`, `aud`, `exp`, `email_verified`), extracts `sub` / `email` / `name`.
4. Backend upserts/links the `iam.users` row, then **reuses the exact existing token-issuance path** (`issue_access_token` + `issue_refresh_token` + Valkey allowlist + `_set_refresh_cookie`).
5. Response is **byte-identical in shape to `VerifyOtpResponse`** (access JWT in body, refresh cookie in `Set-Cookie`).

The crux is the **identity model change**: phone becomes nullable, Google `sub` becomes a valid primary identity, and three deterministic linking rules govern upsert. This **amends locked CLAUDE.md Key Decision #5** and must be founder-ratified before any code.

**Recommended schema shape:** keep identities **inline on `iam.users`** (add `google_sub`, make `phone` nullable, keep existing `email`, add `auth_provider` audit column, add a CHECK constraint "at least one identity"). A separate `identities` table is deferred to V1.5. Rationale in §B.

**Recommended linking rule:** match by `google_sub` → login; else match by **verified `email`** → link `google_sub` onto the existing (phone) user; else create a Google-only user with `phone = NULL`.

---

## A. LOCKED-SPEC AMENDMENT — REQUIRES FOUNDER RATIFICATION

> **This section must be approved by the founder before any code is written.** It amends a locked Key Decision and touches the FE-D5 amendment.

### A.1 What changes

**CLAUDE.md Key Decision #5** currently reads: *"Phone OTP login, not email — Indian sellers prefer phone, no password friction."*

This design introduces a **DUAL-IDENTITY model**: a user may exist with

- **phone only** (current behaviour — every existing row),
- **Google only** (`email` + Google `sub`, `phone = NULL`), or
- **both** (a phone user who later links Google, or a Google user who later adds phone — V1.5 for the latter).

Concrete consequences:

1. `iam.users.phone` changes from `NOT NULL UNIQUE` → **NULL-able, UNIQUE** (the unique index must allow multiple NULLs — Postgres `UNIQUE` already treats NULLs as distinct, so no partial-index gymnastics required for NULL-multiplicity, but see §B.3 for the collision detail).
2. `iam.users.email` becomes a **genuine identity** (it was a free-text optional column). It gains a **UNIQUE constraint** (nullable-unique) because email is now a linking key.
3. A new column `iam.users.google_sub` (Google's stable subject identifier) is added — **UNIQUE, nullable**.
4. A table-level **CHECK constraint** guarantees every row carries at least one identity: `phone IS NOT NULL OR google_sub IS NOT NULL`.

### A.2 Why

The founder has locked the product decision to offer Google sign-in. Indian Meesho sellers increasingly have Google accounts on Android; Google sign-in removes SMS cost (MSG91 per-OTP fee) and SMS-delivery friction for that cohort while keeping phone-OTP as the primary path. This is **additive** — the phone path is unchanged.

### A.3 Interaction with Decision #14 (FE-D5 split-token)

**No change to FE-D5.** Google sign-in produces **our own** access JWT + refresh cookie exactly as the OTP path does. Google's ID-token is consumed **once** at `/auth/google/verify` and never stored, never re-presented, never placed in a cookie. The split-token contract (`access in memory`, `refresh in HttpOnly cookie on path /api/v1/auth`, Valkey allowlist revocation) is identical for both providers. The cookie is set via the **existing** `_set_refresh_cookie` helper — same name, domain, path, flags.

### A.4 Interaction with locked `BACKEND_ARCHITECTURE.md §7` and §17

- §7.B endpoint inventory grows from **6 → 7** iam endpoints; §17 mounted-endpoint inventory grows from **28 → 29**. Both are LOCKED counts — **this requires a §7.3 architecture amendment** (founder approval), not just a board edit.
- §7.E (Pydantic schema set) gains `GoogleVerifyRequest` (`GoogleVerifyResponse` is an alias of the existing `VerifyOtpResponse` shape — see §C).
- §7.D (repository) gains `find_user_by_google_sub`, `find_user_by_email`, and `upsert_user_on_google_login`.
- §6 (adapters) gains a **6th adapter**: `adapters/google.py`. The adapter import-linter allowlist (§6.G / §19) must be extended to permit `app.adapters.google` consumed by `iam.service` (iam already consumes `adapters.msg91` and `adapters.razorpay`, so this is consistent with the existing pattern — no new ✗→✓ in the cross-MODULE matrix because adapters are not modules).

### A.5 Risk

| Risk | Severity | Mitigation |
|---|---|---|
| Widening `phone NOT NULL → NULL` on a live table with data | LOW | Widening a NOT-NULL to NULL is **always safe** — no existing row violates it; no rewrite, no lock beyond a brief `ACCESS EXCLUSIVE` for the `ALTER`. |
| Adding `UNIQUE` on `email` when legacy rows may share/duplicate email | MEDIUM | Pre-migration scan for duplicate non-NULL emails; abort if any exist (mirrors the Risk#5 pre-scan pattern in `b1c2d3e4f5a6`). See §B.5. |
| Account-takeover via email-linking | MEDIUM-HIGH | Only link on `email_verified == true` from Google AND only when the existing user's email already equals the Google email (we never link to an arbitrary phone user). See §E + §G. |
| Endpoint/inventory count drift vs locked §17 | LOW (process) | §7.3 amendment requested in this doc. |

### A.6 Requested ratification

**Founder: please explicitly ratify (or amend) the following before code is written:**

1. The DUAL-IDENTITY model (phone nullable, Google a primary identity) — amends Decision #5.
2. The `email`-based auto-linking rule in §E (this is the security-sensitive decision).
3. The §7.3 architecture amendment raising the iam endpoint count 6→7 and §17 count 28→29.

---

## B. Schema & Migration Design

### B.1 Current `iam.users` shape (as-built)

| column | type | constraints |
|---|---|---|
| `id` | UUID | PK, `gen_random_uuid()` |
| `phone` | VARCHAR(15) | **UNIQUE, NOT NULL, indexed** |
| `email` | VARCHAR(255) | nullable, **no unique** |
| `plan` | VARCHAR(20) | NOT NULL default `'free'`, indexed |
| `created_at` | TIMESTAMPTZ | NOT NULL default `NOW()` |
| `last_login_at` | TIMESTAMPTZ | nullable |

### B.2 Target `iam.users` shape

| column | type | constraints | change |
|---|---|---|---|
| `id` | UUID | PK | unchanged |
| `phone` | VARCHAR(15) | UNIQUE, **NULL-able**, indexed | **widened to NULL** |
| `email` | VARCHAR(255) | **UNIQUE (nullable-unique)**, indexed | **gains UNIQUE** |
| `google_sub` | VARCHAR(255) | **UNIQUE (nullable-unique)**, indexed | **new** |
| `auth_provider` | VARCHAR(20) | NOT NULL default `'phone'` | **new** (audit/analytics: `phone` \| `google`; the *most recent* provider used to authenticate — informational, NOT an identity key) |
| `plan` | VARCHAR(20) | unchanged | — |
| `created_at` | TIMESTAMPTZ | unchanged | — |
| `last_login_at` | TIMESTAMPTZ | unchanged | — |

**Table-level CHECK constraint** (`ck_users_at_least_one_identity`):

```sql
CHECK (phone IS NOT NULL OR google_sub IS NOT NULL)
```

Note: `email` alone is **deliberately not** sufficient to satisfy the CHECK. Email is a *linking* key but not an *authentication* key on its own (we never authenticate by email without a verified Google token). A Google-only user always has `google_sub`; a phone user always has `phone`. This keeps the invariant tight.

### B.3 Inline columns vs. separate `identities` table — RECOMMENDATION

**Recommendation: keep identities INLINE on `iam.users` for V1.** Defer a normalized `identities` table to V1.5.

Rationale:

- **Cardinality is tiny.** V1 supports exactly two providers (phone, google), at most one of each per user. A 1-row-per-provider join table buys nothing for a 2-column inline representation.
- **Hot path stays single-row.** `core/auth.get_current_user` does `db.get(User, sub)` (PK fetch). `find_user_by_phone` / `find_user_by_google_sub` / `find_user_by_email` are single-column UNIQUE-index lookups. A join table would add a join to every auth read.
- **Vendor-parity is cheaper.** The svc-iam tree is a byte-for-byte vendored copy; adding 2 columns + 1 check to one ORM file is far less surface than introducing a new table + ORM model + cross-schema considerations in both trees.
- **Migration is reversible and low-risk** (column adds + constraint, no data move).

**When V1.5 should revisit:** if/when a *third* provider (Apple, email-magic-link) or *multiple emails per user* is required, normalize to `iam.identities(user_id, provider, provider_subject, email, verified_at, created_at)` with a unique `(provider, provider_subject)`. The migration path from inline → table is a straightforward backfill (one identity row per non-NULL `phone`/`google_sub`). **Flag this in the migration docstring as the V1.5 evolution path.**

### B.4 ORM model change (`app/shared/models/user.py`, both trees)

Add (Pydantic/SQLAlchemy 2.0 `Mapped[T]` style, matching the existing file):

```python
google_sub: Mapped[str | None] = mapped_column(
    String(255), unique=True, index=True,
    comment="Google Identity Services stable subject (sub claim); NULL for phone-only users",
)
auth_provider: Mapped[str] = mapped_column(
    String(20), nullable=False, server_default=text("'phone'"),
    comment="Most-recent provider used to authenticate: phone | google",
)
```

And amend the existing `phone` and `email` columns:

```python
phone: Mapped[str | None] = mapped_column(   # was Mapped[str], nullable=False
    String(15), unique=True, nullable=True, index=True,
    comment="E.164 format; NULL for Google-only users",
)
email: Mapped[str | None] = mapped_column(
    String(255), unique=True, index=True,    # gains unique=True, index=True
    comment="Verified email; UNIQUE linking key (nullable-unique)",
)
```

`__table_args__` must move from a bare `{"schema": "iam"}` dict to a tuple carrying the CHECK constraint:

```python
__table_args__ = (
    CheckConstraint(
        "phone IS NOT NULL OR google_sub IS NOT NULL",
        name="ck_users_at_least_one_identity",
    ),
    {"schema": "iam"},
)
```

> **Note for database-builder:** the monolith `user.py` carries 6 ORM relationships; the svc-iam copy drops them. The column/constraint adds are identical in both; only the relationships differ. Keep both in sync in the same PR.

### B.5 Alembic migration plan

**New revision** in `backend/services/svc-iam/app/alembic/versions/` (and the mirror chain in the monolith `backend/alembic/versions/`):

- **Revision id:** new (e.g. `c2d3e4f5a6b7_add_google_identity_to_users`).
- **down_revision:** `b1c2d3e4f5a6` (the current svc-iam head; verified — the svc-iam chain currently has exactly one migration). In the **monolith** chain, `down_revision` = the monolith head (`f31c75438e61` per the svc-iam migration docstring — database-builder MUST re-confirm the live monolith head at implementation time; do not hardcode without verifying).
- **Head-divergence guard:** before authoring, run `alembic heads` in BOTH trees and confirm a single head each. This is a P0 merge-gate check (Stop Condition: migration head divergence between dev and staging).

**Upgrade sequence:**

1. **Pre-scan for duplicate non-NULL emails** (Risk-style guard, mirrors `b1c2d3e4f5a6`'s Risk#5 pattern):
   ```sql
   SELECT email, COUNT(*) FROM iam.users
   WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1;
   ```
   If any row returned → **raise RuntimeError and abort** (emit the offending emails, hashed, to the log). The UNIQUE-on-email add would fail anyway; failing early with a clear forensic message is the locked pattern.
2. `ALTER TABLE iam.users ALTER COLUMN phone DROP NOT NULL;` — safe widening.
3. `ALTER TABLE iam.users ADD COLUMN google_sub VARCHAR(255);`
4. `ALTER TABLE iam.users ADD COLUMN auth_provider VARCHAR(20) NOT NULL DEFAULT 'phone';` (existing rows backfill to `'phone'` automatically via the default — correct, they are all phone users).
5. `CREATE UNIQUE INDEX ix_users_google_sub ON iam.users (google_sub);` (nullable-unique — multiple NULLs allowed by Postgres semantics).
6. `CREATE UNIQUE INDEX ix_users_email ON iam.users (email);` (nullable-unique).
7. `ALTER TABLE iam.users ADD CONSTRAINT ck_users_at_least_one_identity CHECK (phone IS NOT NULL OR google_sub IS NOT NULL);` — every existing row has a phone, so the constraint validates immediately with no violations.

**Ordering note:** step 1 (the scan) must run before step 6 (the email unique index). The `phone DROP NOT NULL` (step 2) is independent and can run any time before the CHECK in step 7.

**Backfill:** none required beyond the `auth_provider` default. Existing rows all have `phone IS NOT NULL`, so they satisfy the CHECK and need no `google_sub`.

**Unique-index collision handling:** the email pre-scan (step 1) is the collision guard. `google_sub` cannot collide on existing data (the column is brand-new, all NULL).

**Downgrade sequence (reverse order):**

1. `ALTER TABLE iam.users DROP CONSTRAINT ck_users_at_least_one_identity;`
2. `DROP INDEX iam.ix_users_email;`
3. `DROP INDEX iam.ix_users_google_sub;`
4. `ALTER TABLE iam.users DROP COLUMN auth_provider;`
5. `ALTER TABLE iam.users DROP COLUMN google_sub;`
6. **`phone` re-tighten:** `ALTER TABLE iam.users ALTER COLUMN phone SET NOT NULL;` — **DANGER:** this fails if any Google-only user (phone NULL) was created after the upgrade. The downgrade must first guard:
   ```sql
   SELECT COUNT(*) FROM iam.users WHERE phone IS NULL;
   ```
   If `> 0`, the downgrade **raises with a clear message** ("cannot re-tighten phone NOT NULL: N Google-only users exist; delete or assign phones first"). This is the correct, honest behaviour — a downgrade that would destroy the at-least-one-identity invariant must not silently proceed. Document this loudly in the migration docstring.

**Rollback (operational, not Alembic downgrade):** if the new endpoint misbehaves in dev/staging, the **feature flag** (`FEATURE_GOOGLE_AUTH_ENABLED`, see §C.6) is the first-line rollback — flip it off, the route 404s/501s, the schema stays. Only `alembic downgrade` if the schema itself is implicated (rare).

**Apply ordering (infra hand-off):** dev before staging, never the reverse (locked rule). The migration touches only `iam.users` (no cross-schema FK), so it is self-contained within the iam service's DB role.

---

## C. New Endpoint Contract

### C.1 Route

```
POST /api/v1/auth/google/verify
```

Mounted on the existing iam `router` (prefix `/api/v1`, tag `iam`). It sits alongside `/auth/otp/verify` and uses the **same** `Request` + `Response` + `db` + `valkey` dependency set so it can call `_set_refresh_cookie`.

### C.2 Request schema (`GoogleVerifyRequest`, new in `schemas.py`)

```python
class GoogleVerifyRequest(BaseModel):
    """POST /api/v1/auth/google/verify body."""
    credential: str = Field(
        min_length=1, max_length=4096,
        description="Google Identity Services ID-token (JWT). Verified server-side; never stored.",
    )
```

- `max_length=4096` bounds the token to defend against oversized-body abuse (Google ID-tokens are ~1KB; 4KB is generous headroom).
- No other fields. The frontend sends only the credential.

### C.3 Response schema

**Reuse `VerifyOtpResponse` exactly** (`access_token`, `expires_in`, `token_type="bearer"`). For OpenAPI differentiation we declare a thin alias model `GoogleVerifyResponse(VerifyOtpResponse)` with no added fields (mirrors how `RefreshResponse` is a distinct-but-identical model per §7.E). The **`Set-Cookie: refresh_token=...`** header is set via the existing `_set_refresh_cookie(response, refresh_token, refresh_expires_in)` — byte-identical cookie attributes to the OTP path.

### C.4 Status codes & error envelope mapping

| Outcome | HTTP | `validation_message_id` | Exception (new, in `exceptions.py`) |
|---|---|---|---|
| Success | 200 | — | — |
| Malformed / unparseable credential | 400 | `validation.credential.invalid_format` | (Pydantic for empty; `GoogleTokenInvalidError` for non-JWT) |
| Invalid signature / wrong `aud` / wrong `iss` / expired | 401 | `auth.google.token_invalid` | `GoogleTokenInvalidError` (401) |
| `email_verified != true` | 401 | `auth.google.email_unverified` | `GoogleEmailUnverifiedError` (401) |
| Google certs endpoint unreachable | 503 | `auth.google.unavailable` | `GoogleUnavailableError` (503) — mirrors `Msg91UnavailableError` |
| Email-linking conflict (email belongs to a *different* google_sub) | 409 | `auth.google.identity_conflict` | `GoogleIdentityConflictError` (409) — see §E edge cases |

All exceptions subclass `IamError` → `MeesellError`, so the §4.F error handler builds the locked envelope. New `validation_message_id`s must be added to the i18n registry (`app/i18n/messages_en.py`) — **3-segment form** per §5A.H (`auth.google.token_invalid`, `auth.google.email_unverified`, `auth.google.unavailable`, `auth.google.identity_conflict`, `validation.credential.invalid_format`). Missing-key gaps render blank errors (a recurring defect class in master memory) — the i18n keys are a **required deliverable**, not optional.

### C.5 Rate limit

```python
@rate_limit(scope="google_verify", limit=20, window=3600)
```

Per-IP (the existing decorator keys anonymous routes per-IP, per the router docstring). 20/h is higher than OTP-verify's 10/h because there is no SMS cost to throttle and the Google token itself is the proof-of-work; the limit exists purely as a DDoS/abuse floor. Founder may tune.

### C.6 Feature flag

Add `FEATURE_GOOGLE_AUTH_ENABLED: bool = False` to `shared/config.py` (both trees). When `False`, the route returns 404 (not mounted) or 501 — **recommendation: do not mount the route when the flag is off**, so the OpenAPI surface and §17 count are unchanged until the founder enables it per environment. This gives a clean per-namespace rollout (dev → staging) and an instant rollback that does not require redeploy of a code revert.

### C.7 OpenAPI metadata

```python
@router.post(
    "/auth/google/verify",
    response_model=GoogleVerifyResponse,
    summary="Verify a Google ID-token, mint access JWT, set refresh cookie",
)
```

OpenAPI must be regenerated and reviewed at the merge gate (locked criterion: "OpenAPI regenerated when an endpoint shape changes").

---

## D. Google Token Verification (`adapters/google.py`)

### D.1 Adapter design

A new **6th adapter** following the existing pattern (`adapters/msg91.py`, `adapters/razorpay.py`):

- Pure transport/verification boundary. No business logic (no upsert, no token issuance — those live in `service.py`).
- Async public surface (one exception: the actual signature math is sync/CPU-bound; wrap it so the public method is `async def verify_id_token(credential: str) -> GoogleClaims`).
- Reads `settings.GOOGLE_OAUTH_CLIENT_ID` — **never `os.getenv`** (§6.G CI-enforced).
- Returns a typed frozen dataclass `GoogleClaims(sub, email, email_verified, name, picture | None)` — Google SDK quirks never leak past the file boundary (§2.9 / M10).

### D.2 Library

Use **`google-auth`** (`google.oauth2.id_token.verify_oauth2_token`), which handles cert fetching, caching, signature, `iss`, `aud`, and `exp` verification in one call:

```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

claims = id_token.verify_oauth2_token(
    credential,
    google_requests.Request(),     # caches Google certs internally
    audience=settings.GOOGLE_OAUTH_CLIENT_ID,
)
# verify_oauth2_token already enforces: signature, exp, aud == client_id,
# and iss in {"accounts.google.com", "https://accounts.google.com"}.
```

**Dependency status (verified 2026-06-18):** `google-auth==2.53.0` is present in the **monolith** venv but **only as a TRANSITIVE dependency** (pulled by `google-generativeai` / `google-cloud-storage`). The **svc-iam `requirements.txt` explicitly EXCLUDES all google libraries** ("NO gemini / langfuse / google-cloud-storage"). Therefore:

> **`google-auth` MUST be added as a NEW DIRECT dependency to `backend/services/svc-iam/requirements.txt`** (pin `google-auth==2.53.0` to match the monolith's transitive pin). The monolith `requirements.txt` should also pin it **directly** (promote it from transitive to direct) so the iam module's import is not silently dependent on the Gemini/GCS dependency graph. This is the only new runtime dependency the feature introduces. (`google-auth` brings `cachetools`, `pyasn1-modules`, `rsa` transitively — all already present in the monolith venv.)

### D.3 Verification rules enforced

1. **Signature** against Google's published JWKs (handled by `verify_oauth2_token`).
2. **`aud` == `GOOGLE_OAUTH_CLIENT_ID`** (audience confusion defence — see §G). If the founder later ships a separate Android/iOS OAuth client, `audience` becomes a *set* of accepted client IDs; design `GOOGLE_OAUTH_CLIENT_ID` as a comma-split list in config now to avoid a later migration (recommended: accept `list[str]`, like `CORS_ALLOWED_ORIGINS`).
3. **`iss`** in the Google issuer set (handled by the library).
4. **`exp`** not in the past (handled by the library; small clock-skew tolerance is built in).
5. **`email_verified == true`** — enforced in the **adapter** after the library call; raise `GoogleEmailUnverifiedError` if false/absent. This is **the** anti-spoofing gate (see §G).
6. Extract `sub` (the stable identity), `email`, `name`.

### D.4 Cert caching

`google.auth.transport.requests.Request()` caches Google's JWKs in-process with the documented TTL (respects Google's `Cache-Control`/`max-age`, ~hours). Recommendation: hold a **module-level singleton `Request` instance** (lazy, like the msg91 `_get_client()` pattern) so cert caching is shared across calls within the worker process. Do not construct a new `Request()` per call (defeats caching, adds latency).

### D.5 Failure modes

| Failure | Adapter behaviour |
|---|---|
| Network error reaching Google certs | raise `GoogleUnavailableError` (503) — analogous to MSG91 503, but here we **raise** (Razorpay/MSG91 have their documented non-raise exceptions; google follows the default §6.G raise-on-failure pattern). |
| `ValueError` from `verify_oauth2_token` (bad sig / aud / exp / malformed) | raise `GoogleTokenInvalidError` (401). |
| `email_verified` false/missing | raise `GoogleEmailUnverifiedError` (401). |

The adapter raises **typed `IamError`/adapter exceptions**; `service.py` does not re-translate (unlike the MSG91 bool-return path). This keeps the adapter's surface explicit.

### D.6 Config additions (`shared/config.py`, both trees)

```python
GOOGLE_OAUTH_CLIENT_ID: str = ""           # the Web client ID; audience for verify
FEATURE_GOOGLE_AUTH_ENABLED: bool = False  # per-env rollout gate
```

`GOOGLE_OAUTH_CLIENT_ID` is added to `REQUIRED_FIELDS` **only when `FEATURE_GOOGLE_AUTH_ENABLED` is true** (use a `model_validator` that conditionally requires it — do not hard-require it, or every existing env breaks at boot). Infra hand-off: populate `google-oauth-client-id` in Secret Manager (it is not secret per se — the client ID is public — but keep config provenance uniform).

---

## E. Account Linking / Upsert Rules (the crux)

### E.1 New repository method

`upsert_user_on_google_login(db, *, google_sub, email, ip) -> User` in `repository.py` (both trees), plus two finders: `find_user_by_google_sub(db, google_sub)` and `find_user_by_email(db, email)`.

### E.2 Deterministic linking algorithm (V1)

Given verified `(google_sub, email)` from the adapter:

1. **Match by `google_sub`** → returning Google user. UPDATE `last_login_at`, set `auth_provider='google'`. **Login.** (No email re-write in V1 — see edge case 3.)
2. **Else match by `email`** (the email is verified-by-Google) → an existing user (created via phone OTP, has `phone` set, `google_sub IS NULL`). **LINK:** set that row's `google_sub`, set `auth_provider='google'`, UPDATE `last_login_at`. **Login as the existing user** (preserves their catalogs, plan, history).
3. **Else** → no match by either key. **CREATE** a new Google-only user: `phone = NULL`, `email = <verified email>`, `google_sub = <sub>`, `auth_provider='google'`, `plan='free'`, `last_login_at = NOW()`.

This runs inside the caller's `db` transaction (repository does not commit; service/`get_db` owns the boundary), exactly like `upsert_user_on_login`.

### E.3 Edge cases — V1 behaviour vs V1.5 deferral

| # | Scenario | V1 behaviour | V1.5 |
|---|---|---|---|
| 1 | Google `sub` already known | Login (rule 1). | — |
| 2 | Email matches a phone-only user, no `google_sub` yet | Link `google_sub` to that user (rule 2). | — |
| 3 | Google `sub` known, but the email on the token **differs** from the stored email (user changed their Google email) | **Keep stored email; login by `sub`.** Do NOT overwrite email (overwriting could collide with another row's unique email). Log an `auth.google.email_changed` audit note. | Offer a "your Google email changed, update it?" reconciliation flow with conflict checks. |
| 4 | Email matches an existing user **AND** that user already has a *different* `google_sub` | **409 `GoogleIdentityConflictError`.** This means two distinct Google accounts claim the same verified email — should be impossible (Google enforces email uniqueness per account), but we fail closed rather than hijack. | Manual support merge. |
| 5 | A Google-only user later wants to add a phone (OTP) | **Not in V1** — the OTP `upsert_user_on_login` matches by phone only and would create a *second* row. V1 does not link phone→existing-Google-user. | Account-settings "add phone" linking flow + merge-by-email-on-OTP. |
| 6 | Two separate accounts (one phone-only, one Google-only) that the human owns, with *different* emails | Stay separate in V1 (no signal to merge). | Manual/assisted merge tool. |
| 7 | Email collision on CREATE (rule 3) — race where two requests create the same new email concurrently | The `email` UNIQUE index rejects the second INSERT; service catches `IntegrityError`, retries the read (now finds the row), links/logs in (rule 1/2). Implement as a **single retry on unique-violation**. | — |

### E.4 Concurrency

The whole upsert is one DB transaction. The `email`/`google_sub` UNIQUE indexes are the source of truth for race resolution (edge case 7). The service wraps the upsert in a **try/except IntegrityError → re-read → resolve** loop (max 1 retry) so a concurrent link/create does not 500.

---

## F. Token Issuance & Audit

### F.1 Token issuance — REUSE, do not duplicate

After `upsert_user_on_google_login` returns the `User`, the Google path calls the **identical** issuance code as the OTP path:

```python
access_token = issue_access_token(user.id, user.plan)
refresh_token = issue_refresh_token()
await valkey.set(refresh_allowlist_key(refresh_token),
                 _serialize_allowlist_entry(RefreshAllowlistEntry(user.id, now, ip)),
                 ex=settings.REFRESH_TOKEN_TTL_SECONDS)
```

No new token shape, no new TTL, no new allowlist key format. The dual-pepper allowlist, the Lua rotation, `/auth/refresh`, and `/auth/logout` all work unchanged for Google-issued sessions (they are provider-agnostic — they only know the opaque refresh token + user_id).

### F.2 New service method

`verify_google_and_issue_tokens(credential, client_ip, db, valkey) -> VerifyOtpResult` (returns the **same** `VerifyOtpResult` domain object the OTP path returns — the router serializes it identically). Pipeline:

1. `claims = await google_adapter.verify_id_token(credential)` (raises typed errors).
2. `user = await iam_repo.upsert_user_on_google_login(db, google_sub=claims.sub, email=claims.email, ip=client_ip)`.
3. Mint access + refresh, write allowlist entry (as above).
4. Write audit row via the existing `_write_audit_direct` (SAVEPOINT in-request path — same reason as OTP: the user upsert is in-flight in this transaction).

### F.3 Audit event types

- `auth.login.success` with `metadata={"provider": "google", "ip": ip, "hashed_email": sha256(email + AUDIT_PII_SALT)}`. Reuse the existing event type so dashboards aggregate logins uniformly; the `provider` discriminator is in metadata. (Email is PII → hash it with `AUDIT_PII_SALT`, mirroring `_hash_phone_for_audit`. Add a `_hash_email_for_audit` helper.)
- `auth.google.linked` (new) when rule 2 fires (a phone user gains a Google identity) — security-relevant, log it.
- `auth.google.email_changed` (new, info) for edge case 3.
- Failure paths (`auth.google.token_invalid`, `auth.google.email_unverified`) have **no user_id** → the existing `_write_audit_direct` short-circuits on `user_id is None` (the `audit_events.user_id` NOT-NULL constraint). Log via the service logger instead, exactly as the OTP-miss path does today.

### F.4 DPDP consent parity

The OTP path passes `capture_dpdp=True` to the repository (currently a no-op + WARNING because the `dpdp_consented_at` column does not exist — a documented V1 gap). The Google path must achieve **parity**: pass the same `capture_dpdp=True` intent. Since the column gap is pre-existing and owned by a separate V1.5 hand-off, the Google path inherits the same no-op-with-warning behaviour — **do not** fix the DPDP column gap inside this feature (out of scope; flag it stays open for both providers). If the founder wants DPDP captured at Google sign-in, that is a **coupled decision** to add `dpdp_consented_at` (database-builder) — surface it as an open question (§I).

---

## G. Security Analysis

| Threat | Vector | Mitigation in this design |
|---|---|---|
| **ID-token replay** | Attacker captures a valid Google ID-token and re-POSTs it. | ID-tokens are short-lived (~1h `exp`); `verify_oauth2_token` rejects expired tokens. We issue **our own** refresh cookie immediately, so the Google token is single-use in practice. **We do NOT store or accept the Google token after verify.** Optional hardening (V1.5): track a `jti`/`nonce` nonce-cache in Valkey DB 0 with the token's remaining TTL to make replay impossible even within the `exp` window — **deferred** (low value given short exp + our-token issuance). Surfaced in §I. |
| **Audience confusion** | Attacker presents an ID-token minted for a *different* OAuth client (a token they legitimately obtained for some other app that uses Google sign-in). | `audience=GOOGLE_OAUTH_CLIENT_ID` enforced by `verify_oauth2_token` — a token with a different `aud` is rejected. This is the single most important check; **`GOOGLE_OAUTH_CLIENT_ID` must be set and non-empty when the feature is enabled** (config validator enforces). |
| **`email_verified` spoofing** | A Google account with an unverified email tries to link to a victim's phone-account whose email matches. | We enforce `email_verified == true` in the adapter; unverified → 401. Linking (rule 2) only fires on a verified email. |
| **Account takeover via email-linking** | The dangerous one: if we linked on *any* email match, an attacker who controls a Google account with email `victim@x.com` could absorb the victim's phone-account. | Mitigated by: (a) `email_verified` gate (Google only marks verified if the account owner proved control of that mailbox); (b) we link to the existing user **only** when the existing user's stored email already equals the verified Google email — we never link to a phone-account that has a *different* or NULL email. Combined, an attacker must control a Google account that Google has verified owns the victim's exact email — i.e. they already control the victim's email, at which point the victim has bigger problems. **Founder must explicitly accept this linking posture (§A.6 item 2).** Conservative alternative (offer as option): do NOT auto-link at all in V1 — always create a separate Google-only user, and defer all linking to an authenticated "link account" flow in V1.5. This is safer but creates duplicate accounts for users who used both phone and Google. Recommendation: auto-link with the email-equality guard; surface the choice in §I. |
| **Rate-limit / DoS** | Flood `/auth/google/verify` to exhaust the Google certs endpoint or DB. | Per-IP rate limit (20/h, §C.5); Google certs are cached in-process (§D.4) so verification does not hit Google per request; the DB op is a single-row upsert. |
| **Token-in-URL leakage** | If credential were a query param it could leak via logs/referrer. | Credential is in the **POST body**, never the URL. Never logged (the service logs `email_verified`/`sub`-presence booleans, never the raw token). |
| **CSRF on the cookie** | The refresh cookie is set on a state-changing POST. | Unchanged from OTP path: `SameSite=Strict`, `HttpOnly`, `Secure`, path-scoped to `/api/v1/auth`. The access token is bearer-in-header (not cookie), so the authenticated API surface is CSRF-immune. |

---

## H. Test Plan (described — not written here)

### H.1 Adapter unit tests (`tests/test_adapter_google.py`)
- `verify_id_token` happy path with a mocked `verify_oauth2_token` returning a full claim set → returns `GoogleClaims`.
- `email_verified=false` → raises `GoogleEmailUnverifiedError`.
- `verify_oauth2_token` raises `ValueError` (bad sig/aud/exp) → raises `GoogleTokenInvalidError`.
- Network error from the certs transport → raises `GoogleUnavailableError`.
- Confirms the raw credential is never passed to a logger (assert via caplog).
- Confirms the singleton `Request` instance is reused across calls.

### H.2 Service unit tests (`tests/test_service_google.py`) — linking matrix
One test per linking rule + edge case in §E.3:
- `sub`-match → login, no new row, `auth_provider='google'`.
- email-match (phone user, no sub) → links `google_sub`, same `id` returned, `auth.google.linked` audit written.
- no-match → creates Google-only user with `phone IS NULL`, satisfies CHECK.
- email matches a user with a *different* `google_sub` → `GoogleIdentityConflictError` (409).
- email-changed (sub known, different token email) → keeps stored email, logs `auth.google.email_changed`.
- IntegrityError race on create → single retry resolves to login (mock the unique violation).
- Confirms the **same** `issue_access_token`/`issue_refresh_token`/allowlist code is exercised (assert allowlist key written with the correct format).

### H.3 Route tests (`tests/test_route_google_verify.py`)
- 200 happy path → body has `access_token`+`expires_in`+`token_type`; `Set-Cookie: refresh_token` present with the locked attributes (HttpOnly, Secure, SameSite=Strict, Path=/api/v1/auth, Domain=.mesell.xyz).
- 400 on empty/oversized credential (Pydantic).
- 401 on token-invalid / email-unverified (envelope shape matches §4.F).
- 409 on identity conflict.
- 503 on Google-unavailable.
- Rate-limit: 21st request in an hour → 429.
- **Feature flag off** → route not mounted (404) / OpenAPI does not list it.

### H.4 Migration tests (`tests/test_migration_google_identity.py`)
- Upgrade on a DB with only phone users → all rows get `auth_provider='phone'`, CHECK validates, indexes created.
- Upgrade with a duplicate-email dataset → aborts with the forensic error.
- Downgrade with a Google-only user present → aborts on the `phone SET NOT NULL` guard.
- Downgrade with only phone users → clean reverse.

### H.5 Integration test (coordinator-owned, `backend/tests/test_google_auth_integration.py`)
- Full flow against a test DB + fake Valkey: POST credential → 200 → use the returned access token on `GET /auth/me` → 200 with the linked user's profile → POST `/auth/refresh` with the issued cookie → 200 (proves the Google-issued session participates in the shared refresh/rotate path).
- Cross-provider: create a phone user via OTP verify, then Google-verify with the same verified email → assert the **same** `user_id` (linking works end-to-end), and `/me` shows both `phone` and (V1.5) `google_sub` populated.

---

## I. Open Questions / Founder Decisions

1. **[SECURITY — must decide] Auto-link on verified email, or never auto-link in V1?**
   Recommendation: **auto-link** with the email-equality + `email_verified` guard (§E rule 2, §G row "Account takeover via email-linking"). The safer-but-clunkier alternative is "never auto-link; always create a separate Google-only user; defer linking to an authenticated V1.5 flow." This is the single most consequential decision in the design — it trades duplicate-account friction against a (well-mitigated) takeover surface.

2. **[SCOPE] DPDP consent at Google sign-in.**
   The OTP path's DPDP capture is a documented no-op (the `dpdp_consented_at` column does not exist — a pre-existing V1 gap). Should Google sign-in (a) inherit the same no-op-with-warning parity (no extra work, gap stays open for both providers — **recommended**), or (b) trigger adding `dpdp_consented_at` now (a coupled database-builder change beyond this feature's scope)?

3. **[ARCHITECTURE — §7.3 amendment] Ratify the endpoint-count increase.**
   iam endpoints 6→7, §17 mounted inventory 28→29. This is a LOCKED-section amendment requiring founder approval. Bundling it with the §A amendment is cleanest.

4. **[ROLLOUT] Feature-flag default + per-env enablement.**
   Recommendation: `FEATURE_GOOGLE_AUTH_ENABLED=False` default; enable dev → staging → (prod deferred to V1.5 per master plan §3). Confirm the rollout order and whether staging gets it before founder demo.

5. **[FORWARD-COMPAT] Multiple OAuth client IDs (Android/iOS native).**
   Should `GOOGLE_OAUTH_CLIENT_ID` be modeled as a **list** now (accepting Web + future native client IDs as audiences) to avoid a config migration when Phase-2 Ionic/Capacitor mobile ships? Recommendation: yes, model as a comma-split list (like `CORS_ALLOWED_ORIGINS`) even though V1 populates one value.

6. **[HARDENING — optional] ID-token nonce/replay cache.**
   Deferred recommendation: skip the Valkey nonce cache in V1 (short `exp` + immediate our-token issuance makes replay low-value). Confirm the founder is comfortable deferring this to V1.5.

---

## Appendix: Cross-lead hand-offs this feature will require (post-ratification)

- **→ frontend lead** (`handoff_contract_google_auth.md`): the new `POST /api/v1/auth/google/verify` contract (request `{credential}`, response = `VerifyOtpResponse` shape + refresh cookie). The FE owns obtaining the GIS credential and the `RefreshInterceptor` already covers the post-login session. The refresh cookie path/flags are unchanged, so no FE refresh-flow change is needed.
- **→ infra lead** (`handoff_secret_google_oauth_client_id.md`): populate `google-oauth-client-id` in Secret Manager and inject `GOOGLE_OAUTH_CLIENT_ID` + `FEATURE_GOOGLE_AUTH_ENABLED` per namespace (dev first). Confirm the svc-iam image rebuilds with the new `google-auth` dependency.
- **→ data lead**: none (no category/alias/template surface touched).
- **AI lead**: none.
```
