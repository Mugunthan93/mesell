# Sub-Session Prompt: §15 Cross-Cutting Walkthrough — VERIFICATION
# Wave 9 of 10 — VERIFICATION (parallel-safe with §16, §21, §22A)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-15-crosscutting-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §15 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §15 (Cross-Cutting Walkthrough).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION. Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §15 Cross-Cutting Walkthrough — 10 cross-cutting concerns wired across all modules
- Sub-session naming: `/rename meesell-backend-verification-15-crosscutting-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §15 (audit target; esp. §15.B multi-tenancy, §15.C caching, §15.D search & indexing, §15.E audit log + autosave coalescing, §15.F AI operations, §15.G plan guard, §15.H session management refresh allowlist, §15.I CSRF posture, §15.J observability, §15.K i18n).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §4, §6A, §7-§14 (constructed source).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
4. `/Users/mugunthansrinivasan/Project/mesell/backend/app/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §15 (10 cross-cutting concerns):

1. **Multi-tenancy 3-layer defense present** per §15.B:
   - Layer 1: `scope_to_user(user_id)` in 7 repositories (iam, customer, catalog, image, pricing, export — categories has documented exception; dashboard has no repo).
   - Layer 2: `assert_product_ownership` cross-call enforced (catalog.service + consumed by image/pricing/dashboard/export).
   - Layer 3: GCS path prefix `{user_id}/{product_id}/...` enforced in adapters/gcs.py + image/tasks.py + export/tasks.py.

2. **Caching `core/cache.py` is sole Valkey DB 3 access** per §15.C — `grep -rn "get_valkey_cache\|VALKEY_DB=3" backend/app/` should show ONLY `core/cache.py` consuming `get_valkey_cache()`. Other modules consume via `core/cache.py`.

3. **pg_trgm GIN indexes live** per §15.D — `\di` on Postgres shows the 3 GIN trgm indexes from session 2 G4 (idx_categories_path_trgm + 2 others).

4. **Audit middleware + 7 documented direct-write exceptions** per §15.E:
   - Middleware: `core/middleware/audit_mw.py` post-commit write on 2xx.
   - Direct-write exceptions (7): cost_tracker (§6A.D), verify_otp / refresh / logout (§7.I), image.precheck.completed (§11.J), export.generate.* (§14.J).

5. **AI Ops single import surface (`ai_ops.client.call_gemini`) + 3 workloads + 3-layer guardrail + ₹500 cap + graceful fallback per workload** per §15.F:
   - Single import surface: `grep -rn "adapters.gemini" backend/app/modules/` returns nothing.
   - 3 workloads: `Literal["smart_picker", "autofill", "watermark"]` in `ai_ops/client.py`.
   - 3-layer guardrail: Layer 1 prefix in guardrail.py, Layer 2 enum re-validation, Layer 3 enum gate in export.service.
   - ₹500 cap: present in `ai_ops/budget_cap.py` with Asia/Kolkata timezone.
   - Graceful fallback per workload: smart_picker / autofill return 200 + fallback_offered; watermark = "skipped_budget".

6. **Plan_guard 4 resources enforced** per §15.G:
   - smart_picker_hourly=100/h, autofill_hourly=50/h, active_products_count=100, autosave_coalescing_5min.

7. **FE-D5 refresh allowlist HMAC + Lua EVAL working** per §15.H:
   - HMAC-with-pepper keyspace `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` in `iam/service.py`.
   - Lua rotation script registered + EVALSHA used + EVAL fallback on NOSCRIPT.

8. **CSRF posture verified (no CSRF middleware)** per §15.I — `grep -rn "csrf\|CSRF" backend/app/` returns no middleware reference. Refresh cookie is `SameSite=Strict` which is the CSRF defense.

9. **Observability `request_id` + Prometheus + LangFuse all firing** per §15.J:
   - `request_id` propagation: `X-Request-ID` middleware in `core/middleware/request_id.py`.
   - Prometheus counters: at least 1 counter exposed per major surface (verify via `/metrics` endpoint or grep `Counter\|Histogram` in code).
   - LangFuse trace: emitted from `ai_ops/client.py` step 8.

10. **i18n ~50 message IDs populated** per §15.K — `grep -c '^"[a-z]' backend/app/i18n/messages_en.py` ≈ 50.

Plus universal: no regressions; import-linter PASS.

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
# §15 Cross-Cutting Walkthrough Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-15-crosscutting-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Multi-tenancy 3-layer | PASS/FAIL | per-layer evidence |
| 2 | core/cache.py sole Valkey DB 3 | PASS/FAIL | grep |
| 3 | pg_trgm GIN indexes | PASS/FAIL | \di output |
| 4 | Audit middleware + 7 direct-write exceptions | PASS/FAIL | grep |
| 5 | AI Ops single import + 3 workloads + guardrail + cap + fallback | PASS/FAIL | per-element evidence |
| 6 | Plan_guard 4 resources | PASS/FAIL | grep |
| 7 | FE-D5 refresh allowlist (HMAC + Lua EVAL) | PASS/FAIL | grep |
| 8 | CSRF posture (no middleware) | PASS/FAIL | grep |
| 9 | Observability (request_id + Prometheus + LangFuse) | PASS/FAIL | per-element |
| 10 | i18n ~50 message IDs | PASS/FAIL | wc -l |

## Non-compliance findings
## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save at `docs/audits/§15_crosscutting_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Multi-tenancy layer missing (CRITICAL — cross-tenant data leak risk).
- AI Ops single import surface violated (CRITICAL — boundary breach).
- CSRF posture changed (escalate — security review).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-15-crosscutting-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-7 CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §15 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 9 of 10
- **Sequential dependency:** Wave 8 complete (recommended) OR may run in parallel with Wave 8 if §20 deployed and all modules constructed.
- **Parallel-safe?:** Yes — parallel with §16, §21, §22A.
- **Expected duration estimate:** ~3-5 hours.
- **Acceptance verification by master:** read audit; spot-check multi-tenancy + AI ops boundary; on PASS proceed to Wave 10.
