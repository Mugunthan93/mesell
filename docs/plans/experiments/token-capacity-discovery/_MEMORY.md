# tokcap — infra-builder working memory (ISOLATED)

> **Why this file exists.** Founder ruling 2026-07-17: the token-capacity-discovery experiment
> (tokcap) is **ISOLATED from MeeSell** — it lives ONLY on branch
> `chore/token-capacity-discovery/plan` (+ worktree `/tmp/mesell-wt/tokcap`), **never merges to
> `develop`**, and must **touch no file outside `docs/plans/experiments/token-capacity-discovery/`**.
> So tokcap learnings do NOT go into the shared `.claude/agent-memory/meesell-infra-builder/MEMORY.md`
> (that would be a file outside this dir, and it must never route to develop). They live here,
> on-branch, instead. This is the tokcap memory locus; read it at the start of any tokcap session.

---

## 2026-07-17 — session `mesell-token-capacity-discovery-plan-infra-session-1` (+ architecture follow-up)

**What tokcap is.** The dev subscription IS the budget (API-key metered mode is unaffordable),
so we need (A) a 100%-exact per-request token **ledger** with hierarchical attribution
`global → slug → session → agent → request`, and (B) **capacity discovery** — measure the
denominator `C` = what 100% of the 5h rolling session window / fixed weekly bar equals in
*weighted* tokens per model. Motivating incident: Pro meter jumped to 40% after ONE session.
Sibling of `rtk-token-adoption` (shares transcript-mining; tokcap's ledger generalizes RTK
Phase 0's script). Two docs authored (DRAFT, nothing built): `EXPERIMENT_PLAN.md` (objective,
3 data streams, quantization math, active-dose calibration §5, phases 0–3 + gates) and
`ARCHITECTURE.md` (collectors → SQLite ledger → processors → outputs; 4 collectors, 9 tables,
7 processors, launchd scheduling, stdlib+sqlite3 only).

