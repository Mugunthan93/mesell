# Phase 2 Report — Active-Dose Calibration: COMPLETE (first fit)

**Date:** 2026-07-18 · **Spend:** ~$1.0-equiv across 4 batches (33 doses) · **Result: the meter is understood.**

## The journey (one day)
1. **Trigger:** "40% gone on the first session — where?" → plan + architecture (2026-07-17).
2. **POC Group 1:** transcripts carry exact server receipts; subagents = 49% of spend (recursive-glob fix); dedup by requestId per-field-MAX.
3. **POC Group 2:** OTEL tap verified (reversible toggle, local listener, `query_source` attribution).
4. **Sensor (route b):** `/api/oauth/usage` + Keychain token → live bars (session / weekly_all / weekly-per-model). Transcript gauge proven ~60× lag-blind → live guard uses sensor only.
5. **Batches 1–4:** titration with founder-ruled per-dose pre-flight (never fire a dose that could cross the ceiling), human live log, quarantine discipline.

## Findings (measured, not guessed)
| # | Finding | Evidence |
|---|---|---|
| F1 | **Meter is $-WEIGHTED** (charges ≈ API prices) | mono-decider: sonnet/haiku $-per-tick = **1.04**, tokens-per-tick = 0.42 |
| F2 | **1% ≈ $0.05–0.065-equiv** → **C_session(Pro) ≈ $5–6.5**, C_weekly ≈ 8–9× ≈ $42–55 | 4 interior ticks (mono) + batch-3 no-tick bound |
| F3 | **Model choice ≈ 10× budget lever** | window output-budgets: Fable ≈100K · Opus ≈210K · Sonnet ≈350K · Haiku ≈1M tokens |
| F4 | **Warm cache ≈ free; cold restarts are the tax** | 11 warm doses → zero ticks; cold 78K Fable rewrite ≈ $1 ≈ ~20% of a window |
| F5 | **Effort has no surcharge** — it is only more output tokens | effort-high: out 4→406 (~100×), cost scaled exactly; receipts capture all |
| F6 | Contamination destroys tick math | batch-1 "$3.9 convergence" was artifact; quarantine now mandatory |
| F7 | Reset anomaly: fresh bar read 31% at reset+1min | carryover/lag semantics — OPEN, needs repro |

## Method lessons (locked into the tools)
- **Pre-flight per dose** (founder rule): estimate dose % cost from observed jumps; refuse to fire into the ceiling.
- **Mono-model phases with interior-tick-only accounting** is the decisive design; interleaving cannot separate weight hypotheses.
- **Live human log** (`clean_batch_live.log`) lets the founder observe without chat turns (which cost 3–10%/turn on Fable-max and destroy quarantine).

## Gate stamps
- **G0** (Phase 0): PARTIAL — ledger built (46,708 reqs, $4,879 corpus); OTEL tap verified; the *daily* reconciliation <5% needs OTEL running over normal work → carried into Phase 3.
- **G1** (Phase 1): PASSED via sensor route (b) — capacity bands from organic + probe data.
- **G2** (Phase 2): **SUBSTANTIALLY PASSED** — weight model fitted ($-weighted ✓); session constant ±~15% (target ±5–10: one clean repetition, queued); weekly bounded (precision accrues passively).
- **G3** (Phase 3): STARTED — see phase3-plan.md.
