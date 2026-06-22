# Category Seeding — Architecture

**STATUS: APPROVED — founder-ratified 2026-06-16.** The three §9 decisions are RESOLVED (see §9); execution proceeds per the resolved scope.

| Field | Value |
|---|---|
| Document type | Architecture (formalises the founder-approved direction; not yet executed) |
| Author | `meesell-data-engineer` (Data Lead) |
| Session | `mesell-category-seeding-architecture-data-session-1` |
| Date | 2026-06-16 |
| Branch | `plan/category-seeding-architecture` (off `origin/develop`) |
| Supersedes (in scope) | The OPTIONS section (§5) of `docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md` (PR #239). That doc collected the state and laid out A/B/C; the founder approved a direction; this doc formalises it. |
| Scope | The global reference-data seeding architecture: how ~53k rows across 4 FK-ordered tables get from committed JSON into every environment's database, idempotently, safely, and refresh-ably. **NOT tenant data; NOT a schema-migration doc; NOT a scrape.** |
| Constraint posture | dev-only · no secrets · no production · no DB writes performed by this doc. Architecture only. |

> The founder reviewed `CATEGORY_SEEDING_DISCUSSION.md` (#239) and **APPROVED a specific 5-layer direction**. This document formalises that approved direction. It does **not** re-explore options. The three items in §9 remain **OPEN** for the founder by design — they are scope/policy choices, not architecture choices, and the approved architecture holds under any resolution of them.

---

## §1 Purpose + scope

### 1.1 What this architecture governs
MeeSell's `categories` / `templates` / `field_enum_values` / `field_aliases` tables are **GLOBAL reference data** — not user-scoped, not tenant data (per `MVP_ARCHITECTURE.md §10.2 / §4.C`, `DATABASE_ARCHITECTURE.md` Group A "Reference Data (seeded; read-mostly)"). They are loaded **once per environment** from a **fixed, committed corpus** and **refreshed monthly, usage-driven** (interim; moving to monthly, usage-driven per the locked scraper-cadence design). This document defines the architecture that moves those ~53,000 rows from disk into every environment's Postgres deterministically.

The numbers this architecture must reproduce in every environment (per `seed_all.py` smoke targets + `DATABASE_ARCHITECTURE.md` §2):

| Table | Rows | Tolerance | Natural key |
|---|---|---|---|
| `field_aliases` | 67 | exact | `(meesho_header, canonical_name)` family — see §5 |
| `templates` | 3,566 | ±0.5% (SSoT 3,557) | `schema_hash` |
| `categories` | 3,772 | exact | `meesho_leaf_id` |
| `field_enum_values` | ~49,259 | ±0.5% (SSoT 49,295) | `(category_id, canonical_field_name, value)` |

### 1.2 Why this is an architecture, not a one-off run
The immediate trigger (local dev `categories` = 0 rows → visual gate BLOCKED, per #239 §1) is solved by a single seeder run. But the **same load must hold for**: every fresh local DB, every `dev`/`staging` deploy, and every monthly corpus refresh. A one-off run does not survive a DB reset or a deploy to a new namespace. Therefore the seed is modelled as a **standing, layered, idempotent pipeline**, not a command someone remembers to type.

### 1.3 Non-goals (explicit)
- **No DDL.** Schema (tables, FKs, indexes, the pg_trgm extension) is owned by Alembic. This layer loads rows only.
- **No scrape.** The committed `meesho_category_tree.json` (dated 2026-06-03) is fresh; seeding consumes it directly. A scrape is the monthly-refresh *upstream* path (§7), not part of a seed.
- **No tenant/user data.** This is global reference data, seeded identically in every environment.
- **No production.** V1 environments are `dev` + `staging` only (per `MASTER_PLAN §3`); `prod` is V1.5 and inherits the same Job (§2 ④, §4).

---

## §2 The 5-layer architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ① UPSTREAM SOURCE  (COLD — never in CI or any deployed env)                   │
│    data/meesho_templates/*.xlsx  (3,772 files, GITIGNORED)                    │
│        +  meesell-xlsx-parser  +  meesell-scraper-maintainer (refresh only)   │
│    → source-of-truth on disk; the only place a parse/scrape ever happens.     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 │  parse / refresh  (data-engineer owns)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ② RELEASE ARTIFACT  (COMMITTED — the single deterministic seed input)         │
│    backend/app/data/meesho_category_tree.json   (1.7 MB · 3,772 leaves)       │
│    data/parsed/leaf_id_to_schema_hash.json      (3,772 → 3,566 hashes)        │
│    data/parsed/batch_01..12_*.json              (templates + enum values)     │
│    data/parsed/canonical_field_aliases.json     (67 aliases)                  │
│    → PROVEN COMPLETE + FK-CLEAN: leaf sets all 3772=3772=3772, 0 FK gaps.     │
│    → every environment consumes THIS, identically. No per-env re-parse.       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 │  read (no network, no .xlsx)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ③ SEED ENGINE  (scripts/seed_all.py — FK-ordered, upsert, count-gated)        │
│    Step 1 field_aliases  → Step 2 templates → Step 3 categories               │
│                                              → Step 4 field_enum_values        │
│    upsert on natural keys · prints counts · exits NON-ZERO on count drift.    │
│    Re-runnable; second run = identical counts, no errors.                     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 │  invoked by …
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ④ ENVIRONMENT WIRING  (PROMOTION of the identical artifact — not re-derive)   │
│    local      :  make migrate && make seed                                    │
│    dev/staging:  post-migrate one-shot K8s Job (alembic upgrade head, THEN    │
│                  seed_all.py) — idempotent, safe to fire every deploy.        │
│    prod (V1.5):  SAME Job, gated.                                             │
│    → INFRA-BUILDER HANDOFF (cross-lead): infra wires the Job + ordering.      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 │  guarded by …
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⑤ INTEGRITY & SAFETY                                                          │
│    • pg_trgm/GIN migration (a1b2c3d4e5f6) MUST precede the seed               │
│    • env/DB guard — seed targets the configured DATABASE_URL only             │
│    • count tolerances are a GATE (non-zero exit = deploy fails)               │
│    • SCHEMA_VERSION_CHANGE alert BLOCKS auto-seed → coordinator review        │
│    • post-seed proof: prewarm warms >0 schemas · /suggest non-empty · /browse │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ① UPSTREAM SOURCE (cold)
- **Inputs:** `data/meesho_templates/*.xlsx` — 3,772 files, **GITIGNORED**, never committed, never present in CI or any deployed pod.
- **Tools:** `meesell-xlsx-parser` (parse) and, for the monthly refresh only, `meesell-scraper-maintainer` (re-capture the tree).
- **Property:** This is the *only* place a parse or scrape ever runs. It is **cold** — it executes on the data-engineer's workstation on the parse/refresh cadence, never on the seed path. A fresh DB is seeded without ever touching layer ①.
- **Owner:** `meesell-data-engineer` (this lead) via the two data specialists.

### ② RELEASE ARTIFACT (committed)
The deterministic, version-controlled output of layer ① — the **single seed input every environment consumes**:

| Artifact | Path | Role | Count |
|---|---|---|---|
| Category tree | `backend/app/data/meesho_category_tree.json` | canonical source for `categories` rows | 3,772 leaves |
| Leaf→hash bridge | `data/parsed/leaf_id_to_schema_hash.json` | resolves `categories.template_id` | 3,772 → 3,566 distinct hashes |
| Batch parser output | `data/parsed/batch_01..12_*.json` | feeds `templates` + `field_enum_values` | 12 files |
| Field aliases | `data/parsed/canonical_field_aliases.json` | feeds `field_aliases` | 67 rows |

**Proven completeness + FK-cleanliness** (verified; do not re-derive): the three leaf sets are identical — `meesho_category_tree.json` leaves = 3,772; `leaf_id_to_schema_hash.json` keys = 3,772 (→ 3,566 templates); category-tree leaf records = 3,772 — **all 3,772 = 3,772 = 3,772, with 0 FK gaps** (every `leaf_id` resolves to a `schema_hash` that resolves to a `templates.id`; `seed_categories.py` raises `RuntimeError` on any unresolved hash/template, and the corpus produces none).

**Why this layer exists:** it **decouples the seed from the gitignored `.xlsx`**. CI, deploy Jobs, and every environment read a committed, reviewable JSON artifact — never the raw corpus. The artifact is the contract; the `.xlsx` is an implementation detail of how the artifact was produced.

### ③ SEED ENGINE
- **Entrypoint:** `scripts/seed_all.py`, run as `PYTHONPATH=backend python scripts/seed_all.py`.
- **FK-ordered, 4 steps:** field_aliases → templates → categories → field_enum_values (the order `templates.id ← categories.template_id` and `categories.id ← field_enum_values.category_id` dictate; see §5).
- **Upsert on natural keys** — re-runnable; a second run produces identical counts and no errors.
- **Count-gated** — each step's row count is checked against a tolerance; `seed_all.py` returns **exit code 1** if any count is out of tolerance (drift = hard failure). This is what makes the engine safe to fire on every deploy: a corrupt artifact or partial load fails the Job loudly instead of silently shipping bad reference data.
- Full step order, natural keys, tolerances, and column mapping → **§5**.

### ④ ENVIRONMENT WIRING (promotion, not re-derivation)
Every environment runs the **identical** layer-② artifact through the **identical** layer-③ engine. Environments differ only in *how the run is triggered*:

| Env | Trigger | Mechanism |
|---|---|---|
| local | manual | `make migrate && make seed` (new `seed` target wraps `seed_all.py`) |
| dev | every deploy to `develop` | post-migrate one-shot K8s Job (or initContainer): `alembic upgrade head` THEN `seed_all.py` |
| staging | every deploy to `staging` | same Job |
| prod (V1.5) | tagged release | same Job, gated |

This is **promotion**: the same reviewed artifact moves up the environment ladder unchanged. No environment re-parses; no environment scrapes; no environment can diverge in its reference data because they all load the same bytes.

**K8s Job design** (per `INFRASTRUCTURE_PLAYBOOK.md` kubectl/namespace conventions — `-n <namespace>`, `kubectl diff` before apply, no secrets in logs):

```yaml
# k8s/<env>/seed-job.yaml  (authored by infra-builder, NOT this doc)
apiVersion: batch/v1
kind: Job
metadata:
  name: reference-data-seed
  namespace: <dev|staging>          # explicit -n; never default
spec:
  backoffLimit: 1                   # idempotent → at most one retry
  ttlSecondsAfterFinished: 600      # auto-clean completed Jobs
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: seed
          image: <api-image>        # same image as the API pod (carries scripts/ + backend/)
          command: ["sh","-c"]
          args:
            - "alembic upgrade head && PYTHONPATH=backend python scripts/seed_all.py"
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef: { name: postgres-credentials, key: database-url }
```

Ordering guarantee: the Job runs **after** the migration brings the schema (incl. the pg_trgm/GIN migration `a1b2c3d4e5f6`) to head, and **before** API traffic depends on seeded rows. Whether seed is a step inside the migrate-Job or a Job that `dependsOn` the migrate-Job is an infra implementation choice — the invariant is **migrate-to-head THEN seed**, both idempotent.

> **CROSS-LEAD HANDOFF — `meesell-infra-builder`.** Layer ④ for `dev`/`staging` (and later `prod`) is an **infra** responsibility: the K8s Job/initContainer manifest, its placement in the deploy sequence (post-migrate), the `backoffLimit`/`ttlSecondsAfterFinished` posture, and the `DATABASE_URL` secret reference. Data hands off the artifact (②) + the engine contract (③, §5). Backend (`meesell-database-builder`) owns the local `make seed` target. This handoff is opened as an "Inter-lead requests open" row on `feature_board_data.md` and memo'd to `.claude/agent-memory/meesell-data-engineer/handoff_seed_k8s_job.md` **when the founder selects the dev/staging scope** (§9 Q1) — not before.

### ⑤ INTEGRITY & SAFETY
Full detail in **§6**. In brief, five guards make the seed safe to run automatically:
1. **pg_trgm/GIN migration MUST precede the seed.** `categories` carries 3 GIN trigram indexes created by migration `a1b2c3d4e5f6`; the seed runs only after `alembic upgrade head`.
2. **Env/DB guard.** The seed writes only to the configured `DATABASE_URL` (local `.env` for local; the namespace's `postgres-credentials` secret for K8s). No cross-environment write is possible.
3. **Count tolerances as a GATE.** `seed_all.py` exit-non-zero on drift fails the Job → a bad load never ships silently.
4. **SCHEMA_VERSION_CHANGE alert BLOCKS auto-seed.** Per `MEESHO_CATEGORY_INTELLIGENCE.md §8`: if a refresh detects a corpus-invariant violation, it raises `SCHEMA_VERSION_CHANGE` and the auto-seed is **blocked until coordinator review**.
5. **Post-seed verification = acceptance proof.** prewarm warms >0 schemas; `/suggest` returns a non-empty set for a real description; `/browse` trigram search returns matches.

---

## §3 Design decisions + rationale

### (a) Schema vs data separation — Alembic owns DDL, the seed layer owns rows
**Decision:** DDL (tables, FKs, indexes, `CREATE EXTENSION pg_trgm`) lives in Alembic migrations; the ~53k reference-data rows are loaded by the seed engine (layer ③), **never inside a migration**.
**Rationale:** **Option B (Alembic data-migration) is REJECTED.** Bulk reference data in the migration chain means: (1) large, un-diffable, slow migrations; (2) every monthly refresh would require *another* migration → unbounded chain growth; (3) downgrades must delete rows; and critically (4) **Alembic head divergence between `dev` and `staging` from a data migration is a P0 per `MASTER_PLAN §3.3`.** Keeping data out of the chain keeps the migration history pure-DDL, fast to review, and refresh-able by re-run rather than re-revision.

### (b) Committed JSON as the release artifact
**Decision:** the seed input is the committed `meesho_category_tree.json` + parsed JSONs (layer ②), not the gitignored `.xlsx` corpus.
**Rationale:** decouples the deterministic seed from the raw upstream. CI and deploy Jobs never need the 3,772 `.xlsx` files (which are gitignored and must never enter git/CI/pods). The artifact is reviewable in a PR; the corpus is not. A parse failure surfaces at parse time (layer ①), not at deploy time.

### (c) Environment promotion of the identical artifact
**Decision:** local, dev, staging (and V1.5 prod) all load the **same** committed artifact through the **same** engine.
**Rationale:** determinism. No per-env re-parse means no per-env drift. "What's in dev" and "what's in staging" are byte-identical reference data by construction, which makes the visual gate, smart-picker recall, and pricing badges reproducible across environments.

### (d) One idempotent entrypoint
**Decision:** a single orchestrator, `seed_all.py`, owns the 4-step FK order, counts, and gating. Local and K8s both call it.
**Rationale:** one place enforces order and tolerances. No environment can run the steps out of order or skip the gate. Idempotent upsert means re-running is always safe — there is no "already seeded?" branching to get wrong.

### (e) Refresh = re-run, not rebuild
**Decision:** a monthly corpus refresh produces a **new committed artifact** (②); seeding it is the **same `seed_all.py` re-run** (upsert reconciles changed rows in place).
**Rationale:** there is no separate "update" path to maintain. The upsert-on-natural-key engine *is* the refresh mechanism. (Open question on prune-vs-pure-upsert for removed leaves → §9 Q3.)

---

## §4 Environment strategy table

Mapped to `MASTER_PLAN §3` (V1 = dev + staging; prod deferred to V1.5).

| Environment | Branch | DB | Seed trigger | Who runs it | Seed input | Notes |
|---|---|---|---|---|---|---|
| local | any working branch | local Postgres (`DATABASE_URL` in `backend/.env`) | manual | developer / `meesell-database-builder` | committed artifact (②) | `make migrate && make seed` is the sanctioned bring-up sequence (§9 Q1 confirms wiring scope) |
| dev | `develop` | `dev` K3s namespace Postgres | every deploy to `develop` | CI/CD → post-migrate K8s Job | committed artifact (②) | idempotent; safe every deploy; `MASTER_PLAN §3.1/§3.3` |
| staging | `staging` | `staging` K3s namespace Postgres | every deploy to `staging` | CI/CD → post-migrate K8s Job | committed artifact (②) | same Job, same artifact; `MASTER_PLAN §3.1/§3.3` |
| prod | `main` | (V1.5) `prod` namespace Postgres | (V1.5) tagged release | (V1.5) CI/CD → same Job, gated | committed artifact (②) | deferred; inherits the identical Job. `MASTER_PLAN §3` reserves the prod slot for V1.5 |

The seed migration-ordering rule maps onto `MASTER_PLAN §3.3`: the seed runs **after** `alembic upgrade head` in every environment (local step 1, dev/staging steps 2–3, prod step 5). Alembic head parity between dev and staging remains a P0 — keeping data out of the migration chain (§3a) protects that parity.

---

## §5 Seed engine contract

The authoritative contract for layer ③ (`scripts/seed_all.py` + the 4 sub-seeders). Column mapping is authoritative per `DATABASE_ARCHITECTURE.md §2.4` and the live ORM (`backend/app/shared/models/category.py`).

### 5.1 The 4 seeders, FK order, natural keys, count gates

| # | Step | Script | Source artifact(s) | Natural (conflict) key | Target count | Tolerance |
|---|---|---|---|---|---|---|
| 1 | field_aliases | `scripts/seed_field_aliases.py` | `canonical_field_aliases.json` | alias identity (`meesho_header` ↔ `canonical_name`) | 67 | exact |
| 2 | templates | `scripts/build_template_schemas.py` | `data/parsed/batch_*.json` | `schema_hash` (sha256 of canonical field array) | 3,557 → 3,566 actual | ±0.5% → `[3539, 3575]` |
| 3 | categories | `scripts/seed_categories.py` | `meesho_category_tree.json` + `leaf_id_to_schema_hash.json` | `meesho_leaf_id` | 3,772 | exact |
| 4 | field_enum_values | `scripts/seed_field_enum_values.py` | `data/parsed/batch_*.json` | `(category_id, canonical_field_name, value)` | 49,295 → 49,259 actual | ±0.5% |

**FK order is mandatory:** `categories.template_id NOT NULL FK → templates.id ON DELETE RESTRICT` ⇒ templates before categories. `field_enum_values.category_id FK → categories.id ON DELETE CASCADE` ⇒ categories before enum values. `seed_all.py` enforces exactly this order and aborts on the first failing step (returns 1).

**Tolerance rationale (locked inline in `seed_all.py`):**
- templates 3,557 → 3,566 (+9): schema groups differing only by `enum_source` / `help_text` — both valid schema distinguishers — produce 9 extra distinct hashes. Within `[3539, 3575]`.
- field_enum_values 49,295 → 49,259 (−36): 36 duplicate `(category_id, canonical_field_name)` pairs (alias collisions) where the second occurrence is intentionally skipped. Within ±0.5%.
- field_aliases (67) and categories (3,772) are **exact** — any drift is a hard failure.

### 5.2 `categories` column mapping (authoritative)

| `categories` column | Type / constraint | Source | Notes |
|---|---|---|---|
| `id` | UUID PK, `gen_random_uuid()` | server-generated | not seeded explicitly |
| `meesho_leaf_id` | VARCHAR(16) UNIQUE NOT NULL | tree `leaf_id` | **upsert conflict key** |
| `super_id` | VARCHAR(8) NOT NULL | tree `super_id` | |
| `super_name` | VARCHAR(64) NOT NULL | tree `path[0]` | first breadcrumb element |
| `path` | TEXT NOT NULL | `" > ".join(tree.path)` | trigram-indexed (browse) |
| `leaf_name` | VARCHAR(255) NOT NULL | tree `leaf_name` | trigram-indexed |
| `template_id` | UUID NOT NULL FK → `templates.id` RESTRICT | `leaf_id` → `leaf_id_to_schema_hash.json` → `templates.schema_hash` → `templates.id` | resolved at seed time from the DB; raises on miss |
| `commission_pct` | NUMERIC(5,2) nullable | NULL (V1) | see §9 Q2 — seed NULL vs source real values |
| `created_at` | TIMESTAMPTZ NOT NULL, `NOW()` | server-generated | |

**Model facts the founder should note** (the shipped ORM differs from legacy `V1_FEATURE_SPEC` text): there is **no `parent_id`** (hierarchy is denormalised into `path`) and **no `attributes_jsonb`** on `categories` (attributes live in `templates` via `template_id` + `field_enum_values`). The seeder targets the real model.

### 5.3 Upsert shape (categories, illustrative — the proven, shipped form)
`seed_categories.py` builds rows then chunks (500/chunk) through:
`pg_insert(Category).values(chunk).on_conflict_do_update(index_elements=["meesho_leaf_id"], set_={super_id, super_name, path, leaf_name, template_id, commission_pct})`.
A second run updates in place to identical values — idempotent. The other three seeders follow the same upsert-on-natural-key pattern against their own conflict keys.

---

## §6 Integrity & safety details

| # | Guard | Mechanism | Failure mode it prevents |
|---|---|---|---|
| 1 | pg_trgm/GIN precedes seed | seed runs only after `alembic upgrade head`; migration `a1b2c3d4e5f6` creates `pg_trgm` + 3 GIN indexes (`idx_categories_path_trgm`, `_leaf_name_trgm`, `_super_name_trgm`) | seeding rows with no trigram indexes → `/browse` cannot search |
| 2 | env/DB guard | seed writes only to the configured `DATABASE_URL` — local `.env` locally, the namespace's `postgres-credentials` secret in K8s; no second target is reachable from the Job | seeding the wrong database (e.g. a prod DB from a dev run) |
| 3 | count tolerances as a GATE | `seed_all.py` checks each step's count against §5.1 tolerances and **returns exit 1 on drift**; the K8s Job fails on non-zero | a partial/corrupt artifact silently shipping incomplete reference data |
| 4 | SCHEMA_VERSION_CHANGE alert | per `MEESHO_CATEGORY_INTELLIGENCE.md §8`: a refresh that detects a corpus-invariant violation (e.g. a new `Recommended Field` marker, image-slot count ≠ 4) raises `SCHEMA_VERSION_CHANGE` and **BLOCKS the auto-seed until coordinator (`meesell-data-engineer`) review** | an upstream schema break propagating into the DB unreviewed |
| 5 | post-seed verification (acceptance proof) | after seed: (a) `prewarm_top_categories()` warms **>0** schemas (log line shows the count, not `0 schema entries warmed`); (b) `GET /api/v1/categories/suggest` returns a **non-empty** suggestion set for a real description; (c) `GET /api/v1/categories/browse` trigram search returns matches | declaring "seeded" without proving the consuming pipeline actually lights up |

The acceptance proof (#5) is the definition of done for any seed run, local or K8s. It is the inverse of the #239 blocker symptom: `0 schemas warmed` + empty `/suggest` + empty `/browse` becomes `>0 warmed` + non-empty `/suggest` + working `/browse`.

---

## §7 Refresh cadence + ownership

**Cadence:** monthly, usage-driven (interim; moving to monthly, usage-driven per the locked scraper-cadence design; manual run acceptable for V1).

**Refresh flow:**
```
scraper-maintainer re-captures tree  ─┐
xlsx-parser re-parses changed leaves ─┤  (layer ① — data-engineer owns)
                                       ▼
new COMMITTED meesho_category_tree.json + parsed JSONs   (layer ② — PR, reviewed)
                                       │  data hands off the JSON (cross-lead → backend)
                                       ▼
re-run seed_all.py (same engine, upsert reconciles changed rows)  (layer ③/④)
                                       │
                                       ▼
SCHEMA_VERSION_CHANGE gate:  violation? → BLOCK, coordinator review
                             clean?      → counts re-gate, post-seed proof
```

**Ownership split (per `smart-picker/FEATURE_PLAN.md` lines 102/172 + `MEESHO_CATEGORY_INTELLIGENCE.md §8`):**
- **`meesell-data-engineer` (data):** owns the refresh (layers ①–②) — dispatches scraper/parser, produces and commits the new artifact, runs the `SCHEMA_VERSION_CHANGE` check, hands off the JSON via cross-lead memo.
- **`meesell-backend-coordinator` / `meesell-database-builder` (backend):** runs the re-seed against the database (the seed run itself is a backend activity).
- **`meesell-infra-builder` (infra):** the K8s Job that re-runs the seed on the next deploy (layer ④).

Refresh is **re-run, not rebuild** (§3e): the upsert-on-natural-key engine reconciles changed rows in place; there is no separate update path.

---

## §8 Ownership + HYBRID 3-step execution

**Status: NOT yet started.** No `make seed` target, no K8s Job, no seed run exists. This doc formalises the approved direction; execution begins only on founder GO.

Per `MASTER_PLAN` HYBRID dispatch + the `FEATURE_PLAN` division (re-seeding `categories` is a backend-coordinator activity; data hands off the JSON):

| Layer | Owner | Role |
|---|---|---|
| ① UPSTREAM + ② RELEASE ARTIFACT | `meesell-data-engineer` (this lead) → `meesell-xlsx-parser` / `meesell-scraper-maintainer` | Confirm artifact freshness (tree dated 2026-06-03; staleness < 1% → no scrape). Hand off `meesho_category_tree.json` + `leaf_id_to_schema_hash.json` + the §5 column mapping to backend via cross-lead memo. |
| ③ SEED ENGINE + ④ local | `meesell-database-builder` (under `meesell-backend-coordinator`) | Wire `make seed` → `scripts/seed_all.py`; run the 4-step idempotent seed against local dev; confirm counts (3,772 categories exact); prove the §6 #5 acceptance proof (prewarm >0, `/suggest` non-empty, `/browse` works); verify idempotency (second run identical). |
| ④ dev/staging (+ V1.5 prod) | `meesell-infra-builder` | Author the post-migrate K8s Job/initContainer (§2 ④ design), place it after `alembic upgrade head` in the deploy sequence, set `backoffLimit`/`ttlSecondsAfterFinished`, reference the namespace `postgres-credentials` secret. |

**HYBRID 3-step (code-heavy construction)** for the build slice:
1. `meesell-data-engineer` (SPEC) — confirm artifact + hand off mapping (this is the data slice; mostly the memo).
2. `meesell-database-builder` (BUILD) — wire `make seed`, run + prove (backend slice). Infra Job is a parallel infra slice if §9 Q1 selects dev/staging scope.
3. `meesell-backend-coordinator` + `meesell-data-engineer` (MERGE-GATE) — backend lead gates the backend/seed PR; data lead gates any data-domain artifact change. Both confirm idempotency (second run = identical counts) and the §6 #5 proof.

**Cross-lead handoffs anticipated:** data → backend (JSON + §5 mapping, seed run); backend → infra (only if §9 Q1 selects dev/staging — the K8s Job). None opened yet (NOT started).

---

## §9 DECISIONS — RESOLVED (founder, 2026-06-16)

All three are **RESOLVED**. The approved architecture holds under each resolution — they were scope/policy choices layered on top of the fixed 5-layer structure. Rulings captured verbatim below; session `mesell-category-seeding-session-1`.

1. **Build scope — RESOLVED: LOCAL-ONLY this pass.**
   Layer ④-local (`make seed`) is wired and run to unblock the local visual gate immediately. Layer ④-envs (the dev/staging post-migrate K8s Job, §2 ④) is **deferred to a follow-up** — the infra handoff does **not** open in this pass. Wave 2 is skipped; no namespace is touched and no spend-ask is raised.

2. **`commission_pct` — SUPERSEDED → FINAL: KEEP NULL; scrape effort CLOSED (won't-fix).**
   > **FINAL RESOLUTION (2026-06-16, founder).** The two-phase scrape approach below was attempted and then **abandoned on evidence.** The Run-1/Run-2 discovery proved the capture *method* works (authenticated WebKit login + Akamai bypass) but found NO category rate-card — only an account-level flat `default_monetization_percent: 4.0`, with the referral-fee program gated and no category-wise table. The founder then observed that **Meesho commission differs per product and per date at catalog-upload time**, and internet cross-verification confirmed it: Meesho commission is **dynamic** — it varies by category × selling-price slab × time-bound promotions, with no stable published rate-card (Meesho markets "0% on most categories", 1–5% on some; sources: novelwebcreation / infobeamsolution / digicommerce). A single static `commission_pct` per category is therefore **wrong by construction.** DECISION: keep `commission_pct = NULL` (the Wave-1 shipped state); **Wave 1.5 is CLOSED won't-fix**; the scrape scripts + `category_commissions.json` are retained only as a record (NOT a seed input). Real commission, if ever needed, becomes a **per-product value captured at catalog-upload time** on the product/pricing record — a pricing-feature design item, NOT seeded category reference data. The pricing engine's NULL-tolerant 422 path stands. *(The superseded two-phase text is kept below for history.)*

   Real commission values are wanted (not permanent NULL). Verified fact (`mesell-category-seeding-session-1`): commission is **absent from all committed repo data** — 0 hits across the 12 parsed batch JSONs, `meesho_category_tree.json`, and `canonical_field_aliases.json`; the gitignored raw `.xlsx` templates likewise carried none (their full-corpus parse produced zero commission content). Real values therefore cannot be seeded from existing data. Resolution = **two-phase**:
   - **Phase 1 (this pass / Wave 1):** seed `categories.commission_pct = NULL` (as `seed_categories.py` already does). This unblocks the visual gate today — commission does not gate the catalog wizard; the pricing engine contracts a NULL-tolerant path (`commission_pct IS NULL` → `Decimal('0.00')` → `CommissionMissingError` 422, per `test_commission_missing.py`).
   - **Phase 2 (Wave 1.5 backfill):** `meesell-scraper-maintainer` captures Meesho's published category commission **rate-card** → `backend/app/data/category_commissions.json` → idempotent backfill re-seed (`scripts/seed_category_commissions.py`, consuming that JSON; NOT a migration — the column exists). The upsert reconciles real values in place with zero re-architecture. **Source = scraped Meesho rate-card** (refresh-path style; robots/rate-limit care per `PLAYWRIGHT_MCP_REFERENCE §6.4`; founder accuracy review before it seeds). This extends layer ②'s artifact set (adds `category_commissions.json`) and the §5.2 mapping (`commission_pct` sourced from the rate-card map, NULL fallback when a leaf is unmatched).

3. **Refresh idempotency posture — RESOLVED: PURE UPSERT.**
   The monthly refresh updates changed rows and inserts new leaves via upsert on natural keys; it does **not** prune leaves that disappear from a new tree (orphan rows remain, blocked from delete by `ON DELETE RESTRICT` if referenced). No prune logic is built. Affects only the refresh path (§7), not the initial seed.

---

## §10 Relationship to existing docs + revision history

### 10.1 Document relationships
| Document | Relationship |
|---|---|
| `docs/MEESHO_CATEGORY_INTELLIGENCE.md` (**LOCKED**) | SSoT for the corpus + the `SCHEMA_VERSION_CHANGE` invariant gate (§8). This architecture **consumes** it (layer ⑤ guard #4) and does **not** amend it. Amendments require founder escalation per `MASTER_PLAN §7.3`. |
| `docs/DATABASE_ARCHITECTURE.md` | Authoritative column mapping for the `categories` table (§2.4). The §5.2 mapping here cites it verbatim; its header rule ("a stale entry is a bug") makes it the column-mapping authority. |
| `docs/plans/repo_management/MASTER_PLAN.md §3` | Environment strategy (dev+staging V1, prod V1.5; §3.3 migration rules incl. the head-parity P0 that grounds the §3a Option-B rejection). The §4 env table maps onto it. |
| `docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md` (#239) | The discussion doc this architecture formalises. This doc **supersedes its §5 OPTIONS** (the founder picked the direction); it carries forward its §3 inventory and §6 open questions (now §9). |
| `docs/INFRASTRUCTURE_PLAYBOOK.md` | K8s conventions (namespace scoping, `kubectl diff` before apply, no secrets in logs) that the layer-④ Job (§2 ④) follows. The Job manifest itself is authored by `meesell-infra-builder`. |
| `docs/plans/features/smart-picker/FEATURE_PLAN.md` | The consumer of seeded `categories` (`/suggest`, `/browse`, card render) and the ownership division (data hands off JSON; backend runs the seed). |
| `scripts/seed_all.py` + `scripts/seed_categories.py` (+ 3 sub-seeders) | The shipped layer-③ engine this doc documents. The doc reflects the code, not the reverse — if the code's tolerances/keys change, this doc is re-synced. |

### 10.2 Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-16 | `meesell-data-engineer` | Initial DRAFT — formalises the founder-approved 5-layer direction from `CATEGORY_SEEDING_DISCUSSION.md` (#239). §9 keeps 3 items OPEN. Awaiting founder ratification. |
| 1.0 | 2026-06-16 | `meesell-data-engineer` | **APPROVED.** Founder ratified (`mesell-category-seeding-session-1`) and resolved all 3 §9 decisions: D1 = local-only this pass (Wave 2/K8s deferred); D2 = real commission values, two-phase (NULL seed now + Wave-1.5 scrape-sourced backfill via `category_commissions.json` + `seed_category_commissions.py`); D3 = pure upsert. Execution (Wave 1) begins. |

---

*End of document. APPROVED — founder-ratified 2026-06-16. Wave 1 (local seed) authorised; commission backfill is Wave 1.5 (scrape-sourced). No DB writes performed by this document.*
