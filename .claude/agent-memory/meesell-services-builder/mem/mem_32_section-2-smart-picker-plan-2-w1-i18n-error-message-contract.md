## Section-2 (smart-picker) Plan 2-W1 — i18n error message contract (2026-06-15, branch feature/section-2/backend)

### Scope
HYBRID Step-2 specialist dispatch (mesell-section-2-backend-session-1). Worktree
`/tmp/mesell-wt/section-2-backend` (separate checkout — NOT the same tree as
/Users/.../Project/mesell; ALWAYS edit the worktree path for section work).

### What I did
- Change A: `validation_message_id` 2-segment `"rate_limit.exceeded"` → 3-segment
  `"rate_limit.window.exceeded"` in `RateLimitExceededError` class attr + the
  `_build_rate_limit_response` envelope, in BOTH the monolith
  `backend/app/core/middleware/rate_limit_mw.py` AND `backend/services/svc-category/app/core/middleware/rate_limit_mw.py`.
  The `code = "rate_limit.exceeded"` machine slug is NOT touched (not governed by the 3-segment regex).
- Change B: added `"rate_limit.window.exceeded"` to `VALIDATION_MESSAGES` near the plan_guard/rate_limit
  cross-cutting section; fixed `validation.suggest_q.too_short_or_long` copy "2 and 60" → "1 and 500"
  (matches the enforced 1–500 code bound), in BOTH `backend/app/i18n/messages_en.py` +
  `backend/services/svc-category/app/i18n/messages_en.py`.
- Change C honoured: did NOT register `smart_picker.ai.unavailable` / `smart_picker.budget.exceeded`
  (those are HTTP 200 + fallback_offered=true paths, not error envelopes).
- New test `backend/tests/test_section2_i18n_contract.py` (5 funcs / 10 cases) — 10/10 PASS.
- Collateral: `backend/tests/test_core_rate_limit_mw.py:66` assertion updated to the new 3-segment value
  (the middleware it tests no longer emits the old value). 3/3 PASS against local Valkey 6379.

### Reusable learnings
- **Section worktrees are SEPARATE checkouts.** The dispatch gives a worktree path under /tmp/mesell-wt/.
  Files read from /Users/.../Project/mesell may DIFFER from the worktree. Edit the worktree only.
- **Test env to import `app.shared.config.settings`**: it SystemExits at import unless ~14 env vars are set
  (REFRESH_TOKEN_PEPPER, MSG91_AUTH_KEY, MSG91_TEMPLATE_ID, RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET,
  GEMINI_API_KEY, GCS_BUCKET, GCS_PROJECT_ID, LANGFUSE_PUBLIC_KEY/SECRET_KEY, AUDIT_PII_SALT,
  CORS_ALLOWED_ORIGINS, JWT_SECRET). Export dummies before pytest.
- **Use the PROJECT venv python (3.11) not system python3 (3.9).** System 3.9 chokes on `Mapped[str | None]`
  declarative annotations at model import (MappedAnnotationError). Path: /Users/.../mesell/backend/.venv/bin/python.
  It resolves `app` via PYTHONPATH=<worktree>/backend.
- **conftest defaults VALKEY_URL to :6381** (an SSH tunnel). Local Valkey is :6379. The use_live_valkey
  fixture precedence is TEST_VALKEY_URL > VALKEY_URL > CORE_TEST_VALKEY_URL > bare 6379. To run rate-limit
  tests locally: export VALKEY_URL=redis://localhost:6379/15 TEST_VALKEY_URL=redis://localhost:6379/0.
  Without a reachable Valkey the rate-limit mw fails OPEN (200), so 429-expecting tests fail spuriously.

### DISCREPANCY flagged to coordinator (Step-3 gate)
Spec Check-1 wants ZERO tree-wide hits of `validation_message_id.*rate_limit.exceeded`, but Change A scoped
ONLY main + svc-category. 7 OTHER svc trees (svc-catalog/customer/dashboard/export/iam/image/pricing) still
carry the old 2-segment value. Left untouched per "no more, no less". Flagged in STATUS_BACKEND for a possible
follow-up sweep wave.

### Committed
`960ed70 sec2: add/verify i18n message contract (Plan 2-W1)` on feature/section-2/backend (pushed, no PR —
coordinator gates Step 3).

---
