# Handoff — IA-RED-2 eval stub-guard ↔ real-scorer swap (qa-image-ai)

**From:** `meesell-qa-coordinator` (session `mesell-qa-wave-image-ai-backend-session-1`, gate)
**To:** `meesell-ai-coordinator`
**Date:** 2026-06-22
**Topic:** Coordinated retire/replace of `TestStubStateGuards` when the IA-RED-2 `/ai` PR lands.
**Status:** OPEN (48h SLA before founder escalation)

## The collision

Two parallel lanes touch `backend/app/ai_ops/eval.py::_run_one_fixture`:

1. **QA backend lane** (`feature/qa-image-ai/backend`, PR #431 — currently gate-REJECTED for an
   unrelated one-file fixture fix; the eval harness itself is sound and will survive the re-do).
   Added `backend/tests/test_ai_ops_eval_scoring_harness.py` with:
   - `TestStubStateGuards` — asserts the CURRENT stub state: `run_eval('watermark')` and
     `run_eval('autofill')` each return `fixtures_run == 30`, `fixtures_passed == 0`,
     `passed is False`. LOCKS the `_run_one_fixture` hardcoded `passed=False` stub so a silent
     regression (stub flipped to True without real scoring) is caught. VALID NOW.
   - `TestRunnerAggregationLogic` — patches `_run_one_fixture` with a mock scorer and asserts the
     runner's aggregation math (26/30 -> 86.7% >= 85% -> passed=True). Scorer-independent; SURVIVES.

2. **AI lane** (`feature/qa-image-ai/ai`, `meesell-prompt-engineer`, gated by YOU per plan §6).
   REPLACES the `_run_one_fixture` stub with a real (mock-`call_gemini`-backed) scorer + its own
   `test_ai_ops_eval.py` real-scoring test (AI-BE-15/16).

## The hazard

`TestStubStateGuards` asserts `fixtures_passed == 0 / passed is False`. The moment your `/ai` PR's
real scorer lands, those assertions become FALSE. If both lanes merge into
`feature/qa-image-ai/integration` without coordination, the integration branch is
SELF-CONTRADICTING in the same CI run.

## The ask (owned by you, the `/ai` gate)

When you gate `feature/qa-image-ai/ai` -> `feature/qa-image-ai/integration`:
- RETIRE or REPLACE `TestStubStateGuards` in `test_ai_ops_eval_scoring_harness.py` IN THE SAME
  integration assembly — the prompt-engineer's `test_ai_ops_eval.py` real-scoring test now owns
  that surface (watermark >=85%, autofill 100% enum-conformance, mocked seam).
- KEEP `TestRunnerAggregationLogic` (scorer-independent).
- Net: stub-locked + aggregation-proven -> real-scoring-proven + aggregation-proven, no red window.

## Sequencing
- Siblings off the same `qa-image-ai` slug; the integration branch sees both.
- Cleanest: your `/ai` PR both wires the real scorer AND drops/replaces `TestStubStateGuards` in
  one squash. The corrected QA backend re-do PR will still ADD `TestStubStateGuards` (correct vs
  the stub at its base) — the reconciliation is a property of the INTEGRATION assembly, owned at
  your `/ai` gate.

## Cross-reference
- Plan: `docs/testing/IMAGE_AI_QA_WAVE_PLAN.md` §4 (IA-RED-2), §6 (handoff -> you).
- Board: `docs/status/feature_board_qa.md` -> Inter-lead requests open (ai-coordinator row).
- QA memory: `coordinator_patterns.md` ("Golden fixtures landed != golden eval runs").
