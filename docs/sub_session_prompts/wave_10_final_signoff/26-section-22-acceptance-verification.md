# Sub-Session Prompt: §22 Acceptance & Sign-Off — FINAL VERIFICATION
# Wave 10 of 10 — VERIFICATION (FINAL; runs AFTER all 25 prior sub-sessions PASS)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-22-acceptance-1
# THIS IS THE V1 GO/NO-GO SIGN-OFF

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §22 verification" then master's "go".
5. ON PASS — backend V1 is signed off. Founder is notified.

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §22 (Acceptance & Sign-Off). This is the **FINAL V1 GO/NO-GO sign-off**.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION (FINAL acceptance). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §22 Acceptance & Sign-Off — V1 acceptance checklist mapped per Feature 1-9; cross-cutting acceptance; coverage + perf budgets; this is GO/NO-GO
- Sub-session naming: `/rename meesell-backend-verification-22-acceptance-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §22 (audit target; esp. §22.B per-feature acceptance checklist F1-F9, §22.C cross-cutting acceptance, §22.D sign-off responsibilities).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` ALL 25 prior sections (§0 through §22A) — every locked claim is potentially in scope.
3. `/Users/mugunthansrinivasan/Project/mesell/docs/V1_FEATURE_SPEC.md` — the 9 V1 features.
4. `/Users/mugunthansrinivasan/Project/mesell/docs/audits/` — all 9 prior audit reports from Waves 8 + 9.
5. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` — confirm all 16 construction + 9 verification sub-sessions PASS.
6. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_MASTER.md`.
7. `/Users/mugunthansrinivasan/Project/mesell/backend/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

EXECUTE the full V1 acceptance checklist per §22.B + §22.C:

**Per-feature acceptance (V1_FEATURE_SPEC Features 1-9):**

- **F1 — Auth/OTP** — 4 endpoints (otp/send, otp/verify, refresh, logout) + `/me` + razorpay capture. Verify all 6 surfaces mounted; verify §7.J 4 unit + 3 integration tests PASS; verify FE-D5 HMAC-pepper + Lua EVAL working end-to-end.
- **F2 — Smart Picker** — top-5 with guardrails + fallback. Verify `/category/suggest` returns top-5 from §6A Layer 1+2 guardrails; `BudgetExceededError` → 200 + `fallback_offered=true` (NOT 503); §9.J 5 unit + 3 integration tests PASS.
- **F3 — Catalog wizard** — 6 endpoints + autosave + draft recovery. Verify all 6 catalog endpoints mounted; autosave to `product_drafts`; `GET /products/{id}/draft` returns 200 or 204; §10.J 5 unit + 3 integration tests PASS.
- **F4 — AI Auto-fill** — Layer 2 retry + 200 graceful fallback. Verify `POST /products/{id}/autofill` triggers `ai_ops.client.call_gemini("autofill", ...)`; on `BudgetExceededError` → 200 + `fallback_offered=true`.
- **F5 — Image precheck** — 5-step Celery pipeline + watermark informational-not-blocking. Verify `image.precheck` Celery task with 5-step pipeline; watermark "skipped_budget" path; §11.K tests PASS.
- **F6 — Preview** — composes 3 modules (catalog/image/customer). Verify `GET /products/{id}/preview` composes correctly.
- **F7 — Price Calculator** — P&L + 3 alert codes. Verify `POST /products/{id}/price-calc` returns P&L with LOW_MARGIN / HIGH_MRP_MULTIPLIER / THIN_PROFIT alerts; §12.J 4 unit + 2 integration tests PASS.
- **F8 — Dashboard** — paginated + profile_completeness. Verify `GET /products` paginated; profile_completeness surfaces; §13.J 3 unit + 2 integration tests PASS.
- **F9 — XLSX Export** — 9-step pipeline + 15 golden fixtures pass + Layer 3 guardrail. Verify 9-step pipeline; all 15 golden round-trip fixtures PASS; Layer 3 `ExportEnumValidationError` raised on unknown enum; §14.K 10 unit + 3 integration tests PASS.

**Cross-cutting acceptance (§22.C):**

- 27 endpoints mounted per §17.B.
- ~50 i18n message IDs in `messages_en.py`.
- 10 CI gates: 7 import-linter + Contract 8 scope_to_user + Contract 9 M10 symbols + Contract 10 message_id regex — all PASS.
- Multi-tenant isolation regression test PASS.
- 4 perf budgets within target:
  - P95 schema fetch ≤ 50ms cache hit / ≤ 200ms cache miss.
  - P95 manual-browse ≤ 200ms.
  - End-to-end export ≤ 30s.
  - Per-call AI cost ≤ ₹0.05 avg.
- 3 Secret Manager containers populated (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`).
- 80% line / 100% branch coverage on critical paths per §19.F.
- 3 AI eval sets PASS (Smart Picker recall ≥ 80%, Autofill 0% invalid enums, Watermark accuracy ≥ 85%).

