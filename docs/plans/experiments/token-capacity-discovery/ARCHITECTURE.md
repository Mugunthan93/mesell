# Token-Capacity Discovery — End-to-End Architecture

**Status:** DRAFT — design only, nothing built
**Owner:** Founder (Muguntha) + master Claude session
**Created:** 2026-07-17
**Companion:** [`EXPERIMENT_PLAN.md`](./EXPERIMENT_PLAN.md) — read that for the objective, the
three data streams, the quantization math, the active-dose calibration protocol, and the
phase gates. **This doc is the system design those phases implement; it does not repeat their
rationale.** Where a mechanism is justified in the plan, this doc cites the section (e.g.
"EXPERIMENT_PLAN §5") rather than re-arguing it.
**Isolation:** this design lives ONLY on branch `chore/token-capacity-discovery/plan`; it
**never merges to `develop`** (founder ruling 2026-07-17). See §2.

---

## 1. System Overview

Four **collectors** feed one **SQLite ledger**; a set of **processors** read the ledger and
produce **outputs**; **launchd schedulers** drive the collectors on timers. Nothing is a
long-running server except the OTEL receiver (a thin local listener) and the schedulers.

```
              ┌──────────────── launchd schedulers (§8) ────────────────┐
              │   ingest.timer   scrape.timer   probe.timer(use-it-slots) │
              └───────┬───────────────┬───────────────────┬──────────────┘
                      │ drives         │ drives            │ drives
   ┌──────────────────▼────────────────▼───────────────────▼──────────────────┐
   │                              COLLECTORS (§3)                               │
   │  transcript_ingester   otel_receiver   meter_snapshotter   probe_driver    │
   │  (~/.claude/projects)   (OTLP :4317)   (agent-browser)     (claude -p …)   │
   └───────┬──────────────────────┬───────────────┬──────────────────┬─────────┘
           │ receipts (exact)      │ receipts+util │ meter %           │ doses+receipts
           ▼                       ▼               ▼                   ▼
   ┌───────────────────────── LEDGER — SQLite (~/.tokcap/ledger.db) (§4) ─────────┐
   │  requests · sessions · windows · meter_snapshots · ticks · probes ·          │
   │  reconciliations · capacity_estimates · price_table                          │
   └───────────────────────────────────┬──────────────────────────────────────────┘
                                        │ read-only
   ┌──────────────────────────────── PROCESSORS (§5) ───────────────────────────────┐
   │ window_segmenter · weighting_engine · reconciler · tick_detector+bounds ·       │
   │ calibration_solver · drift_monitor · predictor                                  │
   └───────────────────────────────────┬──────────────────────────────────────────┘
                                        │
   ┌──────────────────────────────── OUTPUTS (§6) ──────────────────────────────────┐
   │ CLI reports (raw + weighted rollups: global/slug/session/agent/model/day) ·     │
   │ capacity constants · weight table · "this session ≈ N% of window" predictions · │
   │ plain HTML / CSV files (no dashboard framework)                                 │
   └──────────────────────────────────────────────────────────────────────────────┘
```

**Collector → ledger flow.** Each collector's only job is to land rows in the ledger as
faithfully as possible and then exit (except `otel_receiver`, which listens). `transcript_ingester`
and `otel_receiver` both write `requests`; `meter_snapshotter` writes `meter_snapshots`;
`probe_driver` writes `probes` plus the `requests` row for the probe it fired. Collectors never
compute — they only record.

**Ledger → processor flow.** Processors read the ledger, derive higher-order tables
(`windows`, `ticks`, `reconciliations`, `capacity_estimates`), and never call the network. The
ledger is the single synchronization point between "what happened" (collectors) and "what it
means" (processors), so a processor can be re-run idempotently over history at any time.

**Processor → output flow.** Outputs are pure functions of the ledger: a `report` is a SQL
rollup rendered to text/CSV/HTML; a `prediction` is the predictor reading the current window's
partial `requests` against the latest `capacity_estimates`. No output holds state of its own.

**Scheduler → collector flow.** launchd (§8) fires `ingest` hourly, `scrape` on the configured
cadence (fast near boundaries), and `probe` batches only inside use-it-or-lose-it slots. The
schedulers hold no logic beyond timing; every guardrail (spend cap, quarantine) lives in the
collector it triggers.

---

