# Token-Capacity Discovery Experiment — Ledger + Active-Dose Calibration

**Status:** DRAFT — discussion ratified by founder 2026-07-17, nothing built yet
**Owner:** Founder (Muguntha) + master Claude session
**Created:** 2026-07-17
**Sibling experiment:** `rtk-token-adoption` (shares the transcript-mining methodology; this plan's ledger generalizes RTK Phase 0's mining script)
**Tracking:** `RESULTS_LOG.md` in this directory (created at Phase 0 start)

---

## 1. Objective & Motivation

API-key (metered pay-per-token) mode is unaffordable for day-to-day dev. We run on a
Claude **subscription** instead. That changes the accounting model completely: **the
subscription IS the budget**, and it must be treated like one — a full token ledger, zero
missed tokens, and per-request accountability. There is no invoice at the end of the month
that reconciles reality; the plan meter is all we get, and it is opaque.

Two goals follow.

- **Goal A — the ledger (the numerator).** 100%-accurate per-request token accounting with
  **hierarchical attribution**:

  ```
  global → project / slug → session → agent (main vs each subagent) → request
  ```

  Every token we spend is attributable down to the individual API response that produced it,
  and rolls up cleanly to any level of that hierarchy.

- **Goal B — capacity discovery (the denominator).** We cannot predict the plan meter — its
  internal weighting is undocumented and Anthropic can change it silently. So instead of
  guessing, we **discover** the denominator empirically: what does **100% of the 5-hour
  session window** — and **100% of the weekly limit** — equal in **weighted tokens, per
  model**? Only when we know both the numerator (ledger) and the denominator (capacity) can
  we say "this session will cost N% of the window" before running it.

**Trigger incident.** On Pro, the meter showed **40% consumed on the very first session
after reset**, with zero visibility into where it went. That single unexplained jump is the
motivating datapoint for this whole experiment — §2 shows it is fully explainable.

---

## 2. Why the 40% Is Explainable (worked example)

Live datapoint from the master session **2026-07-17, turn 1**. The usage receipt on that
single turn was:

| Field | Value | API-equivalent weight |
|-------|-------|----------------------|
| `input_tokens` | 2 | $3/M (negligible) |
| `cache_creation_input_tokens` | 78,015 | cache-write 1.25× × $10/M |
| `cache_read_input_tokens` | 0 | 0.1× |
| `output_tokens` | 11,945 | $50/M |
| **model** | `claude-fable-5` | — |

At API-equivalent weights (cache-write 1.25× × $10/M; output $50/M) this is **≈ $1.57-equivalent
for ONE turn**.

Three compounding factors explain why one turn is so heavy:

- **(a) Giant fixed workspace context** — ~78K cache-write on *every* cold session (the
  workspace `CLAUDE.md`, project instructions, memory index, tool schemas). This is paid up
  front the moment a session goes cold.
- **(b) Model weighting** — Fable / Opus ≈ **3–10× Sonnet** per token. The model you pick is
  a multiplier on everything.
- **(c) Thinking tokens** — hidden reasoning bills as `output_tokens` at the **5× output
  rate**. The receipt's `output_tokens` already includes them; there is no separate line.

**Illustrative first estimate of window capacity:** if one turn ≈ $1.57-equivalent moved the
meter enough to be consistent with a ~40% first-session read, then

```
C_pro ≈ 1.57 / 0.40 ≈ $3.9-equivalent per 5-hour window
```

This is **rough — datapoint #1 only** (single turn, single meter read, rounding). It is
written here to anchor intuition, not as a measured constant. The whole point of §5 is to
replace this guess with a measured `C`.

---

## 3. Data Acquisition — Three Streams

The experiment fuses three independent data streams: the **receipts** (exact token counts),
the **meter** (the plan %), and the **boundaries** (which window a spend falls in).

### Stream 1 — Receipts (the numerator, exact)

Every API response carries a **server-metered `usage` object** — the ground truth, four
fields:

```
{ input_tokens,
  cache_creation_input_tokens,   # billed 1.25×
  cache_read_input_tokens,       # billed 0.1×
  output_tokens }                # includes hidden thinking tokens
```

