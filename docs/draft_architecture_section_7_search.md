> **STATUS: INTEGRATED** into docs/MVP_ARCHITECTURE.md (2026-06-04 evening). This file is archival only. See the canonical version in MVP_ARCHITECTURE.md.

# Section 7 — Search & Indexing

**Status:** Draft — produced by `postgresql-agent` from MVP_ARCHITECTURE.md + FULL_CORPUS_ANALYSIS.md.
**Scope:** Category browse and search for 3,772 Meesho leaf nodes on PostgreSQL 16 (self-hosted Supabase image, K3s).

---

## 7.1 Two Search Paths

MeeSell exposes category selection through two parallel flows that share the same `categories` table but use entirely different execution paths:

| Path | Trigger | Backend entry point |
|---|---|---|
| **Smart Picker** (§5.1) | Seller enters a product description; Gemini suggests top-5 leaves with confidence | `GET /api/v1/categories/suggest?q=<desc>` |
| **Manual Browse** (this section) | AI confidence < 70%, AI timeout, or seller prefers to navigate the tree | `GET /api/v1/categories/browse?q=&super_id=&limit=&offset=` |

The two paths are independent. Smart Picker owns the Gemini embedding + compressed-tree prompt chain. Manual Browse owns the trigram index queries defined in this section.

---

## 7.2 Manual Browse — Query Types

Manual Browse handles three overlapping query patterns against `categories`:

1. **Prefix match** — seller types "kurti"; returns leaves whose `leaf_name` begins with or closely matches that prefix. Tolerates one transposition ("kurtee", "kurti").
2. **Substring / path search** — seller types "ethnic"; matches anywhere in the full `path` column (e.g. "Women Fashion > Ethnic Wear > Kurtis"). Enables mid-tree discovery without knowing the exact leaf name.
3. **Hierarchical drilldown** — seller browses top-level super-categories (`super_name`), then narrows to leaves within a chosen `super_id`. No text query required; uses `super_id` filter alone.

All three patterns are served by the single `/browse` endpoint using optional parameters.

---

## 7.3 PostgreSQL FTS vs pg_trgm — Recommendation: pg_trgm

**Decision: use `pg_trgm` (trigram similarity), not `tsvector` full-text search.**

Reasoning:

- **Category names are short tokens, not documents.** FTS (`tsvector`/`tsquery`) is optimised for free-text documents where stemming, stop-word removal, and ranking by term frequency add value. A leaf name like "Sarees" or a path segment like "Ethnic Wear" produces no useful lexemes after stemming and no meaningful tf-idf signal.
- **Trigram handles spelling variation without configuration.** Meesho source data contains drift ("Primiary", "Seconadry" are present in templates). Sellers typing on mobile keyboards make similar errors. `pg_trgm` similarity matching catches these without maintaining a synonym dictionary.
- **Prefix and substring queries map directly to GIN trigram operators.** `ILIKE '%kurti%'` accelerates via a GIN trigram index with zero extra application code. FTS requires `plainto_tsquery` + lexeme normalisation for the same coverage and still cannot match mid-string substrings without `pg_trgm` anyway.
- **3,772 rows is a small working set.** The performance ceiling of trigram GIN on this cardinality is well inside the 200 ms budget even on shared K3s resources.

FTS remains appropriate for long-text matching (product descriptions, AI prompt inputs) but is the wrong tool for this 3-column category browse.

---

## 7.4 Index DDL

Enable the extension once (idempotent migration step):

```sql
-- Migration: 0007_category_search_indexes.sql
-- Run with: alembic upgrade head
-- Concurrent creation avoids locking categories for seeding

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Primary browse index: full path string ("Women Fashion > Ethnic Wear > Sarees")
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_path_trgm
  ON categories
  USING GIN (path gin_trgm_ops);

-- Leaf-name index: prefix + fuzzy match on the terminal category name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_leaf_name_trgm
  ON categories
  USING GIN (leaf_name gin_trgm_ops);

-- Super-name index: top-level drilldown (e.g. "Women Fashion", "Home & Kitchen")
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_super_name_trgm
  ON categories
  USING GIN (super_name gin_trgm_ops);

-- B-tree on super_id retained from §2.3 DDL — drives filter-only drilldown
-- CREATE INDEX idx_categories_super ON categories(super_id);  -- already exists per §2.3
```

All three GIN indexes are built `CONCURRENTLY` so the table remains readable during initial seed and during quarterly refreshes. The existing B-tree on `super_id` (defined in §2.3) handles the filter-only drilldown case without a trigram scan.

---

## 7.5 Query Performance Budget

| Operation | Target P95 | Notes |
|---|---|---|
| Prefix / fuzzy leaf name match | ≤ 100 ms | GIN trigram on `leaf_name`; 3,772 rows, small index |
| Full path substring search | ≤ 150 ms | GIN trigram on `path`; path strings up to ~80 chars |
| Super-category drilldown (filter only) | ≤ 50 ms | B-tree `super_id` index; no text scan |
| Combined query (q + super_id filter) | ≤ 200 ms | GIN + B-tree bitmap AND; PostgreSQL 16 planner handles this well |

