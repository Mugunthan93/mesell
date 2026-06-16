# Feature Board — Data Lead

**Lead agent:** `meesell-data-engineer`
**Domain:** data
**Last updated:** 2026-06-16 (category-seeding Wave 0 ratified + Wave 1 local seed landed; Wave 3 verified)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| category-seeding | feature/category-seeding | RESOLVED (local) — PR #245 open for founder merge | mesell-category-seeding-session-1 | 2026-06-16 | founder — merge PR #245 | Architecture APPROVED (rev 1.0). D1=local-only, D2=real-commission-two-phase, D3=pure-upsert. Wave 1 DONE: `make seed` wired, ran 2× idempotent (categories 3772 / aliases 67 / templates 3566 / enum 49259), seed-script stale-import defect fixed (`app.shared.*`). Wave 3 verified: catalog→wizard chain proven end-to-end on localhost (0 FK orphans, 71-field /schema, seeded enums). Visual-gate blocker RESOLVED. Durable landing on PR #245 merge. |
| category-seeding (commission backfill, Wave 1.5) | feature/category-seeding | BLOCKED — founder e-signature | mesell-category-seeding-session-1 | 2026-06-16 | founder action: complete Meesho e-signature (`is_agreement_accepted=false`) | D2 Phase 2: real `commission_pct`. CAPTURE METHOD PROVEN — Run-1 discovery logged in cleanly via the authenticated WebKit context (Akamai passed: `ctx.request`→404 not 403). Endpoint NOT yet found: Meesho gates the referral-fee page behind e-signature acceptance, so the commission component never mounts + no XHR fires. Account exposes only `default_monetization_percent=4.0` (not the category rate-card). Scraper `backend/scripts/meesho_commission_scraper.py` + runbook ready. **QUEUED:** founder completes the "Add Signature" flow in the supplier panel → signals → re-run scraper (harvest) → data-lead reviews leaf-mapping → author `scripts/seed_category_commissions.py` → idempotent backfill. Log: `logs/scraper/commission_2026-06-16_14-27.log` (gitignored). |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| — | — | — | — | No recent merges. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| infra | category-seeding | Post-migrate K8s Job (alembic upgrade head → seed_all.py) for dev/staging, per §2 ④ / §8 | — | DEFERRED — founder ruled D1=LOCAL-ONLY (2026-06-16); handoff does NOT open this pass. Re-opens if/when dev/staging scope is later requested. |

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