There are two taps into this stream:

- **Tap A — transcripts.** Claude Code writes JSONL to
  `~/.claude/projects/<slug-dir>/<session-id>.jsonl`. Assistant-typed lines carry
  `message.model` + `message.usage` + `requestId`. **Attribution comes for free**: the slug =
  the directory, the session = the file, and subagent activity = the `sidechain` entries. You
  **MUST dedupe by `requestId`** — one response can span multiple lines, and double-counting
  is the classic transcript-mining bug. Transcripts **miss invisible utility calls** (e.g.
  haiku session-titling, compaction) — roughly a few %. Transcripts also **rotate** (~30-day
  cleanup), so the ledger must **ingest incrementally** and never assume the full history is
  on disk.

- **Tap B — OTEL telemetry (100% complete).** Enabling
  `CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_LOGS_EXPORTER=otlp` +
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` emits per-call **`api_request`** events
  (model + the 4 token fields + estimated cost + duration) — **including the utility calls
  transcripts miss** — plus **`claude_code.token.usage`** counters. A local receiver writes to
  file / SQLite; **nothing leaves the machine**.

- **Daily reconciliation.** `OTEL total − transcript total = invisible overhead` — and that
  overhead is itself tracked as a line in the ledger, not discarded.

### Stream 2 — Meter (the %)

The plan meter lives **server-side only**; we can read it but not compute it. Routes, ranked
by trust:

| # | Route | Nature |
|---|-------|--------|
| 1 | `/usage` in-app | Manual, **ground truth**. |
| 2 | `claude.ai/settings/usage` scraped on a schedule with **agent-browser** | Known-good pattern: `HOME=/tmp/ab-home`. **Observation consumes zero plan tokens.** |
| 3 | Unofficial endpoint Claude Code itself calls: `api.anthropic.com/api/oauth/...usage` (OAuth token from the macOS Keychain item **"Claude Code-credentials"**) | **Bonus only** — undocumented, fragile. |
| 4 | `anthropic-ratelimit-*` response headers | **API-key mode only — NOT available on subscription** (a closed door for us). |

### Stream 3 — Boundaries

- **Session bar** = a **5-hour ROLLING window** that opens at the **first message** (not
  clock-fixed).
- **Weekly bar** = a **fixed 7-day reset**, shown in `/usage`.
- **Possible separate Opus-weekly bar** on some plans.
- Each bar gets its **own capacity constant**.
- **Window boundaries are recoverable from transcripts alone:** the first message after a
  **>5h gap** opens a new window. So the ledger can segment history into windows offline,
  with no meter data at all.

---

## 4. The Quantization Problem and Its Fixes

The meter moves in **1% steps** — a **bucket = C/100**. Position *inside* the current bucket
is unknown, the UI **rounds to a whole %**, and it **updates with lag**. Consequence: **two
same-% snapshots ≠ zero spend** (you may have moved 0.9% of a bucket and not ticked). Four
fixes:

- **Tick-hunting.** Poll frequently. Tokens spent **between two consecutive ticks = exactly
  C/100**. Interior ticks are **exact** measurements; discard the first and last **partial**
  buckets (you don't know where in the bucket you started/stopped).

- **Bounds from every observation.** Even a non-tick is informative:
  - `T` weighted tokens with **no tick** → `C > 100 × T`.
  - A **k-tick jump** over `T` tokens → `T / (k+1)% < C < T / (k−1)%`.

- **Wide spans shrink the error.** Worst-case error is **±1 bucket per end**, regardless of
  span. So the wider the span you measure across, the tighter the relative bound:

  | Ticks observed across the span | Relative error on C |
  |---|---|
  | 1 tick | ±100% |
  | 10 ticks | ±20% |
  | 40 ticks | ±5% |
  | ~100 ticks (a full weekly traversal) | ±2% |

  The **weekly bar is the precision champion** — a single organic week can traverse ~100
  ticks and pin `C_weekly` to ±2% with no probing at all.

- **Read discipline.** Pair a meter read to the ledger **only when idle 1–2 min** (let the
  lag settle), **never mid-burst**.

---

## 5. CORE PROTOCOL — Active Controlled-Dose Calibration

*(Founder's design, ratified 2026-07-17.)*

The shift is from **passive observation** to a **controlled-dose experiment (titration)**: we
**inject doses of known weight and watch the meter**. One iteration of the loop:

```
1. usage_before  ← read portal %            (free)
2. fire probe    ← dummy request, variant V (model × cache-state × effort)
3. receipt       ← exact 4-field usage of that probe
4. usage_after   ← read portal %
5. append (variant, receipt, %before, %after, timestamp) to log
```

### Design rules

- **Probe vehicle.** `claude -p "reply: ok" --model <m> --output-format json`, run from an
  **EMPTY scratch directory** (no `CLAUDE.md` / memory / MCP → **no 78K context tax**).
  stdout JSON contains the usage receipt. **Clamp output** with a low `max_tokens`.
- **Measured, not predicted.** The dose is "known" because the **server's receipt states it
  exactly** — never pre-compute the dose weight; read it off the receipt.
- **Probes spend the budget being measured.** Schedule them in **use-it-or-lose-it slots**
  (the final stretch before a session-window / weekly reset). **Cap probe spend ≤ 10% of a
  window.** Expensive cells (Fable / Opus) go in **expiring-budget slots**.
- **Quarantine.** **No parallel Claude usage** (phone app, other sessions) during a batch —
  and the always-on ledger attributes any stray tokens anyway, as a backstop.
- **Titration.** **Far from a tick** → large cheap doses (Haiku) to march toward the edge.
  **Near a tick** → small doses, **binary-search the bucket edge**.
- **One factor at a time.** Baseline = **Sonnet / cold cache / default effort**. Axes swept
  **singly**:
  - **model** — Haiku, Sonnet, Opus, Fable;
  - **cache state** — cold vs warm-within-TTL (fire twice **inside** the cache TTL vs **after**
    expiry);
  - **effort level**.
- **Final analysis — one regression over the whole log:**

  ```
  Δbuckets ≈ Σ weight(model, field) × tokens
  ```

  **Starting hypothesis:** weights = **published API prices** ($/M per model; cache-write
  **1.25×**, cache-read **0.1×**). The data either confirms those weights or fits corrections
  to them.

---

## 6. Deliverables

- **`token_ledger` tooling spec (Phase A).** SQLite + rollups at **global / slug / session /
  agent / model / day**, reporting **both raw fields and weighted totals** — `UE` and `BW` per
  the RTK plan §3 definitions:
  - `UE = input + cache_creation + cache_read + output` (uncached-equivalent, cache-independent);
  - `BW = input + cache_creation×1.25 + cache_read×0.1 + output` (billed-weight).
- **Capacity constants.** Session window + weekly (+ Opus bar if present), **per plan tier**
  (Pro vs Max 5× / 20×).
- **Weight table** per model / field.
- **Per-model window budget table** — e.g. at `C ≈ $4-equiv`:

  | Model | Output price | Output tokens per window (illustrative) |
  |-------|--------------|------------------------------------------|
  | Fable 5 | $50/M | ≈ **80K** |
  | Sonnet | $15/M | ≈ **266K** |
  | Haiku | $5/M | ≈ **800K** |

  *(Illustrative until measured — derived from the §2 guess `C ≈ $4`, not a constant.)*
- **Prediction service.** "This session will cost ~N% of the window", **validated to < 10%
  error**.

---

## 7. Phases with Pre-Committed Gates

Each phase's gate is fixed **now**, before any data is collected, and is not adjusted
post-hoc (§8).

### Phase 0 — Passive ledger (zero spend, read-only)

- **Question:** Can we account for 100% of historical spend from what's already on disk?
- **Method:** Build the passive ledger over **existing transcripts**; **historically mine**
  the last window; **segment into 5h windows** by the >5h-gap rule; make the **OTEL
  enablement decision**.
- **Deliverable:** the passive ledger + a reconciliation report.

| Gate G0 | Criterion |
|---|---|
| ✅ PASS | **OTEL ↔ transcript reconciliation gap explained and < 5%.** |

### Phase 1 — Passive calibration (zero extra spend)

- **Question:** How tight a capacity band can organic usage alone give us?
- **Method:** Take **meter snapshots** (manual `/usage` + agent-browser scraper) **during
  normal work**; accumulate **tick data + bounds** (§4) from organic usage only.
- **Deliverable:** a capacity band from organic data.

| Gate G1 | Criterion |
|---|---|
| ✅ Band derived | Capacity band computed from organic data. |
| ↦ Active probing **optional** | If **band width ≤ ±20%** AND **no variant questions remain**, Phase 2 becomes optional. |

### Phase 2 — Active probing (spend-capped)

- **Question:** What are the precise per-model weights and capacity constants?
- **Method:** The **§5 dose loop**, full **variant sweep** (model × cache-state × effort),
  **spend-capped** (≤ 10% of a window; expensive cells in expiring-budget slots).
- **Deliverable:** fitted weight table + capacity constants.

| Gate G2 | Criterion |
|---|---|
| ✅ Calibrated bounds | **Weekly capacity to ±2%**, **session capacity to ±5–10%**, **weight table fitted.** |

### Phase 3 — Validation + drift

- **Question:** Does the model predict fresh real sessions?
- **Method:** **Predict Δ% of fresh real sessions** before running them, compare to the meter.
- **Deliverable:** validation record; ongoing drift monitor.

| Gate G3 | Criterion |
|---|---|
| ✅ CALIBRATED | Prediction **error < 10% over 5+ sessions**. |
| ♻️ Continuous | Re-estimate **forever** — Anthropic can silently change capacity; estimates are **per-plan**. |

---

## 8. Ground Rules (non-negotiable)

1. **Never in the MeeSell master tree.** All probes run from **`/tmp` scratch dirs**.
2. **Log before the next run.** Every iteration is written to `RESULTS_LOG.md` (created at
   Phase 0 start) **before** the next run starts. No batch backfilling from memory.
3. **Gates are pre-committed** (§7) and **never adjusted post-hoc**.
4. **Probe budget caps are hard** — ≤ 10% of a window per batch; expensive cells only in
   expiring-budget slots.
5. **The unofficial endpoint is bonus-only** — never a load-bearing dependency (§3, route 3).
6. **Rounding ±1% and meter lag are acknowledged in all error bars** — no result is reported
   without its quantization bound.
7. **OTEL hook / settings changes are snapshotted and reversible.** Enabling telemetry edits
   global settings that **affect all workspace projects** (Aletheia, Prospero, …); snapshot
   before, restore after, and never let it linger outside experiment windows.

---

## 9. Risks & Open Questions

| Risk / question | Note |
|---|---|
| **Meter lag magnitude** unknown | Bounds how tightly a paired read can be trusted; measured empirically in Phase 1. |
| **Rounding mode** (floor vs nearest) | **Discoverable from tick spacing** — the offset pattern reveals it. |
| **Burst / priority factors** | The meter may weight bursty spend differently; watch for regression residuals that correlate with burstiness. |
| **Plan-tier change resets calibration** | Constants are per-plan (Pro vs Max 5× / 20×); a tier switch invalidates `C`. |
| **Scraping our own usage page** | Own-account observation of our own meter — **fine**. |
| **Undocumented endpoint may vanish** | Route 3 is bonus-only by design, so its loss costs nothing. |

---

## 10. Tracking

- **`RESULTS_LOG.md`** (same dir, created at Phase 0 start) — one row per iteration:
  `run-id | date | phase | variant (model × cache-state × effort) | usage_before% | receipt (input / cache_create / cache_read / output) | usage_after% | Δbuckets | notes`.
  Written **immediately** after each iteration, before the next.
- **Phase artifacts:** `token_ledger` spec + DB, `phaseN-report.md` per phase, the fitted
  **weight table**, the **capacity constants**, and the **prediction-service** spec.
- The **Status header** of this file is updated at every gate crossing (G0 → G1 → G2 → G3).
