# Category Seeding — Discussion Document

**STATUS: DRAFT — for founder discussion (not a locked plan).**

| Field | Value |
|---|---|
| Author | `meesell-data-engineer` (Data Lead) |
| Session | `mesell-category-seeding-data-session-1` |
| Date | 2026-06-16 |
| Branch | `plan/category-seeding-discussion` (off `origin/develop`) |
| Purpose | Collect every category-seeding-relevant document + the current code/data state into one surface so the founder can rule on how to seed the `categories` table. |
| Scope | Discussion only. **No code, no DB writes, no seeding** performed by this doc. |
| Trigger | Local-host-monitoring session (2026-06-16) verified the visual gate is blocked because the local dev `categories` table has 0 rows. |

> This document is the founder's explicit ask: *collect all the relevant documents and add them*, inventory the current state, analyse the gap, and lay out seeding options for discussion. It does **not** start work. §7 marks the execution shape as NOT yet started.

---

## §1 Purpose + the blocker

### 1.1 Symptom (verified)
- The local dev `categories` table = **0 rows**.
- `GET /api/v1/categories/suggest` returns **HTTP 200** but an **EMPTY** suggestion set (this is correct, contracted behaviour — see §2.6).
- `GET /api/v1/categories/browse` (the pg_trgm search surface) has nothing to match against → empty.
- Backend startup log: `prewarm_top_categories: 0 schema entries warmed`.
- Net effect: there is **no category to pick** → catalog creation and the visual gate are **BLOCKED**.

### 1.2 Verified root cause
This is a **DATA gap, not a code bug.** The smart-picker pipeline behaves exactly as designed when the table is empty:
- `prewarm_top_categories()` (`backend/app/core/cache.py:152`) calls `category_service.get_category_tree(db)`, which reads the `categories` table. With 0 rows it warms 0 schemas — hence the log line.
- `/suggest` correctly returns `200` with `suggestions=[]` + `fallback_offered=True` (graceful fallback per `§9.B.1`), because there is nothing in the table for Layer-2 existence validation to confirm.
- `/browse` correctly returns nothing — the pg_trgm GIN indexes exist (migration `a1b2c3d4e5f6`) but index empty data.

The **derived data exists on disk** and a **complete seeder exists in the repo** (`scripts/seed_all.py` + 3 sub-seeders + `build_template_schemas.py`). **The seeder has simply never been run against the local dev database.** A fresh local DB receives the DDL (`make migrate` → Alembic `upgrade head`) but receives **no rows** because there is no `seed` step wired into local dev setup.

### 1.3 Why it gates the visual gate
The visual gate depends on the full chain: pick a category → create catalog → render the per-category wizard from `categories` → `templates` → `field_enum_values`. With `categories` empty, the chain breaks at step 1. No amount of frontend/AI work unblocks it — only seeded reference data does.

---

## §2 COLLECTED SOURCE DOCUMENTS

One subsection per document read, each with the category-seeding-relevant content distilled.

### §2.1 `docs/MEESHO_CATEGORY_INTELLIGENCE.md` (SSoT — LOCKED, 424 lines)
Path: [`docs/MEESHO_CATEGORY_INTELLIGENCE.md`](../../MEESHO_CATEGORY_INTELLIGENCE.md)
- The single source of truth for the corpus. §1 fixes the governing scale numbers: **3,772 leaf categories**, 30 super-categories, 234 categories, 1,046 sub-categories.
- §2: 28 practical universals; §5: **291 Brand-pattern fields** (same field name, different enum source per category) → stored in `field_enum_values` keyed by `(category_id, field_name)`.
- **Schema-by-template** strategy: 3,557 distinct templates serve 3,772 leaves (5.7% dedup). A `categories` row is a thin leaf pointer; the heavy attribute schema lives in `templates`. **This is why seeding `categories` requires `templates` to be seeded first.**
- LOCKED — amendments require founder escalation per `MASTER_PLAN §7.3`. The seeding plan does NOT amend it.

