## Phase 1 — ORM Models COMPLETE (2026-06-05)

### Head revision
Phase 1 is models-only.  No Alembic revision applied yet (Phase 2).
Existing legacy migration `2651e548010e` covers the OLD schema (users, catalogs, skus, images, exports) and has NOT been applied to any shared DB.  Phase 2 baseline migration will replace it.

### Files authored (all in `backend/app/models/`)
| File | Table | LOC |
|---|---|---|
| `__init__.py` | exports all 13 models | 93 |
| `base.py` | re-exports Base from app.database | 10 |
| `user.py` | users | 97 |
| `seller_profile.py` | seller_profile | 136 |
| `template.py` | templates | 124 |
| `category.py` | categories | 112 |
| `field_enum_value.py` | field_enum_values | 95 |
| `field_alias.py` | field_aliases | 61 |
| `catalog.py` | catalogs | 90 |
| `product.py` | products | 146 |
| `product_image.py` | product_images | 102 |
| `pricing_calc.py` | pricing_calcs | 88 |
| `export.py` | exports | 95 |
| `audit_event.py` | audit_events | 99 |
| `product_draft.py` | product_drafts | 89 |

`database.py` was already correct (async engine, NullPool Celery variant, get_db dependency, settings.DATABASE_URL). No changes made.

### 4 schema deltas applied (pre-approved by coordinator)

1. **`seller_profile` — 3 collapsed columns DROPPED** (`manufacturer_details`, `packer_details`, `importer_details`).
   Only the 9 standard fields are stored.  Export Adapter concatenates at XLSX time.
   Source: §12.6 final ruling (overrides §2.2 DDL).

2. **`templates.compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard'`** added.
   CHECK constraint: `IN ('standard', 'collapsed')`.
   Source: §5.5.13 + §12.6.

3. **`field_enum_values.enum_entries JSONB`** (richer structure) instead of `enum_values JSONB`.
   Shape: `[{"canonical": "...", "meesho": "...", "labels": {"en": "..."}}]`.
   Source: §5.6.4.

4. **`field_aliases.for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE`** added.
   Source: §12.2 + MEESHO_CATEGORY_INTELLIGENCE §6.

### SQLAlchemy 2.0 conventions locked in
- Typed style: `Mapped[T] = mapped_column(...)` throughout
- `from __future__ import annotations` + `TYPE_CHECKING` guards for all cross-model forward refs
- String-based `relationship("ClassName", ...)` — resolved by mapper at first access
- Import order in `__init__.py` follows FK dependency chain (topological)
- `server_default=text("gen_random_uuid()")` for all UUID PKs — requires pgcrypto (confirm in Phase 2 migration)
- `DateTime(timezone=True)` → `TIMESTAMP(timezone=True)` from `sqlalchemy.dialects.postgresql` — used consistently
- `JSONB` from `sqlalchemy.dialects.postgresql` throughout
- `ARRAY(String)` for `seller_profile.active_super_categories`
- `Computed("order_idx = 1", persisted=True)` for `product_images.is_front` GENERATED ALWAYS AS column
- `BigInteger + Identity(always=True)` for `audit_events.id` BIGSERIAL PK
- ForeignKeyConstraint in `__table_args__` for multi-column FKs (seller_profile, product_drafts, field_enum_values)

### Gotchas / learnings
- `Computed(persisted=True)` is the correct SQLAlchemy 2.0 way to map PostgreSQL GENERATED ALWAYS AS ... STORED columns.  Do NOT use server_default or init=False approach.
- `Identity(always=True)` maps to GENERATED ALWAYS AS IDENTITY (SQL standard) which is equivalent to BIGSERIAL but more correct on PG10+.
- `ARRAY(String)` for TEXT[] columns — import from sqlalchemy.dialects.postgresql.
- GIN index for ARRAY column: `Index("name", "col", postgresql_using="gin")` in `__table_args__`.
- Circular import resolution pattern: `from __future__ import annotations` + `TYPE_CHECKING` import guards in each model file.  The `__init__.py` import order resolves everything at mapper-configuration time — no bottom-of-file deferred imports needed.
- `ForeignKeyConstraint` (not `ForeignKey`) needed when the FK col is part of a composite PK (e.g. seller_profile.user_id, product_drafts composite PK).
- `export.py` got a V1 addition: `error_message TEXT` (not in V1_FEATURE_SPEC §4 DDL but required by §5.5.8 Celery task for failure surfacing).  Document this delta if coordinator asks.
- `catalog.py` has `category_id` as nullable FK (ON DELETE SET NULL) — not in original §2.4 DDL, but correct: the category is set when the seller picks a leaf, and the original §2.4 DDL already showed `category_id UUID REFERENCES categories(id)` without NOT NULL, so nullable is consistent.
- `Base` lives in `app.database` (already existed, well-commented).  `app.models.base` re-exports it.  Alembic `env.py` imports `Base` from `app.models` for autogenerate.

### pgcrypto dependency
All UUID PKs use `server_default=text("gen_random_uuid()")`.
pgcrypto extension must be enabled in Phase 2 baseline migration:
`CREATE EXTENSION IF NOT EXISTS pgcrypto;`
Supabase self-hosted image bundles pgcrypto — confirmed safe assumption.

### Pre-existing legacy models (not deleted)
The old model files `image.py` and `sku.py` still exist in `backend/app/models/` but are NOT imported from `__init__.py` and do NOT register tables with Base.  They are dead code.  Phase 2 coordinator task: confirm deletion OK or archive.  Do not delete them in Phase 1 without explicit coordinator instruction.

---
