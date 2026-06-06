# Sub-Session Prompt: §0 Architectural Premises — VERIFICATION
# Wave 8 of 10 — VERIFICATION (parallel-safe with §1, §2, §3, §17)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-0-premises-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §0 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §0 (Architectural Premises).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION (audit/compliance). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §0 Architectural Premises (14 founder-locked decisions + D1-D4 honored in code)
- Sub-session naming: `/rename meesell-backend-verification-0-premises-1`

You write NO production code. You produce an audit report.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Read `/Users/mugunthansrinivasan/Project/mesell/` files only. Touch no project outside MeeSell.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0 (the section being audited).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` ALL constructed sections (§4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11, §12, §13, §14, §18, §19, §20 — all 16 construction sections).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` — confirm all 16 construction sections report CONSTRUCTED.
4. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_MASTER.md` — confirm prior wave milestones reached.
5. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` — the constructed codebase being audited.
6. `/Users/mugunthansrinivasan/Project/mesell/backend/tests/` — the tests being audited.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

You audit the codebase against §0's locked claims. Deliverable is a compliance report.

Audit checklist for §0:

1. **14 founder-locked decisions honored in code.** Inspect §0.G and verify each of the 14 decisions (D1 burn-and-rebuild, D2 13-not-8-models, D3 rls-deferred, D4 specialist-not-master, plus 10 from MVP_ARCH §12 + §15) has a traceable code artifact. Examples: D2 confirmed by `ls backend/app/shared/models/ | wc -l` returning 13 + 1 (`__init__.py`); D3 confirmed by no RLS migration in `alembic/versions/`.

2. **D1-D4 verifiable specifically:**
   - **D1:** No `.legacy.py.bak` files exist anywhere — `find backend/ -name "*.legacy.py.bak"` returns empty.
   - **D2:** `ADVANCED_CANONICAL_NAMES = {"group_id"}` exactly one element — grep `ADVANCED_CANONICAL_NAMES` in `i18n/` or wherever locked at §5A.F.
   - **D3:** §3.4 amendment applied — verify MVP_ARCHITECTURE.md §3.4 carries the construction-phase amendment block (cross-doc check).
   - **D4:** No specialist code in master-session history — review the git log to confirm specialist commits are present (specialist dispatch worked).

3. **27-endpoint count verifiable** via `grep -rE "@(api|router)\.(get|post|patch|delete|put)\(" backend/app/modules/ | wc -l` returning at least 27 (plus 2 infrastructure: `/me` + `/webhooks/razorpay`). Cross-check against §17 inventory.

4. **13-table baseline matches Alembic head `f31c75438e61`** — run `alembic current` (or `alembic heads`) and verify head matches; verify `\dt` against live DB shows 13 tables.

5. **Backend tree clean-state baseline preserved** — verify §0.E lock holds:
   - `backend/app/main.py` mounts ALL constructed routers (auth/customer/category/catalog/image/pricing/dashboard/export — 8 module routers + 2 infrastructure surfaces).
   - 42/42 schema tests + 7/7 boot integration tests still PASS (regressions = critical).

6. **All 6 philosophy commitments visible in code (§0.H):**
   - **M7 enum guardrail** — Layer 2 enum re-validation in `ai_ops/guardrail.py` per §6A.E.
   - **M9 i18n** — `i18n/` package with ~50 message IDs.
   - **M10 Meesho leak rules** — M10 forbidden symbols ONLY in `modules/export/` + `adapters/gcs.py` per §14.J + §19 Contract 9.
   - **F3 3-layer guardrail** — Layer 1 prompt prefix + Layer 2 enum re-validation + Layer 3 export enum gate.
   - **F4 9-not-12 compliance** — `customer.get_compliance_block` returns exactly 9 fields (Standard) or 3 (Collapsed via export).
   - **F5 every field has help_text** — every `fields[]` entry in `schema_jsonb` has the `help_text` key (verifiable in `category/test_schema_envelope_conformance.py`).

Plus universal verification checks:

1. No regressions — `pytest backend/tests/test_app_boot_integration.py` PASS.
2. No regressions — `pytest backend/tests/test_database.py` PASS.
3. All import-linter contracts PASS.
4. STATUS_BACKEND.md has CONSTRUCTED entries for §4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11, §12, §13, §14, §18, §19, §20.

═══════════════════════════════════════════════════════════════
HARD RULES — WHAT YOU MAY NOT DO
═══════════════════════════════════════════════════════════════

