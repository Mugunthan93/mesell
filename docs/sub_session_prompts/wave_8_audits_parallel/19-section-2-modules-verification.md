# Sub-Session Prompt: §2 Module Catalog — VERIFICATION
# Wave 8 of 10 — VERIFICATION (parallel-safe with §0, §1, §3, §17)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-2-modules-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §2 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §2 (Module Catalog).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION (audit). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §2 Module Catalog — verify 8 domain modules + 5 non-domain layers + 8 ✓ cross-module matrix + per-module write/read tables
- Sub-session naming: `/rename meesell-backend-verification-2-modules-1`

You write NO production code. You produce an audit report.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §2 (the section being audited; esp. §2.D cross-module reference matrix).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §7 through §14 (8 domain modules), §4 + §5 + §5A + §6 + §6A (5 non-domain layers — though §3 counts ai_ops + i18n as additional structural peers, §2 enumerates adapters/core/shared as the 3 original non-domain layers).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
4. `/Users/mugunthansrinivasan/Project/mesell/backend/app/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §2:

1. **All 8 modules + 5 non-domain layers exist in `backend/app/`**:
   - 8 domain modules under `backend/app/modules/`: iam, customer, category, catalog, image, pricing, dashboard, export.
   - 5 non-domain layers at `backend/app/` top-level: adapters/, core/, shared/, ai_ops/, i18n/. (The §3 amendment elevates ai_ops + i18n to top-level peers; §2 originally listed 3 non-domain layers — adapters, core, shared.)
   - `ls backend/app/` should show: `__init__.py`, `main.py`, `modules/`, `adapters/`, `core/`, `shared/`, `ai_ops/`, `i18n/`, `workers/`.

2. **8 ✓ cross-module matrix honored** (no ✗ cell crossed). Verify the 8 allowed calls present in code:
   - `catalog → customer.service.assert_eligible_for_super_id` (grep `customer.service.assert_eligible_for_super_id` in `modules/catalog/`).
   - `catalog → category.service.fetch_schema` (grep).
   - `pricing → catalog.service.assert_product_ownership` (grep).
   - `pricing → category.service.get_commission` (grep).
   - `image → catalog.service.assert_product_ownership` (grep).
   - `dashboard → catalog.service.list_products` (grep).
   - `dashboard → customer.service.get_profile_completeness` (grep).
   - `export → customer.service.get_compliance_block` + `category.service.fetch_schema` + `catalog.service.get_product_for_export` + `image.service.get_image_bytes` (export consumes 4; total cross-module call count = 8 allowed + 3 export-extras = 11 with export's calls — but §2.D counts the 8-row category cross-module column). Reconcile against §2.D.

3. **Per-module owned-table writes match.** Verify only the locked owners INSERT/UPDATE the table:
   - `customer` writes `seller_profile` (no other module's repository.py touches it).
   - `iam` writes `users`.
   - `catalog` writes `catalogs`, `products`, `product_drafts`.
   - `image` writes `product_images`.
   - `pricing` writes `pricing_calcs` (append-only).
   - `export` writes `exports`.
   - `audit_events` — multiple modules write directly per documented exceptions (§6A.D, §7.I, §11.J).
   - `categories`, `templates`, `field_enum_values`, `field_aliases` — GLOBAL, no runtime writes.
   - Verify via `grep -rn "INSERT INTO\|update.*set\|self.db.add\|db.execute(insert\|db.execute(update" backend/app/modules/<module>/repository.py` and cross-check ownership.

4. **Per-module global-table reads match.** Verify only `category` reads `templates` / `categories` / `field_enum_values` / `field_aliases` directly. Other modules consume via `category.service.*`.

5. **Dashboard has NO `repository.py`** — `ls backend/app/modules/dashboard/repository.py` returns "no such file" (structural exception per §13.D + §16.F.1).

6. **Category repository has NO `user_id` parameter** — grep `def ` in `modules/category/repository.py` shows no method takes `user_id` (structural exception per §16.F.2; categories/templates/field_enum_values/field_aliases are GLOBAL).

7. **Adapters consumed only by enumerated modules** per §2.9:
   - `adapters.gemini` → consumed via `ai_ops.client` ONLY (no direct domain import).
   - `adapters.msg91` → consumed by `iam` ONLY.
   - `adapters.gcs` → consumed by `image` + `export` ONLY.
   - `adapters.razorpay` → consumed by `iam` ONLY.
   - `adapters.langfuse` → consumed by `ai_ops.client` ONLY.

Plus universal: no regressions; import-linter PASS; STATUS_BACKEND.md has prior CONSTRUCTED entries.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code. Read-only audit.
- DO NOT amend any LOCKED section.
- DO NOT dispatch construction specialists.
- DO NOT modify codebase to fix non-compliance — REPORT it.
- DO NOT touch STATUS_MASTER.md.
- DO NOT touch any project outside MeeSell.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

```
# §2 Module Catalog Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-2-modules-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | 8 modules + 5 layers exist | PASS/FAIL | ls output |
| 2 | 8 ✓ matrix honored | PASS/FAIL | grep results |
| 3 | Per-module owned-table writes | PASS/FAIL | grep INSERT/UPDATE |
| 4 | Per-module global-table reads | PASS/FAIL | grep |
| 5 | Dashboard NO repository.py | PASS/FAIL | ls |
| 6 | Category NO user_id param | PASS/FAIL | grep |
| 7 | Adapters consumed only by enumerated modules | PASS/FAIL | grep |

## Non-compliance findings
<per-finding>

## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save audit at `docs/audits/§2_modules_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- ✗ matrix cell crossed (CRITICAL — module isolation violation).
- Owned-table written by wrong module (CRITICAL).
- Dashboard has repository.py (structural exception broken).
- Category repository has user_id (structural exception broken).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-2-modules-1`
2. Read REQUIRED READING.
3. Confirm all 8 modules CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §2 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 8 of 10
- **Sequential dependency:** All 8 domain modules + 5 non-domain layers CONSTRUCTED.
- **Parallel-safe?:** Yes — parallel with §0, §1, §3, §17.
- **Expected duration estimate:** ~2-3 hours.
- **Acceptance verification by master:** read audit report; spot-check matrix compliance; on PASS proceed.