## 2. Isolation & Footprint

**Code home = this branch only.** All tokcap source lands under
`docs/plans/experiments/token-capacity-discovery/` on branch `chore/token-capacity-discovery/plan`
and is pushed to origin as a branch. It **never** opens a PR to `develop` and never merges.
No file outside that directory is modified on this branch.

**Runtime home = `~/.tokcap/` (never committed).** All *data* lives outside any repo:

| Path | Contents |
|------|----------|
| `~/.tokcap/ledger.db` | the SQLite ledger (§4) |
| `~/.tokcap/config.yaml` | cadences, caps, variant matrix, price-table version (§6) |
| `~/.tokcap/logs/` | collector/processor run logs |
| `~/.tokcap/ab-home/` | dedicated agent-browser profile for the scraper (§3c, §7) |
| `~/.tokcap/otel/` | OTLP capture spool (if the file-exporter implementation is chosen, §3b) |

None of `~/.tokcap/` is ever `git add`-ed. The repo carries **code and docs only**; the machine
carries the data. (A `.gitignore` note is unnecessary because the runtime home is outside the
repo tree entirely.)

**Probe scratch dir = `/tmp/tokcap-probe/` (empty).** The dose vehicle runs from a directory
with **no `CLAUDE.md`, no memory, no MCP config** so a probe pays zero workspace-context tax
(EXPERIMENT_PLAN §2 explains the ~78K cold-context cost this avoids). The driver `mkdir -p`s it,
asserts it is empty of any `CLAUDE.md`/`.mcp.json`/`.claude/`, and runs `claude -p` with `cwd`
set there.

**The ONE global side-effect — OTEL enablement.** Turning on telemetry (§3b) edits
Claude-Code-global settings that affect **every workspace project** (Aletheia, Prospero,
MeeSell, …), so it is snapshotted and reversible, and off by default:

- **Variables set (only when ON):** `CLAUDE_CODE_ENABLE_TELEMETRY=1`,
  `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`
  (written to the `env` block of `~/.claude/settings.json`).
- **Snapshot before:** copy `~/.claude/settings.json` →
  `~/.tokcap/otel/settings.snapshot.<ISO8601>.json` and record its sha256 in the ledger's run
  log **before** any edit.
- **Toggle:** `tokcap otel on` (snapshot → add the three keys) / `tokcap otel off` (restore the
  most recent snapshot, or remove exactly the three keys if the snapshot is missing). `tokcap
  otel status` prints whether the keys are present and which snapshot is current.
- **Restore guarantee:** `off` must leave `settings.json` byte-identical to the pre-`on`
  snapshot; the toggle refuses to run if a snapshot cannot be written first.
- **Reconciliation flags OTEL-off windows** (§3b, §5 reconciler) so any gap is visible rather
  than silently under-counting.

---

## 3. Collectors

### 3a. `transcript_ingester`

- **Source:** incremental walk of `~/.claude/projects/*/`, reading each `*.jsonl` session file.
- **Watermarks (rotation-safe):** a `ingest_watermarks(file_path, inode, size, byte_offset,
  last_ts)` row per file. Each run seeks to the stored `byte_offset` and reads only new bytes,
  advancing the offset. Because transcripts are cleaned up ~every 30 days, the ingester never
  assumes a file still exists; a vanished file simply stops advancing, and its already-ingested
  rows persist in the ledger. A file whose `size` shrank or whose `inode` changed is treated as
  rotated → re-read from offset 0 under a new watermark. **Rotation never loses data because the
  ledger is the durable store, not the transcript.**
- **Dedupe:** one API response can span multiple JSONL lines, so rows are keyed by `requestId`;
  a second line carrying the same `requestId` updates (never duplicates) the `requests` row.
- **Attribution mapping (free, from the file layout):**
  - `slug` = the `<project-slug>` directory name;
  - `session_id` = the `<session-id>.jsonl` filename;
  - `agent` = `main` for normal assistant lines, or the sidechain identity for `sidechain`
    entries (subagent turns);
  - `model` = `message.model`; `ts` = the line timestamp;
  - token fields = `message.usage.{input_tokens, cache_creation_input_tokens,
    cache_read_input_tokens, output_tokens}`.
- **Limitation (recorded, not hidden):** transcripts miss invisible utility calls (haiku
  session-titling, compaction) — a few %. That gap is quantified by the reconciler (§5) against
  the OTEL total, not guessed at.
