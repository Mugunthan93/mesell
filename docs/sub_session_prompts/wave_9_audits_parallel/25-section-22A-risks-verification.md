# Sub-Session Prompt: §22A Risk Register & Mitigations — VERIFICATION
# Wave 9 of 10 — VERIFICATION (parallel-safe with §15, §16, §21)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-22A-risks-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §22A verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §22A (Risk Register & Mitigations).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION. Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §22A Risk Register — all 12 backend risk mitigations are present in code/architecture
- Sub-session naming: `/rename meesell-backend-verification-22A-risks-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §22A (audit target; esp. §22A.B 12 backend risks).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §6A (AI Ops), §15 (cross-cutting), §19 (CI linter), §14 (export Layer 3).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
4. `/Users/mugunthansrinivasan/Project/mesell/backend/app/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §22A — verify all 12 risk mitigations present:

1. **R1 — AI hallucination — 3-layer guardrail.** Verify Layer 1 prompt prefix in `ai_ops/guardrail.py`, Layer 2 enum re-validation in `ai_ops/client.py` (with up-to-2 retries), Layer 3 enum gate in `modules/export/service.py` (raises `ExportEnumValidationError`).

2. **R2 — Listing dashboard at scale (50+ products) — server-side pagination + cache.** Verify `dashboard.list_products` accepts `page` + `limit` query params; pagination happens server-side via `catalog.list_products` with SQL LIMIT/OFFSET.

3. **R3 — 9-vs-12 compliance shape — ComplianceStrategy dispatch.** Verify `modules/export/domain.py` has `ComplianceStrategy` ABC + `StandardComplianceStrategy` + `CollapsedComplianceStrategy` concretes; dispatch via `compliance_shape ∈ {"standard", "collapsed"}`.

4. **R4 — Field-name semantic drift between Meesho XLSX and canonical — round-trip golden fixtures.** Verify `backend/tests/integration/golden_round_trip/` has 15 fixture files.

5. **R5 — Long wizard fatigue — wizard step progress bar.** Backend-side: verify `category/service.py` schema response includes `wizard_step_count` per step. (Frontend renders the bar; backend populates the count.)

6. **R6 — FSSAI license required for Grocery — onboarding shows FSSAI requirement.** Verify `COMPLIANCE_EXTENSION_MAP` in `customer/domain.py` includes super_id=26 (Grocery) with `fssai_license_number` as compulsory.

7. **R7 — Meesho XLSX typo restoration — alias reverse map.** Verify `field_aliases` table has rows where `for_xlsx_export=TRUE` (read-only check; or grep for `for_xlsx_export` in alembic seed scripts).

8. **R8 — Multi-tenant isolation regression — isolation regression tests + scope_to_user linter.** Verify `backend/tests/integration/test_multi_tenant_isolation.py` exists; `tests/lint/check_scope_to_user.py` exists and passes.

9. **R9 — Valkey eviction during peak — fallback to PG on cache miss.** Verify `core/cache.py` `get_or_set_cache` falls back to the `fetch_fn` (which hits Postgres) on cache miss — never raises on Valkey unavailability beyond a logged warning.

10. **R10 — AI cost overrun — daily ₹500 cap + per-workload fallback.** Verify `ai_ops/budget_cap.py` has ₹500 cap + 80% alarm + 100% hard-stop; per-workload graceful fallback (smart_picker / autofill return 200 + fallback_offered; watermark = "skipped_budget").

11. **R11 — Refresh-token leak — HMAC pepper + Lua EVAL.** Verify `iam/service.py` uses `hmac.new(token, settings.REFRESH_TOKEN_PEPPER, sha256)` for allowlist key; Lua rotation script registered + EVALSHA used.

12. **R12 — Legacy `services/pricing_engine.py` import bug — deletion path locked.** Verify `backend/app/services/pricing_engine.py` does NOT exist (deleted during §12 dispatch).

**No risk is left unmitigated** — all 12 R items above should show PASS evidence in the audit.

Plus universal: no regressions; STATUS_BACKEND.md has CONSTRUCTED entries.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code. Read-only audit.
- DO NOT amend LOCKED sections.
- DO NOT touch STATUS_MASTER.md.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

```
# §22A Risk Register Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-22A-risks-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Risk | Mitigation present? | Evidence |
|---|---|---|---|
| R1 | AI hallucination 3-layer guardrail | PASS/FAIL | per-layer file paths |
| R2 | Server-side pagination + cache | PASS/FAIL | grep |
| R3 | ComplianceStrategy dispatch | PASS/FAIL | grep |
| R4 | 15 golden round-trip fixtures | PASS/FAIL | ls count |
| R5 | wizard_step_count populated | PASS/FAIL | schema test |
| R6 | FSSAI compulsory in compliance map | PASS/FAIL | grep |
| R7 | field_aliases.for_xlsx_export rows present | PASS/FAIL | seed inspection |
| R8 | Isolation regression + scope_to_user linter | PASS/FAIL | file + linter pass |
| R9 | Cache fallback to PG on miss | PASS/FAIL | grep |
| R10 | ₹500 cap + per-workload fallback | PASS/FAIL | budget_cap.py |
| R11 | HMAC pepper + Lua EVAL | PASS/FAIL | grep |
| R12 | services/pricing_engine.py DELETED | PASS/FAIL | ls |

## Non-compliance findings
## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save at `docs/audits/§22A_risks_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Any of 12 risks has no mitigation present (escalate — V1 risk surface).
- Mitigation present but ineffective (e.g. Layer 3 guardrail doesn't actually raise).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-22A-risks-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-7 CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §22A verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 9 of 10
- **Sequential dependency:** Wave 1-7 CONSTRUCTED.
- **Parallel-safe?:** Yes — parallel with §15, §16, §21.
- **Expected duration estimate:** ~3-4 hours.
- **Acceptance verification by master:** read audit; spot-check 2-3 risks; on PASS proceed to Wave 10.