**Prior audit consolidation (Waves 8 + 9):**

Confirm all 9 prior verification sub-sessions report PASS verdict:
- §0 Architectural Premises — PASS
- §1 System Topology — PASS
- §2 Module Catalog — PASS
- §3 File Structure — PASS
- §17 Endpoint Inventory — PASS
- §15 Cross-Cutting Walkthrough — PASS
- §16 Inter-Module Rules — PASS
- §21 Extraction Path — PASS
- §22A Risk Register — PASS

Plus universal: 42/42 schema tests + 7/7 boot integration tests + ~88 module-level test classes PASS; no regressions.

**Final verdict:**

If ALL acceptance items PASS → **V1 GO**.
If ANY CRITICAL item FAILS → **V1 NO-GO** (master orchestrates remediation; this audit re-runs as attempt #2).
If only MEDIUM/LOW items partial → **V1 GO WITH CONDITIONS** (master + founder review; some items defer to V1.5).

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code. Read-only acceptance audit.
- DO NOT amend LOCKED sections.
- DO NOT modify codebase to fix non-compliance — REPORT and let master orchestrate.
- DO NOT touch STATUS_MASTER.md (master + founder decide the final sign-off entry).
- DO NOT issue a GO verdict if any of the 9 prior audits returned PARTIAL or FAIL.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

```
# §22 Acceptance & Sign-Off Audit Report — V1 GO/NO-GO
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-22-acceptance-1
**Overall verdict:** V1 GO | V1 GO WITH CONDITIONS | V1 NO-GO

## Per-Feature Acceptance (F1-F9)
| F | Feature | Status | Evidence |
|---|---|---|---|
| F1 | Auth/OTP | PASS/FAIL | test results + endpoint list |
| F2 | Smart Picker | PASS/FAIL | guardrail + fallback evidence |
| F3 | Catalog wizard | PASS/FAIL | endpoint list + draft recovery test |
| F4 | AI Auto-fill | PASS/FAIL | graceful fallback test |
| F5 | Image precheck | PASS/FAIL | Celery pipeline + watermark test |
| F6 | Preview | PASS/FAIL | cross-module composition test |
| F7 | Price Calculator | PASS/FAIL | P&L + 3 alerts |
| F8 | Dashboard | PASS/FAIL | pagination + profile_completeness |
| F9 | XLSX Export | PASS/FAIL | 15 fixtures + Layer 3 |

## Cross-Cutting Acceptance
| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | 27 endpoints mounted | PASS/FAIL | OpenAPI count |
| 2 | ~50 i18n message IDs | PASS/FAIL | wc -l |
| 3 | 10 CI gates PASS | PASS/FAIL | linter output |
| 4 | Multi-tenant isolation | PASS/FAIL | test result |
| 5 | 4 perf budgets within target | PASS/FAIL | perf test results |
| 6 | 3 Secret Manager containers populated | PASS/FAIL | gcloud secrets list |
| 7 | 80% line / 100% branch coverage | PASS/FAIL | coverage report |
| 8 | 3 AI eval sets PASS | PASS/FAIL | eval set results |

## Prior Audit Consolidation
| § | Prior audit | Verdict |
|---|---|---|
| §0 | Premises | PASS/FAIL |
| §1 | Topology | PASS/FAIL |
| §2 | Modules | PASS/FAIL |
| §3 | Files | PASS/FAIL |
| §17 | Endpoints | PASS/FAIL |
| §15 | Cross-cutting | PASS/FAIL |
| §16 | Inter-module rules | PASS/FAIL |
| §21 | Extraction | PASS/FAIL |
| §22A | Risks | PASS/FAIL |

## CRITICAL findings (if any)
<per-finding>

## V1 GO / NO-GO Decision Rationale
<2-4 sentences>

## Hand-back to master + founder
<list of next actions; if GO → notify founder; if NO-GO → remediation plan>
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save at `docs/audits/§22_acceptance_audit_<YYYY-MM-DD>.md`.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §22 Acceptance AUDITED ===
   FINAL VERDICT: V1 GO | V1 GO WITH CONDITIONS | V1 NO-GO
   Per-feature: F1 ✓ F2 ✓ F3 ✓ F4 ✓ F5 ✓ F6 ✓ F7 ✓ F8 ✓ F9 ✓
   Cross-cutting: 27 endpoints ✓ / ~50 i18n ✓ / 10 CI gates ✓ / multi-tenant ✓ / 4 perf budgets ✓ / 3 secrets ✓ / 80%/100% coverage ✓ / 3 AI eval sets ✓
   Prior audits: §0 ✓ §1 ✓ §2 ✓ §3 ✓ §17 ✓ §15 ✓ §16 ✓ §21 ✓ §22A ✓
   Audit report: docs/audits/§22_acceptance_audit_<YYYY-MM-DD>.md
   Hand-back: BACKEND V1 IS SIGNED OFF. Notify founder. Master to update STATUS_MASTER.md to "✅ BACKEND V1 COMPLETE".
   =========
   ```
3. Report back to master under 400 words: per-feature pass/fail; cross-cutting pass/fail; prior audit consolidation; final verdict; "V1 sign-off complete. Standing by for master + founder notification."

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS (STOP AND REPORT TO MASTER)
═══════════════════════════════════════════════════════════════

- Any prior audit (Wave 8 or 9) is PARTIAL or FAIL → cannot issue V1 GO; escalate.
- Any feature F1-F9 fails its acceptance → CRITICAL; cannot issue V1 GO; escalate with remediation plan.
- Any cross-cutting item fails (e.g. 3 AI eval sets fail thresholds) → CRITICAL; escalate.
- More than 3 MEDIUM-level findings → escalate for founder ruling on V1 GO WITH CONDITIONS vs V1 NO-GO.

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-22-acceptance-1`
2. Read REQUIRED READING (esp. all 9 prior audit reports).
3. Confirm STATUS_BACKEND.md shows all 25 prior sub-sessions report CONSTRUCTED / PASS.
4. Report "Audit context loaded. Ready to begin §22 V1 GO/NO-GO verification." to master.

WAIT for master's "go". On master's "go", execute the full acceptance checklist and issue the final verdict.

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 10 of 10 — FINAL
- **Sequential dependency:** ALL 25 prior sub-sessions PASS (Waves 1-7 construction + Waves 8-9 verification).
- **Parallel-safe?:** No — Wave 10 is the final sign-off.
- **Expected duration estimate:** ~4-6 hours (full V1 GO/NO-GO checklist execution).
- **Acceptance verification by master:** read audit report carefully; spot-check 5-7 random per-feature items; verify all 9 prior audits returned PASS; if final verdict is GO → notify founder, update STATUS_MASTER.md to "✅ BACKEND V1 COMPLETE"; if NO-GO → orchestrate remediation per protocol §5.1B, re-attempt as `26-section-22-acceptance-verification-attempt-2.md`.