- **`source_tap = 'transcript'`** on every row it writes.

### 3b. `otel_receiver`

- **Purpose:** the **100%-complete** receipt stream — captures the `api_request` events
  transcripts miss (utility calls included), each carrying model + the 4 usage fields + an
  estimated cost, plus `claude_code.token.usage` counters.
- **Two candidate implementations (compared here, one recommended):**

  | | (i) official `otel-collector` binary + file exporter | (ii) minimal pure-Python OTLP/HTTP listener |
  |---|---|---|
  | Deps | external binary (Go), a `config.yaml` pipeline | **stdlib only** (`http.server` + protobuf/JSON decode) |
  | Surface | full OTLP feature set, battle-tested | just enough to accept `api_request` logs on `:4317` |
  | Failure modes | binary/version drift, its own config | our code, our bug surface |
  | Data path | writes JSONL files → ingested into ledger | writes straight into `ledger.db` |

  **Recommendation: (ii) the minimal pure-Python listener**, to honor the "no heavy deps"
  constraint (§10) and keep the whole system inspectable in one language. The official collector
  is only adopted if Claude Code's OTLP payload proves awkward to parse directly — in which case
  (i) becomes a fallback, writing to `~/.tokcap/otel/` for the ingester to pick up. Either way
  `source_tap = 'otel'`.
- **Gap flagging:** the receiver records its own uptime as `otel_uptime(started_at, ended_at)`
  spans. Any wall-clock period **not** covered by an uptime span is an **OTEL-off gap**; the
  reconciler (§5) marks reconciliations over those periods as `otel_incomplete = true` so no
  gap is silently treated as zero overhead.

### 3c. `meter_snapshotter`

- **Primary route — agent-browser scrape** of `claude.ai/settings/usage` using a **dedicated
  profile** at `~/.tokcap/ab-home` (`HOME=~/.tokcap/ab-home`; the known-good zero-plan-token
  observation pattern from EXPERIMENT_PLAN §3, Stream 2). Observation consumes **zero plan
  tokens**.
- **Parse every bar:** session %, weekly %, and the Opus bar **if present**, each with its
  **reset timestamp**. One `meter_snapshots` row per bar per scrape.
- **Cadence + tick-hunt mode:** the base cadence comes from `config.yaml`; near a boundary
  (approaching a reset, or when the tick_detector signals we are close to a bucket edge) the
  snapshotter switches to **fast-poll "tick-hunt mode"** to catch individual 1% ticks
  (EXPERIMENT_PLAN §4). Cadence is data-driven, not fixed.
- **Manual-entry fallback CLI:** `tokcap scrape --manual` prompts for a hand-read `/usage`
  value (the in-app ground truth) and records it with `source = 'portal_manual'`. This is the
  highest-trust source and always available even if the scraper breaks.
- **Unofficial OAuth/Keychain route = gated BONUS only.** The endpoint Claude Code itself calls
  (`api.anthropic.com/api/oauth/...usage`, token from the macOS Keychain item
  `"Claude Code-credentials"`) is documented but **disabled by default** and only enabled behind
  an explicit config flag (§7). It is never a load-bearing dependency (EXPERIMENT_PLAN §3,
  Stream 2, route 3).

### 3d. `probe_driver` (Phase 2)

- **Role:** executes the active controlled-dose loop of EXPERIMENT_PLAN §5 (read % → fire a
  known-weight probe → read % → log). This design does not re-derive the titration rationale;
  it specifies the mechanism.
- **Variant matrix from config:** the sweep `model × cache-state × effort` is read from
  `config.yaml` (§6); one factor is varied at a time (baseline = Sonnet / cold / default).
- **Vehicle:** `claude -p "reply: ok" --model <m> --output-format json` run with `cwd =
  /tmp/tokcap-probe/` (empty scratch, §2) and a **low `max_tokens`** clamp. The stdout JSON
  usage object is the exact, server-stated dose — recorded, never pre-computed.
- **Hard spend-cap enforcement:** before each probe the driver checks the running window spend
  (from the ledger) against a **configurable cap (default ≤ 10% of the window)** and **aborts
  the batch** if the next probe would breach it. Expensive cells (Fable/Opus) are only scheduled
  in expiring-budget slots (§8).