- DO NOT write production code. Verification is READ-ONLY against `backend/app/`.
- DO NOT amend any LOCKED section of BACKEND_ARCHITECTURE.md.
- DO NOT dispatch construction specialists.
- DO NOT modify codebase to fix non-compliance — REPORT non-compliance; master decides remediation.
- DO NOT touch STATUS_MASTER.md.
- DO NOT touch any project outside MeeSell.

You MAY:
- Read any file under `/Users/mugunthansrinivasan/Project/mesell/`.
- Run `grep`, `find`, `pytest --collect-only`, `ruff check --no-fix`, `mypy`, import-linter.
- Run the §22 acceptance checklist queries (read-only).
- Append an audit-report entry to `STATUS_BACKEND.md`.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT — Audit Report
═══════════════════════════════════════════════════════════════

Produce a markdown audit report:

```
# §0 Architectural Premises Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-0-premises-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | 14 founder-locked decisions honored | PASS/FAIL/N/A | <grep results, file paths> |
| 2 | D1 no .legacy.py.bak files | PASS/FAIL | `find` result |
| 3 | D2 ADVANCED_CANONICAL_NAMES = {"group_id"} | PASS/FAIL | grep result |
| 4 | D3 §3.4 amendment | PASS/FAIL | doc state |
| 5 | D4 specialist commits in git log | PASS/FAIL | git log excerpt |
| 6 | 27-endpoint count | PASS/FAIL | grep count |
| 7 | 13-table baseline, head f31c75438e61 | PASS/FAIL | alembic current + \dt |
| 8 | backend tree clean-state baseline | PASS/FAIL | route count + test pass |
| 9 | M7 enum guardrail | PASS/FAIL | file path + line |
| 10 | M9 i18n | PASS/FAIL | message_en.py key count |
| 11 | M10 forbidden symbols only in export+gcs | PASS/FAIL | grep result |
| 12 | F3 3-layer guardrail | PASS/FAIL | file paths |
| 13 | F4 9-not-12 compliance | PASS/FAIL | service signature + test |
| 14 | F5 every field has help_text | PASS/FAIL | schema_jsonb test result |

## Non-compliance findings (if any)

For each failure:
- **Finding:** <one-line>
- **Locked claim:** <quote from §0>
- **Actual code:** <grep result or file:line>
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW
- **Recommended remediation:** <which construction sub-session needs to amend>

## Verdict rationale

<2-3 sentences>

## Hand-back to master

<list of items master must orchestrate>
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

When audit completes:

1. Save the audit report at `/Users/mugunthansrinivasan/Project/mesell/docs/audits/§0_premises_audit_<YYYY-MM-DD>.md`.

2. Append a one-paragraph UPDATE block to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §0 Premises AUDITED ===
   Verdict: PASS / PARTIAL / FAIL
   Critical findings: <count>
   Audit report: docs/audits/§0_premises_audit_<YYYY-MM-DD>.md
   Hand-back to master: <list>
   =========
   ```

3. Report back to master (under 300 words):
   - Section + verdict.
   - Critical/high findings summary.
   - Recommended remediation.
   - "Audit complete. Standing by for master decision."

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS (STOP AND REPORT TO MASTER)
═══════════════════════════════════════════════════════════════

- The locked claim being audited is itself ambiguous (e.g. §0.H "M10 Meesho leak rules" enforced at code level vs documentation level).
- A prior-wave construction section is missing or unconstructed (audit cannot run against missing code).
- Audit finds the locked contract is technically impossible in V1 stack.
- More than 5 critical findings (escalate before continuing — likely systemic issue).

Escalation format same as construction sub-sessions.

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-0-premises-1`
2. Read REQUIRED READING.
3. Confirm STATUS_BACKEND.md shows all 16 construction sections CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §0 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 8 of 10
- **Sequential dependency:** All 16 construction sections CONSTRUCTED (Waves 1-7 complete).
- **Parallel-safe?:** Yes — runs in parallel with §1, §2, §3, §17 (all 5 Wave 8 audits are read-only).
- **Expected duration estimate:** ~3-5 hours.
- **Acceptance verification by master:** read the audit report; spot-check 2-3 random checklist items; verify the file exists at `docs/audits/§0_premises_audit_<date>.md`; update STATUS_MASTER.md with audit result; on PASS proceed to Wave 9; on PARTIAL/FAIL trigger remediation per protocol §5.1B.
