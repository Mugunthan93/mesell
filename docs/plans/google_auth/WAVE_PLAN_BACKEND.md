# Google Sign-In — Backend Wave Plan (svc-iam + monolith iam)

**Status:** COMPLETE 2026-06-18 (all 5 waves landed in both trees; self-gated; 22 new tests green; ruff clean; migration `c2d3e4f5a6b7`)
**Owner:** meesell-backend-coordinator (executing directly per HYBRID dispatch rule — dispatched coordinator self-gates)
**Branch / worktree:** `feature/google-auth` @ `/private/tmp/mesell-wt/google-auth`
**Source design (authoritative):** `docs/plans/google_auth/GOOGLE_AUTH_DESIGN_BACKEND.md` (master tree, uncommitted)
**Founder-ratified decisions:** dual-identity (phone OR Google); GIS ID-token flow; AUTO-LINK on verified email (google_sub match → verified-email link → new Google-only user; 409 on google_sub mismatch).

Every change lands in BOTH trees for byte-parity:
- `backend/services/svc-iam/app/...` (standalone microservice)
- `backend/app/modules/iam/...` + `backend/app/...` (monolith)

---

## BE-W1 — Locked-spec amendment in CLAUDE.md
- Key Decision #5: phone-only → dual-identity (phone OR Google).
- §7.3 / §17 endpoint-count change: iam 6→7, mounted 28→29.
- Precise, reversible-in-wording.

## BE-W2 — Schema + ORM (database slice)
- Alembic migration in svc-iam (`down_revision = b1c2d3e4f5a6`) + mirror in monolith chain (re-confirm monolith head live).
- `phone` → nullable (keep unique); `email` → unique (nullable-unique); add `google_sub` (unique, nullable); add `auth_provider` (default 'phone').
- CHECK `(phone IS NOT NULL OR google_sub IS NOT NULL)`.
- Dup-email pre-scan abort guard on upgrade; downgrade refuses `phone SET NOT NULL` if any google-only user exists.
- ORM `User` model updated in both trees.

## BE-W3 — Adapter + config + dependency
- `adapters/google.py`: verify ID-token via `google.oauth2.id_token.verify_oauth2_token` (sig/iss/aud/exp) + enforce `email_verified==true`; extract sub/email/name. Typed `GoogleClaims` frozen dataclass. Module-level singleton `Request`.
- `google-auth==2.53.0` as DIRECT dep in svc-iam requirements; promote to direct in monolith requirements.
- `GOOGLE_OAUTH_CLIENT_ID` + `FEATURE_GOOGLE_AUTH_ENABLED` in `shared/config.py` (both trees); conditional-required validator.

## BE-W4 — Endpoint + service + repository
- `POST /api/v1/auth/google/verify` — req `{credential}`, resp = `VerifyOtpResponse` shape + same refresh cookie via `_set_refresh_cookie`; rate-limit 20/h per-IP; feature-flag gated (route not mounted unless flag on).
- `GoogleVerifyRequest` schema; `GoogleVerifyResponse` alias.
- New exceptions: `GoogleTokenInvalidError` (401), `GoogleEmailUnverifiedError` (401), `GoogleUnavailableError` (503), `GoogleIdentityConflictError` (409).
- i18n keys (3-segment): `auth.google.token_invalid`, `auth.google.email_unverified`, `auth.google.unavailable`, `auth.google.identity_conflict`, `validation.credential.invalid_format`.
- Repository: `find_user_by_google_sub`, `find_user_by_email`, `upsert_user_on_google_login` (auto-link rule, single retry on IntegrityError).
- Service: `verify_google_and_issue_tokens` (reuse issue_access/refresh + allowlist + audit). Audit `auth.login.success` provider=google via SAVEPOINT direct-ORM pattern; `auth.google.linked`, `auth.google.email_changed` notes; `_hash_email_for_audit`.

## BE-W5 — Tests
- Adapter unit, service linking-matrix, route tests (success, invalid token, unverified email, 409 sub mismatch, flag-off). Run pytest in svc-iam tree, make pass.

## Validation
- pytest (svc-iam) + ruff on changed files + import resolution.

## Commit
- File-scoped (`git add backend/ CLAUDE.md docs/plans/google_auth/WAVE_PLAN_BACKEND.md`), logical conventional commits per wave. No push, no PR.