- **Quarantine check:** before starting a batch, the driver queries the ledger for any
  **non-probe traffic in the last N minutes** (N configurable); if found, it **aborts** (no
  parallel Claude usage may contaminate a probe batch). The always-on ledger is the backstop —
  any stray tokens are still attributed even if a batch slips through.
- **Titration strategy:** far from a tick → **large cheap doses (Haiku)** to march toward the
  edge; near a tick → **small doses, binary-search the bucket edge** (EXPERIMENT_PLAN §5).

---

## 4. Data Model (SQLite DDL sketch)

All tables in `~/.tokcap/ledger.db`. Types are indicative; `_id` columns are surrogate keys
unless noted. Join keys are listed after each block.

```sql
-- Exact receipts, one row per API response (the numerator).
CREATE TABLE requests (
  request_id       TEXT PRIMARY KEY,          -- dedupe key (from transcript/OTEL)
  session_id       TEXT REFERENCES sessions(session_id),
  window_id        INTEGER REFERENCES windows(window_id),
  ts               TEXT NOT NULL,             -- ISO8601
  slug             TEXT,                      -- project/slug (attribution)
  agent            TEXT,                      -- 'main' | sidechain id
  model            TEXT NOT NULL,
  input_tokens              INTEGER NOT NULL,
  cache_creation_input_tokens INTEGER NOT NULL,
  cache_read_input_tokens     INTEGER NOT NULL,
  output_tokens             INTEGER NOT NULL, -- includes hidden thinking
  est_cost_usd     REAL,                      -- OTEL-provided when source='otel'
  is_probe         INTEGER NOT NULL DEFAULT 0,
  source_tap       TEXT NOT NULL              -- 'transcript' | 'otel'
);

CREATE TABLE sessions (
  session_id   TEXT PRIMARY KEY,             -- = transcript filename stem
  slug         TEXT,
  first_ts     TEXT,
  last_ts      TEXT
);

-- 5h-rolling / weekly / opus segmentation (§5 window_segmenter).
CREATE TABLE windows (
  window_id    INTEGER PRIMARY KEY,
  bar_type     TEXT NOT NULL,                -- 'session_5h' | 'weekly' | 'opus_weekly'
  opened_at    TEXT NOT NULL,               -- first message of the window
  closes_at    TEXT,                        -- opened_at + span (rolling) / fixed reset
  reset_source TEXT                          -- 'gap_rule' | 'meter_reset'
);

CREATE TABLE meter_snapshots (
  snapshot_id  INTEGER PRIMARY KEY,
  ts           TEXT NOT NULL,
  bar_type     TEXT NOT NULL,
  percent      REAL NOT NULL,               -- rounded whole % as shown
  reset_at     TEXT,                        -- bar's reset timestamp when shown
  source       TEXT NOT NULL                -- 'scrape' | 'portal_manual' | 'oauth'
);

-- Derived: an observed 1% movement between two consecutive snapshots of one bar.
CREATE TABLE ticks (
  tick_id      INTEGER PRIMARY KEY,
  bar_type     TEXT NOT NULL,
  from_snapshot_id INTEGER REFERENCES meter_snapshots(snapshot_id),
  to_snapshot_id   INTEGER REFERENCES meter_snapshots(snapshot_id),
  buckets      INTEGER NOT NULL,            -- whole-% delta (k)
  tokens_between_weighted REAL NOT NULL,    -- Σ weighted tokens in the interval (T)
  lower_bound_C REAL,                       -- from T/(k+1)% (or 100*T if k=0)
  upper_bound_C REAL,                       -- from T/(k-1)%
  is_interior  INTEGER NOT NULL DEFAULT 0   -- exclude first/last partial bucket
);

CREATE TABLE probes (
  probe_id       INTEGER PRIMARY KEY,
  request_id     TEXT REFERENCES requests(request_id),
  batch_id       TEXT,
  model          TEXT, cache_state TEXT, effort TEXT,  -- the variant
  before_snapshot_id INTEGER REFERENCES meter_snapshots(snapshot_id),
  after_snapshot_id  INTEGER REFERENCES meter_snapshots(snapshot_id)
);

-- Daily OTEL vs transcript delta = invisible overhead.
CREATE TABLE reconciliations (
  recon_id         INTEGER PRIMARY KEY,
  day              TEXT NOT NULL,
  otel_total_weighted        REAL,
  transcript_total_weighted  REAL,
  invisible_overhead_weighted REAL,          -- otel - transcript
  otel_incomplete  INTEGER NOT NULL DEFAULT 0 -- true if day had an OTEL-off gap
);

-- Versioned capacity constants, one per bar per estimation run.
CREATE TABLE capacity_estimates (
  est_id          INTEGER PRIMARY KEY,
  bar_type        TEXT NOT NULL,
  plan_tier       TEXT NOT NULL,             -- 'pro' | 'max_5x' | 'max_20x'
  value_weighted_tokens REAL,
  value_usd_equiv REAL,
  error_band_pct  REAL,                      -- ± from the bounds/regression
  method          TEXT,                      -- 'bounds' | 'regression'
  price_table_version INTEGER REFERENCES price_table(version),
  created_at      TEXT NOT NULL
);

-- Versioned API weights (the regression seed / weighting engine input).
CREATE TABLE price_table (
  version          INTEGER,
  model            TEXT,
  input_price_per_m   REAL,
  cache_write_mult    REAL,                  -- e.g. 1.25
  cache_read_mult     REAL,                  -- e.g. 0.10
  output_price_per_m  REAL,
  effective_at     TEXT,
  PRIMARY KEY (version, model)
);
```

