# Feature Board — Data Lead

**Lead agent:** `meesell-data-engineer`
**Domain:** data
**Last updated:** 2026-06-16 (category-seeding architecture doc authored)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| category-seeding | plan/category-seeding-architecture | IN REVIEW | — | 2026-06-16 | founder — ratify DRAFT + §9 Q1–Q3 | Architecture doc `docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md` (DRAFT). Formalises founder-approved 5-layer direction from discussion #239 (root cause: complete seeder `scripts/seed_all.py` exists but never run locally → categories table 0 rows → visual gate blocked). PR open, left for founder. NOT yet started (no `make seed`, no K8s Job, no seed run). |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| — | — | — | — | No recent merges. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| infra | category-seeding | Post-migrate K8s Job (alembic upgrade head → seed_all.py) for dev/staging, per §2 ④ / §8 | — | PENDING (opens only if founder selects §9 Q1 dev/staging scope) |

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
