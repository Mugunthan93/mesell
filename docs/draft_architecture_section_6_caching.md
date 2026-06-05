> **STATUS: INTEGRATED** into docs/MVP_ARCHITECTURE.md (2026-06-04 evening). This file is archival only. See the canonical version in MVP_ARCHITECTURE.md.

# Section 6 — Caching Strategy

**Status:** Draft — produced 2026-06-04. Awaiting coordinator review before integration into MVP_ARCHITECTURE.md.
**Philosophy anchors:** M10 + F8 govern what may be cached and at what layer. Any cached payload that contains `meesho_column_header`, `meesho_enum_code`, or `meesho_column_index` is a philosophy violation — those fields must only be materialised inside the Export Adapter, never in a cacheable API response.

---

## 6.1 What Gets Cached

| Cache class | Source table | Why it's hot |
|---|---|---|
| **Template schema** | `templates.schema_jsonb` | 3,557 schemas; every wizard load hits one. Average JSONB size ~8 KB. |
| **Field enum values** | `field_enum_values.enum_entries` | 291 Brand-pattern fields; largest sets have up to 4,481 entries. Served on every dropdown keystroke. |
| **Category tree** | `categories` (all rows, path + super info) | Sent as compressed tree to Gemini for Smart Picker; also the manual browse fallback. Rarely changes. |
| **Seller profile** | `seller_profile` | Read on every `/api/v1/products` POST and during wizard render (compliance step auto-fill). |
| **Category picker suggestion** | `categories/suggest` response | Gemini call costs ~1,500 tokens; identical product descriptions should reuse the result for 24h. |

**Excluded from caching:** `products`, `product_images`, `pricing_calcs`, `exports`. These are user-owned mutable state — per-user, per-session, no shared cache benefit.

---

## 6.2 Cache Tiers

Three tiers compose the caching stack:

```
[Angular PWA / browser]
      │ HTTP Cache-Control + ETag
      ▼
[FastAPI worker — in-memory LRU (per-process)]
      │ miss → Valkey lookup
      ▼
[Valkey DB 3 — shared app cache]
      │ miss → PostgreSQL query
      ▼
[PostgreSQL 16]
```

**Valkey DB assignment (per CLAUDE.md locked convention):**

| DB | Purpose |
|---|---|
| DB 0 | Sessions, OTP, rate limits (existing) |
| DB 1 | Celery broker (existing) |
| DB 2 | Celery result backend (existing) |
| **DB 3** | **Application cache — template schemas, enum values, category tree, seller profiles** |

Connection: `redis://valkey:6379/3` (Valkey uses Redis protocol; library: `redis.asyncio`).

---

## 6.3 TTLs per Cache Class

| Cache class | Valkey TTL | Worker LRU TTL | Browser Cache-Control |
|---|---|---|---|
| Template schema | 24 h | 15 min | `max-age=86400, stale-while-revalidate=3600` |
| Field enum values | 24 h | 15 min | `max-age=86400, stale-while-revalidate=3600` |
| Category tree (full) | 24 h | 30 min | `max-age=86400` |
| Category picker suggestion | 24 h | — | `max-age=86400` |
| Seller profile | 5 min | — | `no-store` (user-specific, sensitive) |

Rationale: templates and enum values are updated only on the quarterly Meesho refresh cycle. A 24-hour TTL is conservative relative to that cycle. Seller profile is personal compliance data and must never be stale longer than 5 minutes — a seller updating their FSSAI number must see it reflected on the next API call.

---

## 6.4 Cache Key Patterns

Schema versioning is embedded in every key so a quarterly refresh invalidates atomically without a cache flush command.

```
# Template schema — version-tagged for atomic quarterly refresh
cache:template:{template_id}:v{schema_version}

# Field enum values — keyed by category + field name
cache:enum:{category_id}:{canonical_field_name}:v{schema_version}

# Category tree (full serialised JSON)
cache:category_tree:v{schema_version}

# Smart Picker suggestion — keyed by SHA-256 of the description
cache:category_suggest:{description_sha256}

# Seller profile — keyed by user_id, no version (TTL-based invalidation)
cache:seller_profile:{user_id}
```