**Join keys.**
- `requests.session_id → sessions.session_id`; `requests.window_id → windows.window_id`.
- `requests.model + price_table.version → price_table(model, version)` for weighting (§5).
- `probes.request_id → requests.request_id`; `probes.before/after_snapshot_id →
  meter_snapshots.snapshot_id`.
- `ticks.from/to_snapshot_id → meter_snapshots.snapshot_id` (a tick is derived from two
  consecutive snapshots of the same `bar_type`).
- `capacity_estimates.price_table_version → price_table.version` (an estimate is pinned to the
  weights it used).
- `reconciliations.day` groups `requests.ts::date` across both `source_tap` values.

---

## 5. Processors

All processors are pure ledger→ledger (or ledger→output) functions; none touch the network.

- **`window_segmenter`** — assigns every `requests` row to a `windows` row. Session windows use
  the **>5h-gap rule** (EXPERIMENT_PLAN §3, Stream 3): the first message after a >5h gap opens a
  new `session_5h` window; weekly windows come from the fixed 7-day reset; the Opus bar (if
  present) gets its own. Recoverable from transcripts alone — no meter data required.
- **`weighting_engine`** — computes both totals per the EXPERIMENT_PLAN §3 definitions:
  `UE = input + cache_creation + cache_read + output` (cache-independent volume) and
  `BW = input + cache_creation×1.25 + cache_read×0.1 + output` (billed weight), using the pinned
  `price_table` version for the multipliers/model prices.
- **`reconciler`** — per day, `otel_total − transcript_total = invisible_overhead`, written to
  `reconciliations`; sets `otel_incomplete` when the day overlaps an OTEL-off gap (§3b). This is
  the Phase-0 gate metric (reconciliation gap explained and < 5%).
- **`tick_detector + bounds_accumulator`** — walks consecutive `meter_snapshots` per `bar_type`,
  emits `ticks`, and accumulates capacity bounds (EXPERIMENT_PLAN §4): a `T`-token interval with
  **no tick → C > 100×T**; a **k-tick jump → T/(k+1)% < C < T/(k−1)%**; interior ticks are exact,
  first/last partial buckets discarded. Wider spans tighten the band (weekly bar = precision
  champion).
- **`calibration_solver`** — fits one regression over the whole probe/tick log:
  `Δbuckets ≈ Σ weight(model, field) × tokens`, **seeded with `price_table`** as the starting
  weights (cache-write 1.25×, cache-read 0.1×, model $/M). Writes `capacity_estimates` with
  `method='regression'` and the resulting weight corrections. Solved with a small stdlib
  least-squares (normal equations, ~5–8 unknowns; §10) — no numpy.
- **`drift_monitor`** — re-runs estimation continuously; if a fresh `capacity_estimates` value
  shifts beyond its error band from the prior version, it flags a **capacity change** (Anthropic
  can silently re-weight the meter) and restarts estimation for that bar/tier.
- **`predictor`** — given the current window's partial `requests`, projects "**this session ≈
  N% of the window**" against the latest `capacity_estimates`; validated to < 10% error in
  Phase 3.

