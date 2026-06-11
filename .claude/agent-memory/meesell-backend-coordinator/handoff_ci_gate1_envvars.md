# HANDOFF — backend → infra: CI Gate-1 env block missing 5 §5.D vars (Finding B)

**From:** `meesell-backend-coordinator`
**To:** `meesell-infra-builder`
**Date:** 2026-06-11
**Session:** mesell-ci-gate1-fix-session-1
**Inter-lead row:** OPEN on `docs/status/feature_board_backend.md` (Inter-lead requests open), 2026-06-11, 48h SLA.
**Scope note:** `.github/workflows/ci.yml` is INFRA-OWNED. Backend MUST NOT edit it directly — this memo is the request.

---

## Context

PR #73 (squash `1e95b2a`, merged to develop 2026-06-11) fixed CI Gate-1 pytest COLLECTION
(`ModuleNotFoundError: No module named 'app'`) by adding `pythonpath = .` to `backend/pytest.ini`.
With the `import app` barrier removed, the **next** CI failure point is exposed: `app.shared.config`
calls `SystemExit` at import/boot when any §5.D-required env var is unset.

## Finding B — the 5 missing env vars

The Gate-1 (`unit`) job `env:` block in `ci.yml` currently injects these test-safe dummies:
`SECRET_KEY, JWT_SECRET, MSG91_AUTH_KEY, MSG91_TEMPLATE_ID, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
RAZORPAY_WEBHOOK_SECRET, REFRESH_TOKEN_PEPPER, AUDIT_PII_SALT, GEMINI_API_KEY, APP_ENV`.

It is **MISSING** these 5 §5.D-required vars:

1. `GCS_BUCKET`
2. `GCS_PROJECT_ID`
3. `LANGFUSE_PUBLIC_KEY`
4. `LANGFUSE_SECRET_KEY`
5. `CORS_ALLOWED_ORIGINS`

**Independently reproduced** from a clean worktree (PYTHONPATH unset, post-fix pytest.ini):
```
FATAL: required env var(s) empty or unset: REFRESH_TOKEN_PEPPER, MSG91_AUTH_KEY, MSG91_TEMPLATE_ID,
RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET, GEMINI_API_KEY, GCS_BUCKET,
GCS_PROJECT_ID, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS
(see BACKEND_ARCHITECTURE.md §5.D for the full registry)
```
The local box already has the other 8 in its `.env`, so only the 5 above remain after intersecting
with what Gate-1 injects. On the CI runner (clean env), config will SystemExit naming the union — but
the 5 above are the deltas the Gate-1 `env:` block does not yet supply.

## Request

1. Add dummy / test-safe values for the 5 vars above to the Gate-1 `env:` block in `ci.yml`. Suggested
   safe placeholders (match existing `ci-dummy-*` style; CORS must be a NON-`*` JSON list per §5.D lock):
   - `GCS_BUCKET: ci-dummy-bucket`
   - `GCS_PROJECT_ID: ci-dummy-project`
   - `LANGFUSE_PUBLIC_KEY: ci-dummy-langfuse-public`
   - `LANGFUSE_SECRET_KEY: ci-dummy-langfuse-secret`
   - `CORS_ALLOWED_ORIGINS: '["http://localhost:4200"]'`  (NEVER `*` — §5.D `CORS_ALLOWED_ORIGINS` lock)
2. **Check Gates 2 (smoke), 4 (integration), 5 (golden_roundtrip) too** — they import the same
   `app.shared.config` at boot, so they likely have the same gap in their own `env:` blocks. Audit all
   gate `env:` blocks against the §5.D required-field registry, not just Gate 1.
3. No new SECRETS needed — these are dummies in the workflow `env:`, not GitHub Secrets. (Production values
   flow via Secret Manager at deploy, never into Actions, per DEVOPS_ARCHITECTURE.md §8.2.)

## Authoritative reference

- §5.D required-field registry: `docs/BACKEND_ARCHITECTURE.md` (env-var tables; validator raises SystemExit
  on missing required field — locked model_validator after-mode pattern).
- The SystemExit message itself lists the full required set — diff against any gate `env:` block to find gaps.

## Not in this handoff

- The `pythonpath`/collection fix itself — DONE (PR #73 + repair PR #75).
- Finding A (zero `unit`-marked tests) — that is a BACKEND debt, not infra; tracked in STATUS_BACKEND.md,
  scheduled as a future marker-classification task. NOT part of this request.
- Branch-protection activation — stays DEFERRED (infra lane) until pipeline green.
