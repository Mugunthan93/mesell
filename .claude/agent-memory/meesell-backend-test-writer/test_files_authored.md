# Backend test files authored

Ledger of every pytest file written: path, wave, feature slug, and the route(s) /
module it covers. Append after each task so the coordinator can see coverage
accrue and avoid re-specifying covered ground.

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| _(none yet — bootstrapped 2026-06-22)_ | | | |

## Wave-1 ledger (2026-06-22, PR #380)

Run result for the wave: **1314 passed / 28 skipped / 0 failed**.

New test files authored:

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `backend/tests/integration/test_iam_otp_rate_limit.py` | 1 | qa-wave-1 | iam — OTP send rate-limit (sliding window, Valkey-backed) |
| `backend/tests/.../test_autofill_shape_idempotent.py` | 1 | qa-wave-1 | catalog/ai — autofill response shape + idempotency |
| `backend/tests/.../test_export_zip_member_structure.py` | 1 | qa-wave-1 | export — ZIP member structure (**self-skip**, see deferred_coverage.md P1.11) |

Extended (added cases to) existing files:

| Path | Wave | Feature slug | Covers |
|---|---|---|---|
| `test_google_auth_integration` | 1 | qa-wave-1 | iam — google-auth verify / auto-link |
| `test_settlement_formula` | 1 | qa-wave-1 | pricing — settlement formula |
| `test_razorpay_webhook_router` | 1 | qa-wave-1 | payments — Razorpay webhook routing |
| `test_ai_ops_budget_cap` | 1 | qa-wave-1 | ai_ops — budget cap enforcement |
| `test_suggest_unit` | 1 | qa-wave-1 | catalog/ai — category suggest (unit) |
| `test_catalog_enum_validation_regression` | 1 | qa-wave-1 | catalog — enum validation regression (size_in_ltrs class) |