---

## 6. Interfaces

**CLI verbs** (`tokcap <verb>`):

| Verb | Does |
|------|------|
| `ingest` | run `transcript_ingester` (+ absorb any OTEL spool) up to now |
| `scrape` | run `meter_snapshotter` once (`--manual` for hand-entry, `--tick-hunt` to fast-poll) |
| `probe` | run one `probe_driver` batch (Phase 2; obeys cap + quarantine) |
| `report` | render rollups (raw + weighted) to text/CSV/HTML |
| `predict` | print current-window/session cost projection as % of the bar |
| `status` | show ledger freshness, OTEL on/off + gaps, last scrape, current bounds/estimates |
| `otel on\|off\|status` | the global-side-effect toggle (§2) |

**`config.yaml` shape** (in `~/.tokcap/`):

```yaml
cadences:
  ingest: "1h"
  scrape: "30m"           # base; tick-hunt overrides near boundaries
  scrape_tick_hunt: "60s"
caps:
  probe_window_fraction: 0.10   # ≤10% of a window per batch (hard)
  quarantine_minutes: 15        # abort batch if non-probe traffic seen within
variant_matrix:                 # swept one factor at a time (§3d)
  models:      [haiku, sonnet, opus, fable]
  cache_state: [cold, warm]
  effort:      [low, default, high]
price_table_version: 3          # which weights the weighting/solver use
routes:
  oauth_bonus_enabled: false    # unofficial Keychain endpoint OFF by default (§7)
```

**Report rollups:** every report can group by `global / slug / session / agent / model / day`
and always shows **both** raw fields and weighted totals (UE and BW).

---

## 7. Privacy & Security

- **Metadata only.** The ledger stores **usage counts and attribution metadata only** — model,
  token counts, timestamps, slug, session/agent ids. It **never stores message content**
  (prompts, completions, tool output). Transcript/OTEL parsing reads only the `usage` object and
  routing fields.
- **Scraper credential isolation.** The agent-browser login lives entirely in
  `~/.tokcap/ab-home` (§2, §3c); no cookies/tokens are copied elsewhere, and that profile is
  never committed.
- **Keychain/OAuth route off by default.** `routes.oauth_bonus_enabled` defaults `false`; the
  macOS Keychain token (`"Claude Code-credentials"`) is read only when a founder explicitly
  flips it on, and even then it is a bonus cross-check, never a dependency.
- **Local only.** Nothing leaves the machine: the OTEL endpoint is `localhost:4317`, the ledger
  is a local file, reports are local files.

---

## 8. Scheduling (macOS launchd)

launchd (not cron) is used because it is the macOS-native per-user scheduler, survives reboot,
and coalesces missed timers. Example agents (installed under `~/Library/LaunchAgents/`, plists
written by `tokcap`):

```xml
<!-- com.tokcap.ingest.plist — hourly transcript ingest -->
<key>ProgramArguments</key><array>
  <string>/usr/bin/python3</string><string>-m</string><string>tokcap</string><string>ingest</string>
</array>
<key>StartInterval</key><integer>3600</integer>   <!-- 1h -->
```

```xml
<!-- com.tokcap.scrape.plist — meter snapshot on cadence -->
<key>StartInterval</key><integer>1800</integer>    <!-- 30m base; tick-hunt runs are ad-hoc -->
```

- **`ingest`** — hourly (cheap, local; keeps the ledger fresh so caps/quarantine are accurate).
- **`scrape`** — on the base cadence, with tick-hunt fast-poll runs triggered ad-hoc near a
  boundary rather than as a fixed timer.
- **`probe`** — **not a fixed timer.** Probe batches are launched only into **use-it-or-lose-it
  slots** — the final stretch before a session-window reset, or pre-weekly-reset — because probes
  spend the very budget being measured (EXPERIMENT_PLAN §5). Expensive (Fable/Opus) cells go in
  expiring-budget slots. A calendar-of-resets helper schedules these one-shot launches.

---

## 9. Failure Modes & Mitigations