`schema_version` is a short string derived from `templates.parser_version` + the quarterly refresh date stamp, e.g. `"0.2-2026Q1"`. It is stored as a single Valkey key `cache:schema_version` (type: string) and read once at worker startup into a process-level constant.

**Philosophy guardrail (M10 + F8):** template schema cached in Valkey stores the **display + canonical layers only** — `display_label`, `display_help`, `canonical_name`, `primitive`, `marker`, etc. The `meesho_column_header`, `meesho_column_index`, and `enum_codes_map` fields are **stripped before serialisation into cache**. The Export Adapter fetches the full `schema_jsonb` directly from PostgreSQL (or a separate, adapter-internal cache keyed `adapter:template:{template_id}`) so that Meesho wire format is never accessible through the public cache namespace.

---

## 6.5 Invalidation Flow

### 6.5.1 Quarterly Meesho refresh

1. `meesell-xlsx-parser` re-parses all Meesho XLSX files; `scripts/build_template_schemas.py` runs (idempotent).
2. Script increments `schema_version` (e.g. `"0.2-2026Q2"`) and writes it to `cache:schema_version` in Valkey.
3. All old version-tagged keys (`cache:template:*:v0.2-2026Q1`) are now unreachable — they expire naturally within 24 h. No `FLUSHDB` required.
4. New keys are populated lazily on first request after the version bump.
5. Worker in-memory LRU is invalidated on the next request (cache miss triggers a Valkey fetch with new version key).

### 6.5.2 Seller profile PATCH

Any `PATCH /api/v1/seller-profile` or `PATCH /api/v1/seller-profile/compliance/{super_id}` handler calls:

```python
await valkey.delete(f"cache:seller_profile:{user_id}")
```

immediately after committing the database transaction. The 5-minute TTL serves as a safety net; explicit deletion ensures sub-second consistency.

### 6.5.3 No schema hot-patching in V1

If a single template is corrected outside the quarterly cycle (e.g. a critical typo in a help string), the fix is deployed by incrementing `schema_version` for that batch only. This is a deliberate V1 simplification — full refresh is quick enough (<2 min) that selective invalidation is not worth the complexity.

---

## 6.6 HTTP Cache Headers

Responses that serve cacheable data include explicit cache headers. The FastAPI service layer sets them via a `CacheHeaders` helper.

```
# Template schema endpoint
GET /api/v1/categories/{id}/schema
→ Cache-Control: public, max-age=86400, stale-while-revalidate=3600
→ ETag: "{template_id}-{schema_version}"
→ Last-Modified: {templates.parsed_from_xlsx_at}

# Field enum endpoint (large, paginated)
GET /api/v1/categories/{id}/field-enum/{name}
→ Cache-Control: public, max-age=86400, stale-while-revalidate=3600
→ ETag: "{category_id}-{field_name}-{schema_version}"

# Category tree
GET /api/v1/categories
→ Cache-Control: public, max-age=86400
→ ETag: "{schema_version}"

# Seller profile (private, sensitive)
GET /api/v1/seller-profile
→ Cache-Control: no-store
→ (no ETag — stale data is never acceptable here)
```