### §2.2 `docs/V1_FEATURE_SPEC.md` — Feature 2 (Smart Category Picker) + §4 data model
Path: [`docs/V1_FEATURE_SPEC.md`](../../V1_FEATURE_SPEC.md)
- Feature 2 flow (lines 88–125): description → `/api/v1/categories/suggest` → Gemini ranks against compressed tree → top categories returned with confidence.
- Line 101: *"Database: `categories` table (**preseeded** from scraped 3,772 leaves)"* — the spec assumes the table is preseeded. That preseed has not happened locally.
- Line 423: the spec's illustrative DDL header `-- categories (preseeded from 3,772-leaf tree)`.
- NOTE — naming drift to flag for the founder: the legacy V1_FEATURE_SPEC text references `categories.attributes_jsonb` and `categories.name` (lines 125, 137). The **actual shipped ORM model has neither** (see §3). Attributes live in `templates` / `field_enum_values`; the leaf name column is `leaf_name`. The seeder targets the real model, not the legacy spec text.

### §2.3 `docs/DATABASE_ARCHITECTURE.md` — `categories` table
Path: [`docs/DATABASE_ARCHITECTURE.md`](../../DATABASE_ARCHITECTURE.md)
- §2.4 is the authoritative live spec for the `categories` table. Row count: **3,772 (exact; seeded from `meesho_category_tree.json`)**.
- Group A "Reference Data (seeded; read-mostly)" lists `categories` 3,772, `templates` 3,566, alongside `field_aliases` and `field_enum_values`.
- Confirms the FK chain: `templates.id ← categories.template_id ON DELETE RESTRICT` (a category always has a template). This dictates seed order.
- Columns: `meesho_leaf_id` (UNIQUE), `super_id`, `super_name`, `path`, `leaf_name`, `template_id` (FK NOT NULL), `commission_pct` (nullable). This matches the ORM exactly (§3).
- Header rule (line 9): *"a stale entry in this file is a bug"* — so DATABASE_ARCHITECTURE.md §2.4 is the column-mapping authority for the seeder.

### §2.4 `docs/MVP_ARCHITECTURE.md` — categories DDL / category intelligence (2,948 lines)
Path: [`docs/MVP_ARCHITECTURE.md`](../../MVP_ARCHITECTURE.md)
- §2.3 is the DDL source the ORM model cites. §2.6 defines the **4-step seed order** that `scripts/seed_all.py` implements verbatim: field_aliases → templates → categories → field_enum_values.
- §6.7 hot-tier cache strategy is what `prewarm_top_categories` implements (warm tree + top-n schemas).
- §7.4 specifies the pg_trgm GIN indexes (the migration `a1b2c3d4e5f6` realises them).
- §10.2 / §4.C: `categories` / `templates` / `field_enum_values` / `field_aliases` are **GLOBAL reference data** (not user-scoped) — the seeder is a one-time global load, not a per-tenant operation.