At 3,772 rows the entire `categories` table fits comfortably in PostgreSQL's shared_buffers (default 128 MB). After the first query the working set is hot in buffer cache, keeping subsequent queries under 10 ms in practice. The 200 ms budget is the contract ceiling, not the expected steady-state.

---

## 7.6 Ranking Strategy

Results are ordered by a two-factor score computed in SQL:

```sql
SELECT
  id,
  meesho_leaf_id,
  leaf_name,
  path,
  super_name,
  -- Factor 1: trigram similarity to query (0.0–1.0)
  GREATEST(
    similarity(leaf_name, :q),
    similarity(path,      :q)
  ) AS match_score,
  -- Factor 2: popularity weight (uniform 1.0 for V1; replaced by traffic data in V1.5)
  1.0 AS popularity_weight
FROM categories
WHERE
  (path      % :q OR leaf_name % :q)  -- GIN trigram shortlist
  AND (:super_id IS NULL OR super_id = :super_id)
ORDER BY (match_score * popularity_weight) DESC
LIMIT :limit OFFSET :offset;
```

**V1 popularity weight is uniform (1.0).** Seasonal / category traffic data is not available at launch. When Meesho quarterly refresh data includes view or GMV signals, the `categories` table gains a `popularity_score NUMERIC(6,4) DEFAULT 1.0` column and the weight becomes data-driven without changing the query shape.

The `%` operator (trigram similarity threshold) uses PostgreSQL's default `pg_trgm.similarity_threshold = 0.3`, which is appropriate for short category-name tokens. Tune downward (e.g. 0.2) if recall is insufficient during acceptance testing.

---

## 7.7 API Endpoint Shape

```
GET /api/v1/categories/browse
    ?q=<text>          — optional; trigram search against leaf_name + path
    &super_id=<id>     — optional; filter to one super-category (drilldown)
    &limit=<int>       — default 20, max 50
    &offset=<int>      — default 0

Response 200 OK:
{
  "items": [
    {
      "id": "uuid",
      "meesho_leaf_id": "10003",
      "leaf_name": "Sarees",
      "path": "Women Fashion > Ethnic Wear > Sarees & Petticoats > Sarees",
      "super_id": "11",
      "super_name": "Women Fashion",
      "match_score": 0.82
    }
  ],
  "total": 47,
  "limit": 20,
  "offset": 0,
  "q": "saree",
  "super_id": null
}
```

When `q` is absent and `super_id` is absent, the endpoint returns all 3,772 leaves ordered by `super_name`, `path` — the full tree for initial render. The frontend Smart Picker component pre-fills `q` with the original seller description when triggering the fallback redirect.

---

## 7.8 Seed and Refresh

**Initial seed** (first deploy):
1. Alembic migration `0007` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` and all three `CREATE INDEX CONCURRENTLY` statements.
2. `meesho_categories.json` and `meesho_category_tree.json` (already in `backend/app/data/`) are loaded via the seeding script defined in §2.6 of MVP_ARCHITECTURE.md.
3. GIN indexes are built automatically after row insertion completes.

**Quarterly Meesho refresh** (new XLSX batch from `meesell-xlsx-parser`):
1. New rows are inserted into `categories` using `INSERT ... ON CONFLICT (meesho_leaf_id) DO UPDATE`.
2. GIN indexes update incrementally on each row write — no manual `REINDEX` required for normal refreshes.
3. If a full rebuild is ever needed (e.g. after a bulk schema change), run:
   ```sql
   REINDEX INDEX CONCURRENTLY idx_categories_path_trgm;
   REINDEX INDEX CONCURRENTLY idx_categories_leaf_name_trgm;
   REINDEX INDEX CONCURRENTLY idx_categories_super_name_trgm;
   ```
   `CONCURRENTLY` keeps the table readable throughout. This is safe on PostgreSQL 16 for both `CREATE` and `REINDEX`.

---

## 7.9 Smart Picker Fallback Handoff

When the Smart Picker (`GET /api/v1/categories/suggest`) returns a low-confidence or timed-out result, the frontend automatically redirects to Manual Browse:

**Trigger conditions (either):**
- All returned suggestions have `confidence < 0.70`
- The `/suggest` request exceeds 8 s (Gemini Flash P95 is ~3 s; 8 s is the hard timeout)

**Handoff mechanism:**
1. Frontend Angular service detects the trigger condition in the `suggest` response handler.
2. Router navigates to `/catalog/create/browse` with the original description pre-filled as the `q` query parameter.
3. The `/browse` endpoint runs immediately with the seller's description as the search string — the seller sees pre-filtered results without re-typing.
4. If the seller selects a leaf from Browse, the catalog creation flow resumes identically to a Smart Picker acceptance.

This keeps the handoff invisible to the seller: the description they typed continues driving the search, just through the trigram path instead of the Gemini path.