The browser honours these headers natively. The Angular `HttpClient` respects `ETag` / `If-None-Match` — a 304 Not Modified response avoids parsing 8 KB of JSON on every wizard load. For enum endpoints, the PWA service worker (Angular's `@angular/pwa`) pre-caches the top-100-category enum responses on first load via the `ngsw-config.json` asset strategy.

---

## 6.7 Hot/Cold Tier Strategy

The in-process LRU on FastAPI workers handles the top 100 categories by traffic forecast. This avoids a Valkey round-trip (~0.5–1 ms on the same K3s node) for the most frequent lookups.

```python
# backend/app/cache/lru.py
from functools import lru_cache
from typing import Any

_TEMPLATE_LRU: dict[str, Any] = {}   # populated from Valkey on first miss
_MAX_HOT_TEMPLATES = 100             # covers top-100 categories by traffic

# Worker startup: pre-warm LRU with top-100 categories
# (category IDs ranked by historical traffic or, at launch, by super-category size proxy)
async def prewarm_lru(valkey: Redis, top_category_ids: list[str]) -> None:
    for cat_id in top_category_ids[:_MAX_HOT_TEMPLATES]:
        key = f"cache:template:{cat_id}:v{SCHEMA_VERSION}"
        data = await valkey.get(key)
        if data:
            _TEMPLATE_LRU[cat_id] = json.loads(data)
```

| Data class | Hot tier (worker LRU) | Cold tier (Valkey DB 3) |
|---|---|---|
| Template schemas | Top 100 categories | All 3,557 templates |
| Enum values | Top 100 × top 10 fields = 1,000 entries | All 291 Brand-pattern fields (all categories) |
| Category tree | Full tree (single object, ~150 KB) | Same — Valkey as fallback |
| Seller profile | Not in LRU (user-specific) | Valkey only (5-min TTL) |

The 100-category threshold is a V1 approximation. Traffic instrumentation in V1.5 will replace the static list with a Redis Sorted Set of live request counts.

---

## 6.8 Cache Stampede Protection

When a Valkey cache miss occurs for a hot key (e.g. a popular Brand enum with 3,730 values), concurrent requests must not all race to rebuild from PostgreSQL simultaneously.

**Pattern: single-flight via Valkey `SET NX` lock**

```python
async def get_or_populate(valkey: Redis, key: str, build_fn, ttl: int) -> Any:
    # 1. Try cache hit
    cached = await valkey.get(key)
    if cached:
        return json.loads(cached)

    # 2. Acquire build lock (NX = only first caller wins, PX = 5s expiry)
    lock_key = f"lock:{key}"
    acquired = await valkey.set(lock_key, "1", nx=True, px=5000)

    if acquired:
        # 3. Lock winner: build + populate
        try:
            value = await build_fn()
            await valkey.setex(key, ttl, json.dumps(value))
            return value
        finally:
            await valkey.delete(lock_key)
    else:
        # 4. Lock losers: short-poll until lock releases (max 2s)
        for _ in range(20):
            await asyncio.sleep(0.1)
            cached = await valkey.get(key)
            if cached:
                return json.loads(cached)
        # 5. Fallback: go to PostgreSQL directly if lock holder timed out
        return await build_fn()
```

This keeps concurrent enum fetches at peak load from spawning 50 simultaneous PostgreSQL queries for the same Brand enum. The 5-second lock TTL ensures the lock self-heals if the winning worker crashes mid-build.

In-process LRU pre-warming (§6.7) eliminates stampede risk entirely for the top-100-category keys, since they're populated at worker startup.

---

## 6.9 Estimated Valkey Memory Footprint

| Corpus segment | Count | Avg size | Total (uncompressed) |
|---|---|---|---|
| Template schemas (display+canonical layers only, meesho layer stripped) | 3,557 | ~5 KB | ~17.8 MB |
| Field enum values — small sets (≤100 values) | ~200K values ÷ ~30 avg = ~6,700 keys | ~2 KB | ~13.4 MB |
| Field enum values — large sets (Brand-pattern, up to 4,481 values) | 291 fields × varies | ~50 KB avg | ~14.6 MB |
| Category tree (full compressed JSON) | 1 key | ~150 KB | ~0.2 MB |
| Seller profiles (5-min TTL, active sellers at peak) | 500 concurrent sessions (V1 est.) | ~2 KB | ~1.0 MB |
| Category picker suggestions | Variable (24h TTL) | ~0.5 KB | ~0.5 MB (steady-state) |
| **Estimated total** | | | **~47 MB** |

With Valkey's default overhead (hash table, per-key metadata ~100 bytes/key), add ~20% headroom:

**~57 MB peak working set for application cache (DB 3).**

The K3s Valkey pod is configured with `maxmemory 128mb` (shared across DB 0–3). The ~57 MB app cache sits comfortably below this ceiling alongside the OTP/session and Celery data in DB 0–2, which add at most 10–15 MB at peak. The `maxmemory-policy` should be set to `allkeys-lru` so that under pressure, the least-recently-used cache entries are evicted first — natural for a corpus where top categories dominate traffic.

> Compression note: Most template schemas and enum arrays compress well. If memory pressure becomes an issue, serialising cache values with `zstd` or `msgpack` instead of plain JSON cuts the 47 MB estimate to ~18–22 MB. Defer until measured.
