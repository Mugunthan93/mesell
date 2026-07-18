# Phase 3 — Validation + Drift (ACTIVE from 2026-07-18)

**Goal (G3):** prediction error < 10% over 5+ real sessions → CALIBRATED; then re-estimate forever.

## Protocol
1. Before a work session: `tokcap_predict.py predict --model <m> --out <est>` and `session start`.
2. Work normally. After: `session end --predicted P` → actual vs predicted logged to `~/.tokcap/validation_log.ndjson`.
3. 5+ pairs → G3 evaluation; misses feed constant refinement.
4. **Drift:** any validation pair off by >2× its error band ⇒ re-run one mono cell (cheap) and re-fit; plan-tier change ⇒ full re-fit.
5. **Passive precision:** periodic `tokcap_meter.py` snapshots during normal work accrue weekly-bar ticks for free (weekly ±2% target).

## Carried-over open items
- G0 completion: OTEL running over a normal workday → daily reconciliation <5%.
- Session constant ±5–10%: one clean mono repetition in a pre-reset slot.
- Reset-carryover anomaly repro (bar 31% at reset+1min).
- Opus/Fable spot-check tick ($-weighting predicts same $/tick).
- Productionize: watermark ingester, launchd schedules, `tokcap` CLI wrapper (supervised build).