| Failure mode | Mitigation |
|---|---|
| **Transcript rotation race** (~30d cleanup deletes a file mid-read, or during ingest) | Ledger is the durable store; inode+size watermarks detect rotation and re-key; a vanished file just stops advancing — already-ingested rows persist (§3a). |
| **JSONL schema drift** (a Claude Code update changes the transcript shape) | Parser is defensive: unknown line types skipped + counted; a spike in "unparsed lines" is surfaced by `status`; OTEL (§3b) is the independent cross-check so drift is caught by a widening reconciliation gap. |
| **Scraper login expiry** | Manual-entry fallback CLI (§3c) keeps the meter stream alive; `status` flags stale scrapes; re-login re-uses the isolated `ab-home` profile. |
| **OTEL-off gaps** | Uptime spans → reconciliations flagged `otel_incomplete` (§3b, §5); gaps are visible, never counted as zero. |
| **Meter lag & rounding (±1%)** | Reads paired to ledger only when idle 1–2 min; every capacity number carries its quantization error band (EXPERIMENT_PLAN §4); rounding mode discovered from tick spacing. |
| **Plan-tier change** (Pro↔Max) | Capacity constants are keyed by `plan_tier`; the drift_monitor detects the shift, **auto-invalidates** the affected `capacity_estimates`, and **restarts estimation** for that tier. |
| **Probe over-spend / contamination** | Hard spend-cap + quarantine check in `probe_driver` abort the batch before breach (§3d); always-on ledger attributes stray tokens as a backstop. |

---

## 10. Tech Stack + Rejected Alternatives

**Chosen:** **Python 3.12 stdlib + `sqlite3`.** No cloud, no server infra, no heavy deps. Reports
are plain **HTML/CSV** files. The only external tool is the already-available **agent-browser**
for scraping. Regression is a hand-rolled stdlib least-squares (small system).

| Rejected | Why |
|---|---|
| Postgres / DuckDB | Single-user, single-machine, modest data → `sqlite3` (stdlib) is sufficient and zero-install. |
| pandas / numpy | The rollups are SQL `GROUP BY`; the calibration is a ~5–8-unknown least-squares solvable with stdlib normal equations. numpy stays a **rejected optional** — only revisited if the regression grows large. |
| Grafana / a dashboard framework | Outputs are plain HTML/CSV; a dashboard is unjustified surface area for a personal calibration tool. |
| `cron` | launchd is the macOS-native per-user scheduler, survives reboot, coalesces missed runs (§8). |
| Selenium / a bespoke headless browser | agent-browser is already present with a known-good zero-token observation pattern (§3c). |
| A cloud OTEL backend (Honeycomb, etc.) | Privacy (§7) — telemetry must never leave the machine; the local listener writes straight to the ledger. |
| Official otel-collector as the default | Kept only as a fallback (§3b); the minimal pure-Python listener honors "no heavy deps". |

---

## 11. Phase Mapping & Build Order

Components map onto the EXPERIMENT_PLAN §7 phases; within each phase the dependency order is
listed left→right.

| Phase (gate) | Components delivered | Build order (deps →) |
|---|---|---|
| **Phase 0** — passive ledger, zero spend (gate: OTEL↔transcript reconciliation < 5%) | `price_table` seed · ledger schema · `transcript_ingester` · `window_segmenter` · `weighting_engine` · `otel_receiver` (+ OTEL enablement decision) · `reconciler` · `tokcap ingest/status` | schema → ingester → segmenter → weighting → otel_receiver → reconciler |
| **Phase 1** — passive calibration, zero extra spend (gate: capacity band ≤ ±20% from organic data) | `meter_snapshotter` (scrape + `--manual`) · `tick_detector + bounds_accumulator` · `capacity_estimates` (method `bounds`) · `tokcap scrape/report` | snapshotter → tick_detector → bounds → capacity(bounds) |
| **Phase 2** — active probing, spend-capped (gate: weekly ±2%, session ±5–10%, weights fitted) | `probe_driver` (dose loop, cap, quarantine, titration) · `probes` table · `calibration_solver` (regression) · `tokcap probe` | probe_driver → probes → calibration_solver |
| **Phase 3** — validation + drift (gate: prediction error < 10% over 5+ sessions → CALIBRATED) | `predictor` · `drift_monitor` (continuous re-estimation) · `tokcap predict` | predictor → drift_monitor |

**Cross-phase invariant:** the ledger schema (§4) is created once in Phase 0 and only **added
to** (new tables) in later phases — never reshaped — so every processor can re-run idempotently
over all history as the system grows.
