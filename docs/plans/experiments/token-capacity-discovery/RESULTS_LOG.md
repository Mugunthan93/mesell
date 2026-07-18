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

### Sensor route (b) — LIVE 2026-07-18 (founder-selected)
| item | result |
|---|---|
| Recipe | Keychain svc `Claude Code-credentials` **acct=<login user>** (acct=root item is STALE/expired) → `GET api.anthropic.com/api/oauth/usage` w/ `Authorization: Bearer` + `User-Agent: claude-cli/…` + `anthropic-beta: oauth-2025-04-20` → 200 |
| Response | `limits[]` = kind/group/percent/severity/resets_at/scope (+ five_hour/seven_day summaries). Bars found: **session, weekly_all, weekly_scoped[Fable]**. `resets_at` = ISO string |
| First readings | 01:19Z session 49%/weekly 21%/Fable 18% → 01:45Z **session 81% (warning)** — live guard working (`tokcap_meter.py --guard 90` → PROCEED rc=0) |
| ⚠️ Proxy correction | Ledger transcript-gauge said ~0.8–1.5% while real meter said 49–81% → **transcript flush lag; ~60× undercount. Live guard MUST use this sensor, never the transcript proxy** |
| Caveats | endpoint 429s on rapid polls → 60s courtesy floor built in; token refreshed by Claude Code ~hourly (if expired: run any `claude` cmd); undocumented endpoint = fragile by design (plan §3 route 3 caveat stands) |

## Phase-2 titration batches — 2026-07-18 (founder-supervised)
| batch | cells | doses | Σ$ | meter | key result |
|---|---|---|---|---|---|
| 1 (pre-reset slot) | haiku default | 7 | $0.118 | 89→94% (stop: preflight@94, ceiling 95 founder-amended) | cold 34.3K BW/$0.056 vs warm 6.9K/$0.010 (~5×); per-1% est $0.036–0.040 — **later shown contamination-low** |
| 2 (post-reset) | sonnet default ×5 + `--effort high` ×5 | 10 | $0.472 | 32→39% | **EFFORT VERDICT ✓**: effort-high = ~100× output tokens (4→406), cost scales exactly with tokens, NO hidden surcharge. Sonnet cold $0.159 vs warm $0.008 (~20×). Tick intervals disagreed 19× → contaminated (master-session turns mid-batch) |
| 3 (CLEAN, quarantined, interleaved 6H+6S) | both, default | 12 | $0.122 | 42→44% then flat | **11 warm doses ($0.066 / 31K BW) → ZERO ticks** → clean bound **1% ≥ $0.066** ⇒ C_session ≥ ~$6.6-equiv (likely $7–10); batch-1's $3.9 "convergence" = contamination artifact. Warm-cache ≈ free on the meter (0.1× confirmed live). $-vs-token weighting STILL OPEN — interleaving can't separate; needs mono-model clean runs |
| — | anomaly | — | — | reset 05:50Z → 1 min later fresh bar read 31% | end-of-window spend appears to carry/lag into the new bar — logged, needs repro |

**Method upgrades locked in:** per-dose PRE-FLIGHT guard (founder rule: never fire a dose that could cross the ceiling; adaptive buffer from observed jumps); human live log (`clean_batch_live.log`) for founder observation without chat contamination; quarantine = REQUIRED for any tick attribution (master-session Fable-max turns cost ~1–3%/turn and destroy tick math).
**Next decisive cell:** mono-model clean runs (haiku-only +2 ticks, sonnet-only +2 ticks, same window) → separates $-weighted vs token-weighted.
