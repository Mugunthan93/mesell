# RTK Token-Optimization Experiment — End-to-End Plan

**Status:** DRAFT — Phase 0 not started
**Owner:** Founder (Muguntha) + master Claude session
**Created:** 2026-07-11
**Tracking:** `RESULTS_LOG.md` in this directory (created at Phase 0 start)

---

## 1. Objective

Determine whether installing [rtk-ai/rtk](https://github.com/rtk-ai/rtk) (Apache 2.0, verified real in source review 2026-07-11) measurably reduces Claude Code token consumption **for our actual workflow** — main session and subagents — without degrading output quality, so a Pro-plan usage window buys more real work.

### Hypotheses

| ID | Hypothesis | Tested in |
|----|-----------|-----------|
| H1 | A meaningful share (≥20%) of our context tokens flow through **Bash tool results** — the only surface RTK can compress (built-in Read/Grep/Glob bypass its hook) | Phase 0 |
| H2 | With RTK's hook installed, per-task token usage drops ≥15% on bash-heavy tasks with **no quality regression** | Phase 1 |
| H3 | Subagents inherit the PreToolUse hook — RTK's "100% adoption incl. subagents" claim holds | Phase 1 |
| H4 | The effect holds (or varies predictably) across models and effort levels | Phase 2 |

---

## 2. Ground Rules (non-negotiable)

1. **Never in the MeeSell master tree.** All live runs happen on scratch clones under `/tmp/rtk-exp/`.
2. **Reversible install only.** Snapshot `~/.claude/settings.json` (and any hook files) BEFORE `rtk init`; restore after each phase. A global hook affects every project in the workspace (Aletheia, Prospero, …) — it must never linger outside experiment windows.
3. **Quality is the hard constraint.** A token saving that produces a wrong/incomplete task result = FAIL for that cell, regardless of % saved.
4. **Budget cap per phase** (see §7). If a phase exceeds its cap before producing a decision, stop and record `INCONCLUSIVE — over budget`.
5. **Every run is logged** in `RESULTS_LOG.md` before the next run starts. No batch backfilling from memory.
6. **Decision gates are pre-committed.** The thresholds in this doc were fixed before any data was collected; they are not adjusted post-hoc.

---

## 3. Measurement Methodology

**Primary metric — real API usage from session transcripts.** Every Claude Code session writes JSONL to `~/.claude/projects/<project-slug>/<session-id>.jsonl` with per-turn `usage` blocks:
`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`.

- **Uncached-equivalent total** (controls the cache confound):
  `UE = input + cache_creation + cache_read + output` (raw volume, cache-state-independent)
- **Billed-weight total** (what actually hits the plan):
  `BW = input + cache_creation×1.25 + cache_read×0.1 + output` (relative weights)
- Report both. Cells are only comparable on UE; BW shows real-world impact.

**Secondary metrics:**
- RTK adoption: `rtk gain` / tracking stats — how many bash calls were actually rewritten (tests H3 and agent-behavior).
- Tool-mix: count of Bash vs Read/Grep/Glob tool calls per session (from JSONL).
- Quality: task-specific rubric fixed per task in §5.3, scored blind to condition where possible.

**Confound controls:**
- Fresh session per run (no shared context).
- Same task prompt byte-for-byte per cell.
- Runs of a matched pair (RTK-on / RTK-off) executed back-to-back in the same hour.
- N=2 repetitions minimum per cell — single runs are noise (LLM nondeterminism between identical runs can exceed a 15% effect).

---

## 4. Phase 0 — Ceiling Measurement (near-zero cost, read-only)

**Question:** What is the *maximum possible* RTK saving for our real historical workflow?

**Method:** Script mines existing local transcripts (`~/.claude/projects/*/*.jsonl`, last 30 days):
1. For each `tool_result`, attribute its token estimate to the tool that produced it (Bash / Read / Grep / Glob / Task / other).
2. Compute **Bash-share** = Bash-result tokens ÷ all tool-result tokens, per project and overall.
3. Apply RTK's own measured compression ratios (~60-90% on supported commands) to the Bash share → theoretical ceiling %.

**Deliverable:** `phase0-ceiling-report.md` — Bash-share per project, overall ceiling, top-10 token-heaviest bash command types.

### Decision gate G0

| Outcome | Criterion | Action |
|---------|-----------|--------|
| ✅ PROCEED | Bash-share ≥ 20% | Run Phase 1 |
| ⚠️ MARGINAL | 10% ≤ Bash-share < 20% | Founder decides: proceed with reduced expectations, or stop |
| ❌ STOP | Bash-share < 10% | RTK ceiling too low for our workflow. Record verdict. **Failure path →** pivot to the levers that DO cover our token mass: delegation discipline (subagent read-offload), Read/Grep-slice discipline, model routing. Close experiment. |

---

## 5. Phase 1 — Pilot A/B (small, controlled)

**Precondition:** G0 = PROCEED (or founder-approved MARGINAL).

### 5.1 Setup
1. Snapshot `~/.claude/settings.json` + hooks dir → `/tmp/rtk-exp/settings-backup/`.
2. Install RTK binary (via `meesell-infra-builder` per project rules; or founder installs manually).
3. `rtk init` scoped to the scratch clone only if supported; otherwise global install with restore after every session-pair.
4. Verify hook fires: one manual `git status` through a test session; confirm rewrite in transcript.

### 5.2 Design — 2×2×2 = 8 runs

| Factor | Levels |
|--------|--------|
| Session type | main session / subagent-heavy |
| RTK | on / off |
| Repetition | 2 |

Model fixed: **Sonnet**. Effort fixed: default. Task fixed (see 5.3).

### 5.3 Task + quality rubric (fixed before first run)
**Task:** bash-heavy diagnostic on a scratch clone of a real repo (e.g. RTK's own repo): "run the test suite, identify all failing/warning areas, produce a structured findings report." Uses pytest/cargo, git log/diff, grep — RTK's strongest surfaces.
**Quality rubric (pass/fail per item):** (a) all genuinely failing areas found (vs. answer key established once beforehand), (b) no hallucinated failures, (c) report complete per prompt structure. Any item failed → cell flagged QUALITY-FAIL.

### 5.4 Decision gate G1

| Outcome | Criterion | Action |
|---------|-----------|--------|
| ✅ PROCEED | Median UE saving ≥ 15% AND zero QUALITY-FAIL AND adoption ≥ 80% of eligible bash calls | Run Phase 2 |
| 🔧 REMEDIATE | Saving < 15% BECAUSE adoption < 80% (agents bypassed bash / hook missed calls) | ONE remediation attempt: add CLAUDE.md nudge in scratch repo steering agents to shell commands for search/read-heavy steps; re-run the failing cells once. Then re-apply G1. No second remediation. |
| ❌ STOP | Saving < 5% with good adoption, OR any QUALITY-FAIL attributable to RTK truncation (verify by re-running that cell RTK-off) | Uninstall, restore settings, record verdict. **Failure path →** same pivot as G0-STOP; additionally file upstream issue if a specific RTK filter dropped load-bearing output. |
| ⚠️ INCONCLUSIVE | 5-15% saving, or reps disagree wildly (spread > effect) | Founder decides: +2 reps (budget permitting) or accept as MARGINAL and stop. |

**H3 check (subagents):** compare adoption % in subagent-heavy cells vs main-session cells. If subagent adoption ≈ 0 → RTK's subagent claim fails for our harness → note in verdict; RTK value drops sharply for our dispatch-heavy workflow.

---

## 6. Phase 2 — Expansion (one contrast at a time, NOT a grid)

**Precondition:** G1 = PROCEED. The full matrix (4 models × 4 efforts × 2 sessions × 2 conditions × 2 reps = 128 runs) is explicitly REJECTED — it would cost more than months of the savings it measures.

Run sequential contrasts, each with its own mini-gate; stop when marginal value of the next contrast < its cost:

| # | Contrast | Question | Runs |
|---|----------|----------|------|
| 2a | Haiku vs Sonnet (RTK on/off) | Do cheaper models benefit more (less able to self-summarize)? | 8 |
| 2b | Opus (RTK on/off) | Does the effect hold at the expensive end (biggest ₹ impact)? | 4 |
| 2c | Effort: low vs high on one model | Does thinking effort change bash-output volume enough to matter? | 8 |

**Gate per contrast:** same structure as G1 (≥15% = strong, <5% = stop expanding that axis). Results appended to `RESULTS_LOG.md`.

---

## 7. Budget Caps

| Phase | Cap (approx. UE tokens) | Rationale |
|-------|------------------------|-----------|
| 0 | ~50K (script writing + report; mining is local CPU, not API) | Read-only |
| 1 | ~1.5M across 8-12 runs | ~120-150K/run for a full diagnostic task |
| 2 | ~2M per contrast, founder-approved before each | Only spent if Phase 1 proved ≥15% |

Runs happen in off-hours windows so experiment consumption doesn't starve real work windows.

---

## 8. Phase 3 — Decision & Rollout (only after PROCEED verdicts)

1. **Verdict memo** in this directory: measured saving, quality record, adoption %, recommendation.
2. If ADOPT: staged rollout — enable for scratch/experiment work first, then one real project for a week (monitored via transcripts), then workspace-wide. Keep the settings snapshot as permanent rollback.
3. If REJECT: uninstall, restore snapshot, record verdict + the pivot plan (delegation discipline, Read-slice discipline, model routing) so the effort still yields a token-reduction outcome.
4. Either way: persist all artifacts (this plan, RESULTS_LOG, reports, verdict) per Task Completion Protocol Rule A (scribe branch + PR).

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Global hook leaks into real project sessions mid-experiment | Settings snapshot + restore after every session-pair; verify with `grep rtk ~/.claude/settings.json` before real work |
| RTK filter drops load-bearing output → agent hallucinates around the gap | Quality rubric per cell; any QUALITY-FAIL triggers RTK-off re-run of same cell to attribute cause |
| Cache state contaminates comparison | UE metric (cache-independent) is primary; matched pairs run back-to-back |
| Experiment itself burns the Pro window | Phase caps (§7); Phase 0 first (near-free); off-hours runs |
| Nondeterminism swamps effect | N=2 minimum, spread-vs-effect check in G1; INCONCLUSIVE path defined |
| `rm`/install restrictions in MeeSell context | Install/uninstall via `meesell-infra-builder` or founder-manual; never by the master session directly |

---

## 10. Tracking

- **`RESULTS_LOG.md`** (same dir): one row per run — `run-id | date | phase | cell | model | effort | session-type | rtk | UE | BW | adoption% | quality | notes`. Written immediately after each run.
- Phase reports: `phase0-ceiling-report.md`, `phase1-pilot-report.md`, `phase2-<contrast>-report.md`, `VERDICT.md`.
- Status header of this file updated at every gate crossing.
