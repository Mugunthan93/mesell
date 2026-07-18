# tokcap RESULTS_LOG

One row per iteration, written immediately (plan §8/§10). Data lives in `~/.tokcap/` (never committed).

## POC 2026-07-18 — master session `bae00058`, direct-mode, unattended (founder asleep)

### Group 1 — transcript reality check (read-only, $0) — ALL GREEN
| check | verdict | evidence |
|---|---|---|
| T1 fields | PASS+ | 23,742 asst lines: 100% carry 4 usage fields + model; requestId 94.9% (5% gap = API-error lines, 0 tokens) |
| T2 dedup real | PASS | up to 24 lines/requestId; 32,868/46,698 multi-line; 20,507 merges had *differing* usage → per-field-MAX rule |
| T3 subagent attribution | PASS (was red) | 1,356 subagent transcripts at `projects/<slug>/<session>/subagents/agent-*.jsonl`; 462M BW; **needs recursive glob** |
| T4 slug/session | PASS+ | dir=slug + native `slug` field + attributionSkill/McpServer |
| T5 windows | PASS | 95 rolling-5h windows, spans bounded 0–5.00h |

### Group 2 — OTEL reality check (direct mode; 2 Haiku probes ≈ $0.079) — SUCCESS (gate cleared)
| id | verdict | evidence |
|---|---|---|
| O1 reversible enable | PASS | add OTEL keys to `~/.claude/settings.json` → restore → sha byte-identical (`a497854…`) |
| O2 token capture | PASS | local OTLP http/json listener received `claude_code.token.usage` by type = {input10, output393, cacheRead16334, cacheCreation10453} == probe stdout; `claude_code.cost.usage`=$0.0245; attrs incl. model + `query_source`(main/subagent) + org/user id |
| probe#1 cold | — | in10 cc26917 cr0 out393 → $0.054 |
| probe#2 warm | — | in10 cc10453 cr16334 out393 → $0.0245 (cache-state effect visible) |
| baseline catch | — | "empty" scratch still loads ~27K cache-creation (global config) — subtract in Phase-2 dose math |

### Phase 0 — passive ledger BUILT (read-only, $0)
- 1,419 files (63 main + 1,356 subagent) → 46,708 deduped requests → `~/.tokcap/ledger.db` (17MB)
- main 478.3M / **subagent 462.0M BW (49%)** — recursive-glob correction confirmed load-bearing
- 95 windows; **max 81.88M BW = capacity lower bound**; current window ~1.5% of max (budget gauge); corpus ≈ **$4,879** API-equiv
