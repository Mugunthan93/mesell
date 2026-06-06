# Sub-Session Prompt: §21 Extraction Path — VERIFICATION
# Wave 9 of 10 — VERIFICATION (parallel-safe with §15, §16, §22A)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-21-extraction-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §21 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §21 (Extraction Path).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION. Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §21 Extraction Path — per-module extraction-readiness + V1.5 landing zones
- Sub-session naming: `/rename meesell-backend-verification-21-extraction-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §21 (audit target; esp. §21.B extraction order, §21.C per-module extraction-readiness checklist).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §16.H extraction-preserves-call-sites contract.
3. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §7-§14 per-module §X.K extraction notes.
4. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
5. `/Users/mugunthansrinivasan/Project/mesell/backend/app/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §21:

1. **Every cross-module `domain.py` return type is JSON-serializable** (no UUID/datetime/Decimal without conversion). For each cross-module service method:
   - `customer.get_compliance_block(user_id) -> ComplianceBlock` — verify ComplianceBlock dataclass fields are JSON-friendly (str, int, list, dict, Pydantic-serializable).
   - `customer.get_profile_completeness(user_id) -> ProfileCompleteness` — same check.
   - `customer.assert_eligible_for_super_id` returns None or raises.
   - `category.fetch_schema(category_id) -> dict` — verify dict shape per §5A.B is JSON-friendly.
   - `category.get_commission(category_id) -> Decimal | None` — Decimal must serialize via Pydantic v2 with custom encoder.
   - `catalog.assert_product_ownership` returns None or raises.
   - `catalog.list_products(user_id, Pagination) -> list[ProductCard]` — ProductCard JSON-friendly.
   - `catalog.get_product_for_export(product_id, user_id) -> ExportSnapshot` — ExportSnapshot JSON-friendly.
   - `image.get_image_urls(product_id, user_id) -> list[ImageUrl]` — ImageUrl JSON-friendly.
   - `image.get_image_bytes(image_id) -> bytes` — bytes are NOT JSON-friendly, but this is consumed by export internally NOT across a network boundary in V1; flag as V1.5 concern.
   - V1.5 candidate: replace bytes-returning method with signed-URL-returning method for HTTP transport.

2. **Every `service.py` public method has a stable signature** — no `**kwargs`, no positional-only without defaults. `grep -A 2 "def [a-z]" backend/app/modules/<X>/service.py` reviewed per module.

3. **`core/extracted_clients/` directory does NOT exist in V1** — V1.5 landing zone — must be empty. `ls backend/app/core/extracted_clients/` should fail with "no such file or directory".

4. **Per-module extraction readiness — data-layer migration plan documented in section's §K** — read §7.K, §8.K, §9.K, §10.K, §11.K, §12.K, §13.K, §14.K. Confirm each has an extraction-notes paragraph documenting:
   - The owned tables.
   - The cross-module call signatures (which become HTTP/gRPC in V1.5).
   - The extraction order rank per §21.B (export easiest, catalog hardest).

5. **§21 8-step extraction order documented + consistent with §16.H** — verify §21.B order matches §16.H exactly: `export → dashboard → image → pricing → customer → category → iam → catalog`.

Plus universal: no regressions; STATUS_BACKEND.md has CONSTRUCTED entries.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code. Read-only audit.
- DO NOT amend LOCKED sections.
- DO NOT modify codebase to fix non-compliance — REPORT.
- DO NOT touch STATUS_MASTER.md.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

```
# §21 Extraction Path Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-21-extraction-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Cross-module domain.py JSON-serializable | PASS/FAIL/PARTIAL | per-type evidence |
| 2 | service.py signatures stable (no **kwargs) | PASS/FAIL | grep |
| 3 | core/extracted_clients/ absent (V1.5 landing zone) | PASS/FAIL | ls |
| 4 | Per-module §X.K extraction notes present | PASS/FAIL | per-section read |
| 5 | §21.B 8-step order consistent with §16.H | PASS/FAIL | doc compare |

## Non-compliance findings
## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save at `docs/audits/§21_extraction_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Cross-module method returns a non-JSON-serializable type (escalate — V1.5 blocker).
- service.py uses `**kwargs` (escalate — signature instability).
- `core/extracted_clients/` exists in V1 (escalate — premature V1.5 work).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-21-extraction-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-7 CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §21 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 9 of 10
- **Sequential dependency:** Wave 1-7 CONSTRUCTED.
- **Parallel-safe?:** Yes — parallel with §15, §16, §22A.
- **Expected duration estimate:** ~3-4 hours.
- **Acceptance verification by master:** read audit; spot-check 2-3 cross-module return types; on PASS proceed.
