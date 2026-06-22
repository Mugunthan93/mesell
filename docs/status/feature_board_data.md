# Feature Board — Data Lead

**Lead agent:** `meesell-data-engineer`
**Domain:** data
**Last updated:** 2026-06-22 (session-start sweep: PR #370 reconciled to MERGED; #370 amended → monthly cadence + scraper-cadence design folded in, on `feature/scraper-cadence-reconcile/data` awaiting founder merge)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| category-seeding | feature/category-seeding | RESOLVED (local) — PR #245 open for founder merge | mesell-category-seeding-session-1 | 2026-06-16 | founder — merge PR #245 | Architecture APPROVED (rev 1.0). D1=local-only, D2=real-commission-two-phase, D3=pure-upsert. Wave 1 DONE: `make seed` wired, ran 2× idempotent (categories 3772 / aliases 67 / templates 3566 / enum 49259), seed-script stale-import defect fixed (`app.shared.*`). Wave 3 verified: catalog→wizard chain proven end-to-end on localhost (0 FK orphans, 71-field /schema, seeded enums). Visual-gate blocker RESOLVED. Durable landing on PR #245 merge. |
| scraper-cadence-reconcile (#370 amendment) | feature/scraper-cadence-reconcile/data | IN PROGRESS — committed @ `f518550`, awaiting founder merge to develop | mesell-scraper-cadence-reconcile-data-session-2 | 2026-06-22 | founder — merge branch to develop | DOCS-ONLY amendment of the now-CANONICAL `docs/specs/RETENTION_CATEGORY_MONITOR.md` per founder ruling 2026-06-22: it absorbs today's locked scraper-cadence-and-caching design (same pipeline). Cadence quarterly/90-day → MONTHLY default (TTL=1 month, monthly sweep); measurement plan preserved (tunes cadence; per-super tighter still allowed). Folded in §2.4 demand-count priority (derived over `category_subscription`, no new table) + 1-month unused-category eviction; §2.5 cache(Valkey ~1d)→DB→background-scrape serving + evict-on-update; §3.2 equivalence map (on-choose=catalog-add trigger, "update your catalog entry"=§4 fan-out, diff-gated). §9.2 ToS posture RATIFIED 2026-06-22 (PLAYWRIGHT §6 unchanged). §9.1 billing cadence LEFT OPEN (measurement-gated; PRICING_LOCKED NOT edited). NO LOCKED doc edited. Branch off prior `7d77adc` (agent-spec cadence reconcile, also unmerged). Founder merge lands BOTH commits. Phase-2 LOCKED-doc quarterly sweep (~34 sites) still pending separate LOCKED escalation. |
| category-seeding (commission backfill, Wave 1.5) | feature/category-seeding | CLOSED — won't-fix | mesell-category-seeding-session-1 | 2026-06-16 | — | D2 Phase 2 ABANDONED ON EVIDENCE. Scrape method proven (auth WebKit + Akamai bypass) but NO category rate-card exists — only account-level flat `default_monetization_percent=4.0`. Founder observed commission differs per-product/per-date at upload; internet cross-verification CONFIRMED Meesho commission is DYNAMIC (category × price-slab × time-bound promotions; no stable published rate-card). A static `commission_pct` is wrong by construction. DECISION (founder 2026-06-16): keep `commission_pct=NULL` (Wave-1 shipped state); pricing engine's NULL-tolerant 422 stands. Real commission, if needed, = per-product capture at upload time (pricing-feature item, NOT seeded reference data). Scrape scripts + `category_commissions.json` retained as record only, NOT a seed input. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| retention-monitor-spec | develop @ `bbeb1ec` | 2026-06-22 | #370 | DESIGN SPEC `docs/specs/RETENTION_CATEGORY_MONITOR.md` (V1.x/post-V1, no code). Founder-merged to develop (was stale-marked IN REVIEW on the board; reconciled at this session's start sweep). **Subsequently AMENDED 2026-06-22** → now the SINGLE CANONICAL category-scrape/refresh/monitor pipeline spec, cadence monthly, today's scraper-cadence design folded in — see the active `scraper-cadence-reconcile (#370 amendment)` row (`f518550`, awaiting founder merge). |

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
