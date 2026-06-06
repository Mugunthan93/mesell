# Sub-Session Prompt: §16 Inter-Module Communication Rules — VERIFICATION
# Wave 9 of 10 — VERIFICATION (parallel-safe with §15, §21, §22A)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-16-rules-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §16 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §16 (Inter-Module Communication Rules).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION. Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §16 Inter-Module Communication Rules — 8 ✓ matrix + 4 file-level rules + §16.E import-linter contracts + 2 documented structural exceptions
- Sub-session naming: `/rename meesell-backend-verification-16-rules-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §16 (audit target; esp. §16.B 8 allowed cross-module service calls, §16.C 4 file-level rules, §16.E import-linter TOML, §16.F 2 documented structural exceptions).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §19 CI linter construction (§19.C — 10 CI contracts).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
4. `/Users/mugunthansrinivasan/Project/mesell/backend/app/`, `backend/tests/lint/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §16:

1. **8 allowed cross-module calls present in code** per §16.B:
   - `catalog → customer.service.assert_eligible_for_super_id` ✓
   - `catalog → category.service.fetch_schema` ✓
   - `pricing → catalog.service.assert_product_ownership` ✓
   - `pricing → category.service.get_commission` ✓
   - `image → catalog.service.assert_product_ownership` ✓
   - `dashboard → catalog.service.list_products` ✓
   - `dashboard → customer.service.get_profile_completeness` ✓
   - `export → multiple services (customer + category + catalog + image)` ✓
   - Verify via grep across each consumer module's service.py.

2. **`repository.py` PRIVATE** — no cross-module imports. `grep -rn "from app.modules.<X>.repository" backend/app/modules/` where X ≠ self returns nothing for every module.

3. **`schemas.py` PRIVATE** — no cross-module imports. `grep -rn "from app.modules.<X>.schemas" backend/app/modules/` where X ≠ self returns nothing.

4. **`adapters.gemini` ONLY consumed via `ai_ops.client`** — `grep -rn "from app.adapters.gemini" backend/app/modules/` returns nothing; the only legitimate import is in `ai_ops/client.py`.

5. **`ai_ops.*` ONLY consumed by category/catalog/image** — `grep -rn "from app.ai_ops" backend/app/modules/` shows hits ONLY in modules/category, modules/catalog, modules/image (NOT in iam, customer, pricing, dashboard, export).

6. **`router.py` + `tasks.py` never cross-module imported** — only `app/main.py` registers routers; only `app/workers/celery_app.py` registers tasks. Verify: `grep -rn "from app.modules.<X>.router\|from app.modules.<X>.tasks" backend/app/modules/` returns nothing (cross-imports forbidden). The allowlist is `app/main.py` for routers + `app/workers/celery_app.py` for tasks.

7. **Dashboard no-repository exception allowlisted** in `tests/lint/import_rules.toml` per §16.F.1 + §19 Contract 8 allowlist.

8. **Category no-user_id exception allowlisted** in `tests/lint/check_scope_to_user.py` per §16.F.2 + §19 Contract 8 allowlist.

9. **All 7 import-linter contracts + 3 custom AST scanners pass in CI** — run the linter + 3 scanners:
   - `lint-imports --config tests/lint/import_rules.toml` returns clean.
   - `python -m tests.lint.check_scope_to_user` returns clean.
   - `python -m tests.lint.check_no_meesho_symbols_outside_export` returns clean.
   - `python -m tests.lint.check_message_id_regex` returns clean.

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
# §16 Inter-Module Rules Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-16-rules-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | 8 allowed cross-module calls present | PASS/FAIL | grep results |
| 2 | repository.py PRIVATE (no cross-imports) | PASS/FAIL | grep |
| 3 | schemas.py PRIVATE | PASS/FAIL | grep |
| 4 | adapters.gemini only via ai_ops.client | PASS/FAIL | grep |
| 5 | ai_ops.* only by category/catalog/image | PASS/FAIL | grep |
| 6 | router.py + tasks.py never cross-imported | PASS/FAIL | grep |
| 7 | Dashboard no-repo exception allowlisted | PASS/FAIL | TOML content |
| 8 | Category no-user_id exception allowlisted | PASS/FAIL | scanner content |
| 9 | All 10 CI contracts PASS | PASS/FAIL | lint output |

## Non-compliance findings
## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save at `docs/audits/§16_rules_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Any cross-module repository import (CRITICAL — boundary breach).
- adapters.gemini imported directly by a domain module (CRITICAL — §3.G violation).
- ai_ops.* imported by a non-AI-consumer module (e.g. pricing or export — CRITICAL).
- CI contract fails (escalate — likely construction regression).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-16-rules-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-7 CONSTRUCTED (esp. §19 with the CI linters).
4. Report "Audit context loaded. Ready to begin §16 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 9 of 10
- **Sequential dependency:** Wave 1-7 CONSTRUCTED (esp. §19 with the CI linter wiring).
- **Parallel-safe?:** Yes — parallel with §15, §21, §22A.
- **Expected duration estimate:** ~2-4 hours.
- **Acceptance verification by master:** read audit; verify all 10 CI contracts PASS; on PASS proceed.
