## Session 3 — GIN trgm ORM sync (2026-06-05)

### Task
Sync `backend/app/models/category.py` with migration `a1b2c3d4e5f6` by declaring the
3 GIN trigram indexes in `Category.__table_args__` so autogenerate no longer emits
false-positive drop_index operations.

### GIN trigram index declaration pattern (canonical)

```python
Index(
    "idx_categories_path_trgm",
    "path",
    postgresql_using="gin",
    postgresql_ops={"path": "gin_trgm_ops"},
),
Index(
    "idx_categories_leaf_name_trgm",
    "leaf_name",
    postgresql_using="gin",
    postgresql_ops={"leaf_name": "gin_trgm_ops"},
),
Index(
    "idx_categories_super_name_trgm",
    "super_name",
    postgresql_using="gin",
    postgresql_ops={"super_name": "gin_trgm_ops"},
),
```

Key: `postgresql_ops` is a dict keyed by column name string (NOT the column object).
`postgresql_using="gin"` is the access method kwarg.

### Drift check result
`alembic revision --autogenerate -m "drift_check_should_be_empty"` produced
`pass` in both `upgrade()` and `downgrade()`. No-op file deleted. Drift is clean.

### Test suite after change
98/98 pass (was reported as 96/96 in prior phases; Session 2 G4 pass added 2 more tests).
All 98 pass with no regression.

### api-routes-builder migration a1b2c3d4e5f6 ORM sync
Migration `a1b2c3d4e5f6` (pg_trgm + 3 GIN indexes on categories) is now fully
ORM-synchronized. Future autogenerate runs will not report these indexes as drift.

---

---
