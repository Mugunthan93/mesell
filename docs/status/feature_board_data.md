# Feature Board — Data Lead

**Lead agent:** `meesell-data-engineer`
**Domain:** data
**Last updated:** 2026-06-16 (category-seeding discussion doc)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| category-seeding | (discussion only — no branch) | PENDING | mesell-category-seeding-data-session-1 | 2026-06-16 | founder — review CATEGORY_SEEDING_DISCUSSION.md + rule §6 Q1-Q5 | DRAFT discussion doc at docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md. Root cause: seeder EXISTS (scripts/seed_all.py) but never run locally → categories table 0 rows → visual gate blocked. Recommend Option A (`make seed`). No seeding done; awaits GO. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| — | — | — | — | No recent merges. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| — | — | — | — | No open inter-lead requests. |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/data` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The data group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the active features table until the data group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

PRs from `feature/{name}/data` → `feature/{name}` are reviewed and merged by this lead. Approval requires the PR template at `.github/PULL_REQUEST_TEMPLATE/data.md` to be filled completely — including parser run command + stats, schema-impact decision (no change OR coordinated migration), and either an included or justified-deferred amendment to `MVP_ARCHITECTURE.md` / `MEESHO_CATEGORY_INTELLIGENCE.md`. Gate-1 unit (parser tests) must be green. Gate-5 golden_roundtrip must be green when the PR touches an XLSX surface.
