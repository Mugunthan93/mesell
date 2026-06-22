# Feature Board — Data Lead

**Lead agent:** `meesell-data-engineer`
**Domain:** data
**Last updated:** 2026-06-22 (founder-directed: scraper-cadence-reconcile landed develop @ `9d5f5b4` PR #444; phase-2 LOCKED-doc cadence reconcile landed develop @ `cd81ba0` PR #448 — 29 sites quarterly→monthly across 5 SSoT docs)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| category-seeding | feature/category-seeding | RESOLVED (local) — PR #245 open for founder merge | mesell-category-seeding-session-1 | 2026-06-16 | founder — merge PR #245 | Architecture APPROVED (rev 1.0). D1=local-only, D2=real-commission-two-phase, D3=pure-upsert. Wave 1 DONE: `make seed` wired, ran 2× idempotent (categories 3772 / aliases 67 / templates 3566 / enum 49259), seed-script stale-import defect fixed (`app.shared.*`). Wave 3 verified: catalog→wizard chain proven end-to-end on localhost (0 FK orphans, 71-field /schema, seeded enums). Visual-gate blocker RESOLVED. Durable landing on PR #245 merge. |
| category-seeding (commission backfill, Wave 1.5) | feature/category-seeding | CLOSED — won't-fix | mesell-category-seeding-session-1 | 2026-06-16 | — | D2 Phase 2 ABANDONED ON EVIDENCE. Scrape method proven (auth WebKit + Akamai bypass) but NO category rate-card exists — only account-level flat `default_monetization_percent=4.0`. Founder observed commission differs per-product/per-date at upload; internet cross-verification CONFIRMED Meesho commission is DYNAMIC (category × price-slab × time-bound promotions; no stable published rate-card). A static `commission_pct` is wrong by construction. DECISION (founder 2026-06-16): keep `commission_pct=NULL` (Wave-1 shipped state); pricing engine's NULL-tolerant 422 stands. Real commission, if needed, = per-product capture at upload time (pricing-feature item, NOT seeded reference data). Scrape scripts + `category_commissions.json` retained as record only, NOT a seed input. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| scraper-cadence-locked-reconcile | develop @ `cd81ba0` | 2026-06-22 | #448 | FOUNDER-APPROVED locked-change. Phase-2 reconcile: "quarterly" → "monthly, usage-driven" at the 29 OUR-scrape-cadence sites across 5 LOCKED/SSoT docs (MVP_ARCHITECTURE 13, BACKEND_ARCHITECTURE 9, DATABASE_ARCHITECTURE 3, BUSINESS_STRATEGY 4, MEESELL_AGENT_REGISTRY 3). Per locked scraper-cadence design / #370. 5 "quarter" left deliberately (release-smoke / module-extraction roadmap / Meesho's own change-freq / rejection-rate trend / doc review cadence). No non-cadence content altered. Docs-only, founder-directed develop merge. |
| scraper-cadence-reconcile (#370 amendment) | develop @ `9d5f5b4` | 2026-06-22 | #444 | FOUNDER-DIRECTED docs-only merge. 3 commits: `7d77adc` agent-spec quarterly→monthly reconcile + `f518550` #370 RETENTION_CATEGORY_MONITOR amendment (now SINGLE CANONICAL category-scrape/refresh/monitor pipeline spec; cadence monthly; demand-count derived over `category_subscription` + 1-month eviction + cache→DB serving folded in; §9.2 ToS RATIFIED, §9.1 billing OPEN) + `550d6a5` status. No app code, no derived-JSON, no DDL. |
| retention-monitor-spec | develop @ `bbeb1ec` | 2026-06-22 | #370 | DESIGN SPEC `docs/specs/RETENTION_CATEGORY_MONITOR.md` (V1.x/post-V1, no code). Founder-merged to develop. Subsequently AMENDED via #444 → now the SINGLE CANONICAL category-scrape/refresh/monitor pipeline spec. |

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
