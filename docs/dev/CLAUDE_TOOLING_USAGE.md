# MeeSell Claude Tooling Usage

> **What:** when-to-use guidance for the three lighter Claude tooling primitives MeeSell is
> adopting — **TaskCreate/TaskList**, **`/loop`**, and **`/deep-research` + WebSearch/WebFetch**.
> Advisory. These are productivity ergonomics, not gates: they replace re-reading long board
> prose, automate the recurring sweeps that get skipped, and ground SPECs in current external
> docs past the model's Jan-2026 cutoff. See `docs/dev/CLAUDE_FEATURE_ADOPTION.md` for the
> full adoption plan and sequence (these three are the §4 "quick wins" / §2 medium-impact tier).

## TaskCreate / TaskList — multi-step work tracking

Use the built-in task tools to hold the steps of a multi-step job in a lightweight list
instead of re-reading the status board prose (`feature_board_*.md`, ~3,100 lines) on every
turn.

- **Use when:** a task has 3+ ordered steps (e.g. a feature wave plan, a migration apply
  sequence, a multi-surface infra cutover, an integration->develop checklist).
- **Use when:** resuming after a context break — one `TaskList` query restores "where was I"
  faster than re-parsing the board row prose.
- **Don't use for:** single-step chores (a docs flip, one status append) — the ceremony costs
  more than it saves.
- **Don't replace** the status board or `feature_board_*.md` with it — TaskList is per-session
  scratch state; the board remains the founder's single durable query surface. Land outcomes
  on the board / coordinator memory, not only in the task list.
- **MeeSell fit:** encode the HYBRID 3-step dispatch (coordinator SPEC -> specialist build ->
  coordinator merge-gate review) and the two-step merge gate (group->integration->develop) as
  task items so neither step is silently skipped.

## `/loop` — recurring board / PR sweeps

Use `/loop` to run a recurring action — the kind of sweep that gets skipped under time
pressure — on a defined cadence within a session.

- **Use when:** doing a session-start / session-end board sweep (rows untouched 7+ days), an
  open-PR triage pass, or a "re-check the inter-lead requests open" pass.
- **Hard rule — ONE build-gated rebuild at a time:** the 8GB dev box deadlocks on parallel
  esbuild / `ng build`. If a loop iteration triggers a rebuild (e.g. rebuild a touched MFE,
  re-run a smoke), it MUST be serial — one rebuild per iteration, never fan out builds across
  loop iterations. Honor the single-build mutex / env-manager RAM budget.
- **Use when:** the action is read-mostly (sweeping board state, listing PRs, diffing) — those
  are RAM-cheap and loop safely.
- **Don't use for:** anything spend-bearing or destructive (no `gcloud delete`, no apply to a
  namespace) on an unattended cadence — those stay one-shot and founder-gated.
- **MeeSell fit:** replaces the manually-remembered board sweeps mandated at session start and
  end; keeps the board accurate without a human remembering to look.

## `/deep-research` + WebSearch / WebFetch — grounding SPECs in current docs

Use these to ground a SPEC in CURRENT external documentation when the model's Jan-2026
training cutoff may be stale or the API surface moves fast.

- **Use when:** writing or reviewing a SPEC that depends on a fast-moving external API —
  notably **Razorpay** (Subscriptions / webhook signature / payload shape), **Google Identity
  Services (GIS)** for the held google-auth work (button flow, CSP / origin requirements,
  `email_verified` semantics), and **Angular** (version-specific federation / standalone /
  build behavior).
- **`/deep-research`:** for a broad "what's the current recommended approach" question that
  needs multiple sources synthesized (e.g. "current Razorpay subscription webhook verification
  best practice").
- **WebSearch / WebFetch:** for a targeted lookup — fetch the one canonical doc page or confirm
  a single API field / parameter before committing it to a SPEC.
- **Always cite** the source URL + the date checked in the SPEC, so a later reader knows the
  grounding is current and can re-verify.
- **Don't** paste secrets, internal hostnames, or `mesell.xyz` infra detail into a web query.
- **MeeSell fit:** prevents shipping a SPEC built on a stale memory of an external API — the
  class of error that costs a full FE/BE rebuild cycle on the 8GB box to discover.

## Quick reference

| Tool | Use it for | Don't |
|---|---|---|
| TaskCreate / TaskList | 3+ step jobs; context-break resume | single chores; replacing the durable board |
| `/loop` | recurring board / PR sweeps; read-mostly passes | parallel rebuilds; unattended spend / destructive ops |
| `/deep-research` + WebSearch / WebFetch | grounding SPECs in current Razorpay / GIS / Angular docs | leaking secrets / infra detail into queries |
