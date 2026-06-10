# Feature Board — AI Lead

**Lead agent:** `meesell-ai-coordinator`
**Domain:** ai
**Last updated:** 2026-06-10 (initial creation)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/ai` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The AI group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the Active features table until the AI group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

Group-PR approval criteria live in the AI PR template at `.github/PULL_REQUEST_TEMPLATE/ai.md`. The lead approves a `feature/{name}/ai` → `feature/{name}` PR only when the template is filled completely — including prompt registry version bump, eval evidence green (smart_picker top-5 recall ≥ 80 %, autofill invalid-enum rate = 0 %, watermark accuracy ≥ 85 %), per-call cost ≤ ₹0.05 documented, LangFuse trace sample link, and guardrail compliance — plus CI gate-1 (unit) green and nightly `ai_eval` green within the last 24 hours.
