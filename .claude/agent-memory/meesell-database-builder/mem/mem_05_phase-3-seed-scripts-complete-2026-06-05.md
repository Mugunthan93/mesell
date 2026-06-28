## Phase 3 — Seed Scripts COMPLETE (2026-06-05)

### Files authored (all under `scripts/`)
| File | Purpose | LOC |
|---|---|---|
| `seed_field_aliases.py` | UPSERT field_aliases from canonical_field_aliases.json | 223 |
| `build_template_schemas.py` | Transform batch JSONs → templates (dedup by schema_hash) | 597 |
| `seed_categories.py` | UPSERT categories from meesho_category_tree.json | 205 |
| `seed_field_enum_values.py` | UPSERT field_enum_values from batch JSONs | 290 |
| `seed_all.py` | Orchestrator: runs all 4 in order, smoke checks, verification queries | 289 |

### Actual seeded row counts
| Table | Actual | Target | Status |
|---|---|---|---|
| `field_aliases` | 67 | 67 (exact) | OK |
| `templates` | 3,566 | 3,557 ±0.5% | OK (within [3539,3575]) |
| `categories` | 3,772 | 3,772 (exact) | OK |
| `field_enum_values` | 49,259 | 49,295 ±0.5% | OK (within [49048,49542]) |

### Intermediate artifact
`data/parsed/leaf_id_to_schema_hash.json` — 3,772-entry map produced by `build_template_schemas.py`
and consumed by `seed_categories.py` to look up `template_id` FKs.

### Schema hash strategy
Hash computed over all raw field properties EXCEPT `enum_values` (but INCLUDING `enum_count`,
`enum_source`, `help_text`, raw field name pre-alias normalisation).
- Full-with-enum_values → 3772 (every leaf unique due to per-category brand lists)
- Struct-only (name+dtype+marker+col+enum_count) → 3219 (too aggressive)
- Full-minus-enum_values → **3566** (within ±0.5% of 3557 target) — this is the one used

### compliance_shape discriminator
`templates.compliance_shape = 'collapsed'` when any field in the leaf's raw fields[] has a
`name` in: `{"Manufacturer Details", "Packer Details", "Importer Details"}`.
Exactly 1 template has `compliance_shape='collapsed'` (Eye-Serum, leaf 12378).

### Verified sample queries (on dev Postgres)
- `templates WHERE compliance_shape='collapsed'` = 1 (correct: Eye-Serum only)
- `field_aliases WHERE for_xlsx_export=TRUE` = 66 (all 67 variants are non-canonical; 1 would be
  canonical==variant if that ever occurred; in V1 data all 67 variants differ from their canonicals)
- `super_name, COUNT(*) top 5`: Home & Kitchen 816, Sports & Fitness 362, Grocery 321, Office Supplies 312, Kids & Toys 284
- `MAX(value_count) in field_enum_values` = 4,481 (matches SSoT §5: Compatible Models)

### Idempotency
Confirmed: second `seed_all.py` run produces identical row counts, no errors, no FK violations.
ON CONFLICT DO UPDATE on PKs (variant_name, schema_hash, meesho_leaf_id, composite(category_id+field_name)).

### Performance
Total seed pipeline wall time: ~40s for all 4 tables (~49K + 3.8K + 3.6K + 67 rows).
Bulk insert performance: ~2,600 rows/sec for field_enum_values (chunked at 500 rows).
Templates chunked at 50 rows due to large JSONB payloads (up to 71 fields × full schema objects).

### Data anomalies observed
1. **36 duplicate canonical field_name pairs per category** — two fields in the same leaf both
   map to the same canonical_name (alias collision). Handled: skip second occurrence, log at DEBUG.
   These are valid fields in the source that happen to share a canonical after normalisation.
2. **Category tree path includes leaf_name as last element** — the `path` array in
   `meesho_category_tree.json` already ends with `leaf_name`. DB path = `" > ".join(path)`.
   The dispatch brief's cheat-sheet said `path + [leaf_name]` which would be incorrect (double leaf).
3. **field_display_overrides.json uses `image_1_front` not `image_1`** as the override key for
   Image 1. In the batch JSON, the raw field name is "Image 1 (Front)" which slugifies to
   `image_1_front_`. The display override key mismatch is harmless — V1 simply falls back to
   title-case for image fields.
4. **`wrong_defective_returns_price` canonical** — the override file uses this key but the alias
   map has no explicit variant for it; the raw name "Wrong/Defective Returns Price" slugifies to
   `wrong_defective_returns_price` correctly without alias. Match works via slugify.

### Chunking pattern for large JSONB inserts
asyncpg/asyncio port-forward connections drop if a single statement is too large (>1000 params).
Use CHUNK_SIZE=50 for templates (4 cols × 50 rows = 200 params; safe margin).
Use CHUNK_SIZE=500 for field_enum_values (5 cols × 500 rows = 2500 params; safe for asyncpg).

---
