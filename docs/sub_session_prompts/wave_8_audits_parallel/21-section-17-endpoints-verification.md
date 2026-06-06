# Sub-Session Prompt: §17 Endpoint Inventory — VERIFICATION
# Wave 8 of 10 — VERIFICATION (parallel-safe with §0, §1, §2, §3)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-17-endpoints-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §17 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §17 (Endpoint Inventory).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION. Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §17 Endpoint Inventory — 27 contract endpoints + 2 infrastructure (`/me` + `/webhooks/razorpay`)
- Sub-session naming: `/rename meesell-backend-verification-17-endpoints-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §17 (the section being audited; esp. §17.B 27-endpoint master registry + 2 infrastructure surfaces, §17.C auth distribution, §17.D rate limit distribution, §17.E plan guard distribution, §17.F audit event distribution).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §7 through §14 (8 domain modules) — per-module endpoint listings.
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
4. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` (esp. all 8 modules' router.py files + `app/main.py`).

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §17:

1. **All 27 contract endpoints mounted** verifiable via OpenAPI:
   - Run `python -c "from app.main import app; [print(r.path) for r in app.routes]"` (or hit `/openapi.json` against running instance).
   - Cross-check the list against §17.B master registry (per-module breakdown):
     - iam: 4 endpoints (otp/send, otp/verify, refresh, logout)
     - customer: 5 endpoints
     - category: 5 endpoints
     - catalog: 6 endpoints
     - image: 2 endpoints
     - pricing: 1 endpoint
     - dashboard: 1 endpoint
     - export: 2 endpoints
     - **27 total contract endpoints.**

2. **2 infrastructure endpoints mounted**: `GET /api/v1/auth/me` and `POST /api/v1/webhooks/razorpay` (NOT in the 27-contract count but required for infrastructure).

3. **Each endpoint has the locked auth posture** per §17.C distribution (22 JWT / 2 cookie / 2 none / 1 HMAC):
   - JWT (22): all authenticated endpoints (per-module count adds to 22).
   - Cookie (2): `/auth/refresh` + `/auth/logout` (refresh cookie is the credential, not JWT).
   - None (2): `/auth/otp/send` + `/auth/otp/verify` (public).
   - HMAC (1): `/webhooks/razorpay`.
   - Verify by inspecting each route handler's `Depends(get_current_user)` vs cookie-based auth vs no-auth.

4. **Each endpoint has the locked rate-limit decorator** per §17.D distribution. Verify via grep `@rate_limit` per endpoint. Spot checks:
   - `/auth/otp/send` → 3/h key=phone.
   - `/auth/otp/verify` → 10/h key=phone.
   - `/auth/refresh` → 60/h key=refresh_cookie_user_id.
   - `/category/suggest` → 100/h Smart Picker hourly (also plan_guard).
   - `/products/{id}/images` POST → 10/min per user.
   - `/products` GET (dashboard) → per-IP only (no decorator).

5. **Each endpoint emits the locked audit event** per §17.F distribution (or is in the documented NONE / direct-write set):
   - NONE (read-only): `/me`, `/profile`, `/profile/required-fields`, `/categories`, `/categories/{id}/schema`, `/category/browse`, `/categories/{id}/field-enum/{name}`, `/products/{id}/preview`, `/products/{id}/draft`, `/products` (dashboard list).
   - Direct ORM write (locked exceptions): `verify_otp`, `refresh`, `logout`, `image.precheck.completed`, `export.generate.*`, `ai_ops.cost_record`.
   - Middleware-emitted (post-commit): all 2xx PATCH/POST/DELETE outside the direct-write set.

6. **Plan_guard 4 resources locked at §4.E enforced on the 3 plan-gated endpoints**:
   - `category.suggest_hourly` (100/h Smart Picker) on `POST /category/suggest`.
   - `autofill_hourly` (50/h) on `POST /products/{id}/autofill`.
   - `active_products_count` (100 active) on `POST /products`.
   - Autosave coalescing (5-min audit) on `PATCH /products/{id}` with `X-Autosave: true` (§4.E resource #4).

Plus universal: no regressions; STATUS_BACKEND.md has CONSTRUCTED entries.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code.
- DO NOT amend LOCKED sections.
- DO NOT modify codebase to fix non-compliance — REPORT.
- DO NOT touch STATUS_MASTER.md.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

```
# §17 Endpoint Inventory Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-17-endpoints-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | 27 contract endpoints mounted | PASS/FAIL | OpenAPI route list |
| 2 | 2 infrastructure endpoints mounted | PASS/FAIL | route list |
| 3 | Auth posture (22 JWT / 2 cookie / 2 none / 1 HMAC) | PASS/FAIL | per-route inspection |
| 4 | Rate-limit decorators correct | PASS/FAIL | grep |
| 5 | Audit event distribution correct | PASS/FAIL | per-route inspection |
| 6 | Plan_guard 4 resources enforced | PASS/FAIL | grep |

## Non-compliance findings
## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save audit at `docs/audits/§17_endpoints_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Endpoint count differs from 27+2 (escalate — either missing endpoint or extra unauthorised endpoint).
- Wrong auth posture on critical endpoint (e.g. payment endpoint missing JWT).
- Missing rate-limit on high-abuse-risk endpoint (escalate — security risk).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-17-endpoints-1`
2. Read REQUIRED READING.
3. Confirm all 8 domain modules + iam infrastructure CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §17 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 8 of 10
- **Sequential dependency:** All 8 domain modules + iam infrastructure CONSTRUCTED.
- **Parallel-safe?:** Yes — parallel with §0, §1, §2, §3.
- **Expected duration estimate:** ~2-3 hours.
- **Acceptance verification by master:** read audit; spot-check endpoint count; on PASS proceed to Wave 9.