### §2.5 `docs/PLAYWRIGHT_MCP_REFERENCE.md` — the scraper that produces the tree
Path: [`docs/PLAYWRIGHT_MCP_REFERENCE.md`](../../PLAYWRIGHT_MCP_REFERENCE.md)
- Documents the 6-phase Meesho scraping workflow that produces the category tree. Phase 3B (network interception) is how the tree was captured.
- The committed `meesho_category_tree.json` was sourced via a **direct Meesho API call** (`api:bulkCatalogUpload/fetchCategoryTreeOld`, recorded in the file's `source` field), captured 2026-06-03 — not via the live Playwright scraper.
- **Relevant to seeding:** the tree is already on disk and dated; no scrape is required to seed. A scrape is only the *quarterly refresh* path (Phase 4 onward) and is out of scope for unblocking the visual gate.
- §6.4 hard-stops (403/429/captcha) are a Stop Condition for any future refresh, not for this seed.

### §2.6 `docs/plans/features/smart-picker/FEATURE_PLAN.md` — how `/suggest` consumes categories
Path: [`docs/plans/features/smart-picker/FEATURE_PLAN.md`](../features/smart-picker/FEATURE_PLAN.md)
- Line 59 (load-bearing correction): *"**NO ILIKE fallback inside `/suggest`** — the architecture explicitly contracts an empty-suggestions response plus the flag."* The `/suggest` graceful-fallback is `200 SuggestResponse(suggestions=[], fallback_offered=True)`. The pg_trgm **ILIKE/trigram search lives in `/browse`** (`§9.B.2`), the manual-browse escape hatch — not inside `/suggest`.
- Line 60: per-card display reads `path` + `commission_pct` directly from the `categories` row. **Both must be seeded** for the card to render meaningfully (`commission_pct` is currently seeded as NULL — see §6 open question).
- Lines 102 + 172: re-seeding the Postgres `categories` table is declared a **backend-coordinator** activity; the **data** track hands off the JSON. Conditional scraper dispatch only if a staleness check fails (diff ≥ 1%). For the current local-dev blocker the committed JSON is fresh (2026-06-03) — **no scrape needed**; this is a pure run-the-existing-seeder task.

---

## §3 Current-state inventory

### 3.1 The four data files (real inspection — sizes/counts not guessed)

| File | Path | Size | Top-level structure | Count | Canonical for seeding? |
|---|---|---|---|---|---|
| Category tree | `backend/app/data/meesho_category_tree.json` | **1,695,666 B (~1.7 MB)** | dict: `discovered_at`, `source`, `super_category_count`(30), `category_count`(234), `sub_category_count`(1046), `leaf_count`(3772), `missing_parents`(0), `categories`(list) | **3,772 leaf records** (all `is_leaf: true`); per-record keys: `path`(array), `slug`, `is_leaf`, `leaf_id`, `leaf_name`, `sub_id`, `cat_id`, `super_id`, `min_products`, `max_products` | **YES** — the canonical source for `categories` rows |
| Category stub (nav) | `backend/app/data/meesho_categories.json` | **2,427 B** | dict: 6 invented super-cats (Women/Men/Kids/Home & Kitchen/Beauty & Personal Care/Electronics & Mobile) | 6 keys | **NO** — stale hand-stub (May 27), does not match the real 30 supers. Quality-engine fixture, NOT pipeline output. |
| Category attributes stub | `backend/app/data/category_attributes.json` | **2,776 B** | dict: `_default` + 15 hardcoded named categories (Kurtis, Sarees, …) | 16 keys | **NO** — stale hand-stub (May 27). Return-rate fixture, NOT the 3,772-leaf attribute schema. |
| Shipping slabs | `backend/app/data/meesho_shipping_slabs.json` | **862 B** | dict: `_note`, `slabs`, `additional_500g_rate`, `default_zone`, `gst_on_shipping_percent`, `payment_processing_percent` | n/a | N/A to category seeding (pricing input) |

Supporting parsed artifacts (in `data/parsed/`, gitignored-raw is not; these ARE committed):
- `data/parsed/leaf_id_to_schema_hash.json` — the **leaf_id → schema_hash** map the category seeder uses to resolve `template_id`.
- `data/parsed/batch_01..12_*.json` — per-batch parser output feeding `templates` + `field_enum_values`.
- `data/parsed/canonical_field_aliases.json` — feeds `field_aliases` (67 rows).

### 3.2 The `categories` ORM model (`backend/app/shared/models/category.py`)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, `gen_random_uuid()` | server-generated |
| `meesho_leaf_id` | String(16) | UNIQUE, NOT NULL | Meesho leaf id, e.g. `"10003"` — **the upsert conflict key** |
| `super_id` | String(8) | NOT NULL | super-category id |
| `super_name` | String(64) | NOT NULL | super-category display name |
| `path` | Text | NOT NULL | full breadcrumb, **trigram-indexed** |
| `leaf_name` | String(255) | NOT NULL | terminal name, **trigram-indexed** |
| `template_id` | UUID | NOT NULL, FK → `templates.id` ON DELETE RESTRICT | many-to-one |
| `commission_pct` | Numeric(5,2) | nullable | currently seeded NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, `NOW()` | |

**Key facts the founder should note:**
- There is **NO `parent_id` column** — hierarchy is denormalized into the `path` text column (the tree's `path` array joined by `" > "`).
- There is **NO `attributes_jsonb` column** on `categories` — attributes live in `templates` (via `template_id`) + `field_enum_values`. (The task brief's expected `parent_id` / `attributes_jsonb` columns reflect the legacy V1_FEATURE_SPEC text, not the shipped model.)
- B-tree indexes: `idx_categories_meesho_leaf`, `idx_categories_super`, `idx_categories_template`. GIN trigram indexes: `idx_categories_path_trgm`, `idx_categories_leaf_name_trgm`, `idx_categories_super_name_trgm`.

### 3.3 DDL / migration state

| Migration | Revision | What it does | Status |
|---|---|---|---|
| baseline | `935e55b4852c` | Creates all 13 V1 tables incl. `categories`, `templates`, `field_enum_values`, `field_aliases` (DDL only — **no rows**) | present |
| pg_trgm + GIN | `a1b2c3d4e5f6` (down: `935e55b4852c`) | `CREATE EXTENSION pg_trgm` + 3 GIN trigram indexes on `categories` (CONCURRENTLY via `autocommit_block`) | present; current Alembic head |

`make migrate` runs `alembic upgrade head` → produces empty tables + indexes. **No data migration inserts category rows** (verified: grep for `INSERT INTO categories` across `backend/app`, `backend/alembic`, `backend/scripts` returns nothing).

### 3.4 Does a seeder EXIST or is it MISSING?

**A complete seeder EXISTS** — but it lives at repo-root `scripts/`, not `backend/`, which is why an initial `backend`-scoped grep missed it.

| Script | Role | Idempotency |
|---|---|---|
| `scripts/seed_all.py` | Orchestrator — runs the 4 seeders in dependency order, prints counts, exits non-zero if any count is out of tolerance | re-runnable; tolerances locked inline |
| `scripts/seed_field_aliases.py` | Seeds `field_aliases` (67 rows) from `canonical_field_aliases.json` | upsert |
| `scripts/build_template_schemas.py` | Seeds `templates` (~3,566 rows) from batch JSONs | dedup by `schema_hash` |
| `scripts/seed_categories.py` | Seeds `categories` (3,772 rows) from `meesho_category_tree.json` + `leaf_id_to_schema_hash.json` | `pg_insert(...).on_conflict_do_update(index_elements=["meesho_leaf_id"], ...)` — **idempotent upsert** |
| `scripts/seed_field_enum_values.py` | Seeds `field_enum_values` (~49,259 rows) from batch JSONs | upsert |

Smoke targets in `seed_all.py`: `field_aliases`=67 (exact), `templates`=3557 ±0.5% (actual 3566), `categories`=3772 (exact), `field_enum_values`=49295 ±0.5% (actual 49259). Run command: `PYTHONPATH=backend python scripts/seed_all.py`.

**What is MISSING is not the seeder — it is the WIRING/RUN.** `Makefile` has a `migrate` target (Alembic) but **no `seed` target**. Nothing in local dev setup (`Makefile`, `nightly-localhost-update.sh`, docker-compose) invokes `seed_all.py`. So a fresh local DB is migrated but never seeded.

---

## §4 Gap analysis — exactly why the table is 0 rows

### 4.1 The chain, mapped
```
meesho_category_tree.json (3,772 leaf records on disk)         ← data EXISTS
        │  seed_categories.py maps:
        │     leaf_id        → meesho_leaf_id   (conflict key)
        │     super_id       → super_id
        │     path[0]        → super_name
        │     " > ".join(path) → path
        │     leaf_name      → leaf_name
        │     leaf_id → hash (leaf_id_to_schema_hash.json) → templates.id → template_id
        │     (commission_pct = NULL)
        ▼
categories table  ──────────────────────────────────────────  0 rows  ← THE GAP
        │
        ▼
prewarm_top_categories() reads tree from table → 0 leaves → "0 schema entries warmed"
/suggest → 200 suggestions=[] fallback_offered=true   (correct empty-state behaviour)
/browse  → empty trigram search                       (correct empty-state behaviour)
visual gate → BLOCKED (no category to pick)
```

### 4.2 The missing link (single sentence)
**The derived data and the idempotent seeder both exist; the seeder was never executed against the local dev database, and no local-dev setup step runs it — so the migrated-but-unseeded `categories` table holds 0 rows.**

### 4.3 Secondary facts that matter for any fix
1. **Seed order is mandatory.** `categories.template_id` is `NOT NULL` FK → `templates.id` `ON DELETE RESTRICT`. `categories` cannot be seeded until `templates` is seeded. `field_enum_values` cannot be seeded until `categories` is seeded. `seed_all.py` already enforces this order.
2. **`commission_pct` is seeded NULL.** Per `seed_categories.py` line 137 and DATABASE_ARCHITECTURE §2.4 (nullable). The smart-picker card renders a `commission_pct%` badge (FEATURE_PLAN line 60) and the pricing engine reads `categories.commission_pct` (V1_FEATURE_SPEC line 276). Seeding NULL is spec-valid but means the badge/pricing have no value until commission data is provided — flagged as an open question (§6).
3. **No env/secret needed to seed.** The seeder writes to the configured `DATABASE_URL`; for local dev this is the local Postgres. No production credentials, no GCS, no scrape.

---

## §5 Seeding approach OPTIONS (for discussion)

All three options seed the same data via the same column mapping; they differ in *how the run is triggered and governed*. Idempotency (upsert on `meesho_leaf_id`), canonical source (`meesho_category_tree.json`), and seed order (pg_trgm migration first, then aliases → templates → categories → field_enum_values) are **common to all options**.

### Option A — Standalone idempotent seeder script (run via a Makefile `seed` target) — RECOMMENDED
- **What:** Wire the existing `scripts/seed_all.py` into a new `make seed` target (`PYTHONPATH=backend python scripts/seed_all.py`) and document `make migrate && make seed` as the local-dev bring-up sequence. Optionally chain it after migrate in the local-dev nightly refresh.
- **Pros:** Zero new seeding logic — the seeder already exists, is idempotent, prints counts, and self-checks tolerances. Reversible (just don't run it). Keeps reference-data load OUT of the Alembic chain (data load is not schema). Re-runnable for quarterly refresh. Matches MVP_ARCH §2.6 + the FEATURE_PLAN's "backend lands the seed" division.
- **Cons:** Requires the run step to be remembered / wired; a fresh DB is not auto-seeded by `alembic upgrade head` alone. Mitigated by the Makefile target + doc + (optional) post-migrate hook.

### Option B — Alembic data migration
- **What:** A new Alembic revision (down-rev `a1b2c3d4e5f6`) that bulk-inserts the 3,772 categories (+ templates + enums) inside the migration.
- **Pros:** Auto-runs on every `alembic upgrade head` — fresh DBs self-seed; CI/CD deploy seeds `dev`/`staging` automatically with no extra step.
- **Cons:** Mixes ~53k rows of reference data into the schema-migration chain (large, slow migrations; painful to diff/review). Re-seeding for the quarterly refresh would need *another* migration each quarter — unbounded chain growth. Downgrade must delete rows. **Alembic head divergence between dev/staging from a data migration is a P0 per MASTER_PLAN §3.3.** Generally discouraged for bulk reference data.

### Option C — CLI / make target that also covers `dev`/`staging` deploy
- **What:** Same as A but additionally invoked by the CI/CD post-deploy job (a one-shot Job/initContainer that runs `seed_all.py` after `migrate` on `dev`/`staging`).
- **Pros:** Closes the gap on every environment, not just local. Keeps data load out of Alembic. Cross-lead handoff to infra wires the K8s post-migrate Job.
- **Cons:** Needs infra coordination (a CronJob/Job + idempotent re-run posture). More moving parts than A for the *local* unblock. Best layered on top of A once local is proven.

### Column mapping (common to all options — authoritative per DATABASE_ARCHITECTURE §2.4 + the live ORM)
| `categories` column | Source |
|---|---|
| `id` | server `gen_random_uuid()` (not seeded explicitly) |
| `meesho_leaf_id` | tree `leaf_id` (**upsert conflict key**) |
| `super_id` | tree `super_id` |
| `super_name` | tree `path[0]` |
| `path` | `" > ".join(tree.path)` |
| `leaf_name` | tree `leaf_name` |
| `template_id` | `leaf_id` → `leaf_id_to_schema_hash.json` → `templates.id` |
| `commission_pct` | NULL (V1) — see §6 Q1 |

Expected row count after seed: **3,772 categories (exact)** + 3,566 templates + 67 field_aliases + 49,259 field_enum_values. Prewarm then warms the tree + top-100 schemas; `/suggest` and `/browse` go live.

**Data-lead recommendation: Option A now (unblocks local-dev visual gate immediately with zero new logic and full reversibility), with Option C layered on later for `dev`/`staging` auto-seed via an infra handoff. Option B is not recommended for bulk reference data.**

---

## §6 OPEN QUESTIONS for the founder

1. **`commission_pct` — seed NULL or source real values?** Currently seeded NULL (spec-valid). But the smart-picker card shows a `commission_pct%` badge and the pricing engine reads it. Ship V1 with NULL badges, or source commission data (and from where — is it in the parsed corpus or a separate Meesho commission table)?
2. **Wiring scope — local only, or local + dev/staging now?** Option A unblocks local. Do we also want the infra-wired auto-seed (Option C) for `dev`/`staging` in this same pass, or defer that to a follow-up?
3. **Add a `make seed` target + document `make migrate && make seed`?** Confirm this is the sanctioned local bring-up sequence, and whether it should be appended to the local-dev nightly refresh script.
4. **Refresh cadence ownership.** When the quarterly scrape refreshes `meesho_category_tree.json`, re-running `seed_all.py` (idempotent upsert) re-seeds. Confirm: data lead hands off the refreshed JSON; backend lead runs the re-seed (per FEATURE_PLAN lines 102/172).
5. **Naming drift cleanup (low priority).** V1_FEATURE_SPEC §4 still references `categories.attributes_jsonb` / `categories.name` which do not exist in the shipped model. Do we reconcile that doc text now, or leave it for a separate docs-hygiene pass?

---

## §7 Proposed owners + execution shape (NOT yet started — discussion first)

> **This section is a proposal only. No branch, no PR, no seeding has begun. Work starts only on founder GO.**

Per MASTER_PLAN HYBRID dispatch + the FEATURE_PLAN division (re-seeding `categories` is a backend-coordinator activity; data hands off the JSON):

| Step | Owner | Action |
|---|---|---|
| 0. GO | Founder | Rules on §6 Q1–Q5; picks Option A / C. |
| 1. SPEC | `meesell-data-engineer` (this lead) | Confirms the JSON is fresh (committed tree dated 2026-06-03; staleness check < 1% → no scrape). Hands off the canonical `meesho_category_tree.json` + `leaf_id_to_schema_hash.json` + the column-mapping table (§5) to the backend lead via cross-lead memo. |
| 2. BUILD | `meesell-database-builder` (under `meesell-backend-coordinator`) | Wires `make seed` → `scripts/seed_all.py`; verifies the 4-step idempotent run against local dev; confirms counts (3,772 categories exact); proves prewarm warms > 0 schemas and `/suggest` + `/browse` go live. (Option C: infra handoff for the K8s post-migrate Job.) |
| 3. MERGE-GATE | `meesell-data-engineer` (for the data-domain slice) / `meesell-backend-coordinator` (for the backend slice) | Reviews the PR against the data PR template + coverage report; confirms idempotency (second run = identical counts, no errors). |

**Cross-lead handoffs anticipated:** data → backend (JSON + mapping handoff, seed run); backend → infra (only if Option C — post-migrate Job + bucket/schedule). None opened yet.

---

*End of discussion document. DRAFT — for founder discussion. No code, no DB writes, no seeding performed.*
