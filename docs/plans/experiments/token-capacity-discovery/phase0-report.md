# Phase 0 — Passive Ledger Report

**Generated:** 2026-07-18T06:49:23  ·  **Source:** `~/.claude/projects/**/*.jsonl`  ·  **DB:** `/Users/mugunthansrinivasan/.tokcap/ledger.db`  ·  read-only, zero API calls

## Corpus & dedup

- transcript files: **1421** (65 main + 1356 subagent)
- deduped API requests: **46,708**  ·  multi-line requests: 32,878  ·  multi-line merges with *differing* usage across lines: 20,507 → **per-field-MAX dedup is load-bearing** (T2 confirmed)

## Attribution — recursive-glob correction (headline)

- main: **478.3M BW** (51%)
- subagent: **462.0M BW** (49%)

> Subagent share ≈ **49%** of all weighted tokens. A non-recursive glob (`projects/*/*.jsonl`) misses this entirely — the original design would have undercounted total spend by ~half. **This is the load-bearing Phase-0 fix.**

## Windows & capacity anchor

- rolling-5h windows: **95**
- window BW: min 0K · median 4426K · **max 81.88M**
- **capacity LOWER BOUND** ≈ 81.88M BW (largest window reached without a reported hard stop) — a real anchor for calibration

- current/active window (id 95): opened 2026-07-18T01:09:42.149Z, 11 reqs, 1.205M BW (~1.5% of max-window) — the **self-sourced budget gauge**

## Rollups — billed-weight & approx-$ (deduped)

### by project
- `-Users-mugunthansrinivasan-Project-mesel` — 696.9M BW · ~$3,742
- `-Users-mugunthansrinivasan-Project` — 220.1M BW · ~$1,019
- `-private-tmp-mesell-wt-catalog-form-fix` — 11.0M BW · ~$58
- `-private-tmp-mesell-wt-ui-ds-phase3` — 7.8M BW · ~$41
- `-Users-mugunthansrinivasan-Project-mesel` — 2.8M BW · ~$10
- `-Users-mugunthansrinivasan-Project-mesel` — 1.1M BW · ~$7
- `-private-tmp-rtk-exp-scratch` — 0.5M BW · ~$2
- `-Users-mugunthansrinivasan-Documents-ITR` — 0.1M BW · ~$1

### by model
- `claude-opus-4-8` — 527.2M BW · ~$3,014
- `claude-sonnet-4-6` — 238.3M BW · ~$811
- `claude-opus-4-7` — 130.2M BW · ~$721
- `claude-fable-5` — 27.4M BW · ~$290
- `claude-sonnet-5` — 10.5M BW · ~$35
- `claude-haiku-4-5-20251001` — 6.7M BW · ~$8
- `<synthetic>` — 0.0M BW · ~$0

### total approx-$ across corpus: ~$4,879  *(approx: 5m-cache 1.25×; 1h-cache 2× not modelled)*

## Reconciler (OTEL) — validated separately

- Group 2 proved the OTLP tap: `claude_code.token.usage` (by type) + `claude_code.cost.usage` land in a local listener, byte-reversible settings toggle. The daily OTEL↔transcript delta (gate G0 metric) requires OTEL running over an interactive window → next step.