**Design anchors (so future me doesn't re-read both docs):**
- **Core method = active controlled-dose calibration (titration):** read % → fire a
  known-weight probe (`claude -p "reply: ok" --model <m> --output-format json` from empty
  `/tmp/tokcap-probe/` = no ~78K workspace-context tax; the server receipt STATES the exact
  dose, never pre-compute) → read % → log. Sweep model×cache-state×effort one axis at a time;
  regress `Δbuckets ≈ Σ weight(model,field)×tokens`, seeded with API prices (cache-write 1.25×,
  cache-read 0.1×).
- **3 data streams:** receipts (transcripts `~/.claude/projects/<slug>/<sess>.jsonl` dedupe by
  `requestId`, attribution free from dir/file/sidechain + OTEL `api_request` @ localhost:4317
  = 100% incl. utility calls), meter % (agent-browser scrape of claude.ai/settings/usage with
  `HOME=~/.tokcap/ab-home`; `/usage` manual fallback; unofficial Keychain/OAuth endpoint =
  BONUS-only, off by default; ratelimit headers = API-key-ONLY = closed on subscription),
  boundaries (5h rolling opens at first msg / weekly fixed / maybe Opus bar; recoverable from
  transcripts via the >5h-gap rule).
- **Quantization:** 1% bucket = C/100; tick-hunting; bounds `C>100T` (no tick) and
  `T/(k+1)% < C < T/(k−1)%` (k-tick jump); wide spans shrink error (1 tick ±100% … ~100 ticks
  ±2% = weekly bar is the precision champion).
- **Runtime home = `~/.tokcap/` (NEVER committed):** ledger.db, config.yaml, logs, ab-home
  scraper profile. The ONE global side-effect = OTEL env-vars in `~/.claude/settings.json`
  (affects ALL workspace projects) → snapshot/restore + `tokcap otel on|off|status` toggle.
- **Phases 0(passive ledger, gate <5% OTEL↔transcript) → 1(passive calib, gate band ≤±20%) →
  2(active probe, gate weekly ±2%/session ±5–10%) → 3(validate <10% over 5+ sessions, then
  continuous drift re-estimation).**

**🔴 REUSABLE GIT GOTCHA — `guard-master-tree-git` blocks history-write verbs from master CWD.**
The PreToolUse guard blocks the ENTIRE Bash call (nothing runs, not even a preceding `git add`)
when the tool's DEFAULT CWD is the master checkout AND the command contains a history-write verb
(`git commit`/`merge`). A `cd <worktree>` *inside the same compound command does NOT help* —
the hook evaluates statically BEFORE the cd runs. **FIX = path-explicit
`git -C <worktree> add`/`git -C <worktree> commit`** → the guard resolves the `-C` target as a
non-master worktree and allows it (verified: `git -C` add+commit both passed; the identical op
after a bare `cd` was blocked). Cleaner than the `MESELL_ALLOW_MASTER_GIT=1` override, which is
reserved for genuine master-tree recovery.

**🔴 ISOLATION MECHANICS (this session).** PR #516 (the EXPERIMENT_PLAN PR to develop) was
CLOSED by the Director without merging per the founder ruling — tokcap must never merge. My
first commit `824dbd5` had (pre-ruling) appended tokcap learnings to the shared
`.claude/agent-memory/meesell-infra-builder/MEMORY.md`, which is a file OUTSIDE this dir. To
honor "touch no file outside the tokcap dir," I **restored that shared MEMORY.md to the develop
baseline (`bc58347`) on this branch** (it never reached develop — PR closed — so nothing was
lost from develop) and **relocated the learnings here** into `_MEMORY.md`. Net branch diff vs
the branch point is now **tokcap-dir-only**. Rule for future tokcap work: persist learnings HERE,
commit + push the BRANCH to origin (NO PR, no develop merge), and never edit the shared agent
memory from this branch.

**Cost/impact:** ₹0, docs-only, nothing built, no scripts/settings/telemetry/probes.

## POC results 2026-07-18 (master session bae00058, direct-mode, unattended)
- **Group 1 (transcript reality check) ALL GREEN** + 3 corrections now proven with numbers: (1) **recursive glob mandatory** — subagent transcripts live at `~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl` and are **49% of all weighted spend** (a non-recursive glob undercounts by ~half); (2) **dedup mandatory** — up to 24 lines/requestId, 20,507 merges had *differing* usage → **per-field-MAX** is the correct rule (usage varies across a request's lines, not identical-repeat); (3) slug needs worktree→parent normalization (+ a native `slug` field exists).
- **Group 2 (OTEL) SUCCESS**: O1 byte-identical settings toggle; O2 local OTLP **http/json** listener on `:4318` receives `claude_code.token.usage` (by `type`) + `claude_code.cost.usage` with attrs incl. **`query_source` (main/subagent)** + org/user ids. Listener must decode **chunked+gzip** (Content-Length can be absent). `claude -p --output-format json` returns its own usage + `total_cost_usd`. "Empty" scratch still loads **~27K cache-creation** baseline. Probes: cold $0.054 / warm $0.0245.
- **Phase 0 ledger BUILT** (`tools/tokcap_ledger.py`, read-only, SQLite → `~/.tokcap/ledger.db`, 46,708 reqs). Corpus ≈ **$4,879** API-equiv; **capacity lower bound 81.88M BW** (max window).
- **Phase 1 BLOCKER**: live % sensor — agent-browser scrape **Cloudflare-blocked**; needs founder pick of (a) headed-login-seed / (b) OAuth-endpoint / (c) manual bracketing. Tick/bounds calibration blocked until then.

## Sensor route (b) LIVE 2026-07-18
- **Working recipe** in `tools/tokcap_meter.py`: Keychain acct=login-user (NOT root) → `/api/oauth/usage` (Bearer + UA + oauth-2025-04-20) → `limits[]` bars (session/weekly_all/weekly_scoped-per-model), `resets_at`=ISO string. 60s floor (429s on rapid polls). Guard: `--guard 90` → rc 1 at ≥90.
- **Critical lesson**: transcript ledger lags live sessions (flush lag) — proxy read 0.8% when real meter read 49% (~60×). Historical attribution only; **live guard = this sensor**.
- Live observation: session 49%→81% in ~26min of Fable-max master-session turns — model choice dominates burn, exactly as plan §2 predicted.

## Phase-2 batches 1–3 (2026-07-18)
- Effort axis CLOSED: no surcharge; effort = dose size (out-tokens), receipts capture it. Haiku rejects `--effort` (not a variable there).
- Clean-batch discipline: quarantine mandatory; live human log for founder; pre-flight per dose (ceiling breach forbidden, founder rule "check ongoing will finish before ceiling").
- Weight question OPEN; clean bound 1% ≥ $0.066 (C_session ≥ $6.6, likely 7–10); warm-cache nearly free; batch-1 $3.9 estimate was contamination artifact — NEVER trust tick math from unquarantined windows.
- Reset anomaly: fresh bar read 31% at reset+1min — carryover/lag semantics unknown; reproduce before relying on "reset = 0%".
