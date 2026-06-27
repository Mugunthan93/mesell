## Session 2 Gap Pass — G4+G1 COMPLETE (2026-06-05)

### Revision authored
`a1b2c3d4e5f6` — `backend/alembic/versions/a1b2c3d4e5f6_pg_trgm_and_category_gin.py`
This revision was authored by this agent (database-builder) in Session 2, NOT api-routes-builder
(prior Phase 5 note was in error).

### CONCURRENTLY in Alembic async — working pattern (IMPORTANT)

`op.get_context().autocommit_block()` + `transaction_per_migration=True` in env.py.

Required env.py change (already applied):
```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    transaction_per_migration=True,  # required for autocommit_block() to work correctly
)
```

Migration pattern:
```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")  # inside transaction — OK
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_path_trgm ON categories USING GIN (path gin_trgm_ops)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_leaf_name_trgm ON categories USING GIN (leaf_name gin_trgm_ops)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_super_name_trgm ON categories USING GIN (super_name gin_trgm_ops)")
```

Failed approaches (do NOT retry):
1. `conn.execution_options(isolation_level="AUTOCOMMIT")` — fails if transaction already begun
2. `engine.raw_connection()` + cursor.execute() — asyncpg shim carries transaction; CONCURRENTLY silently no-ops
3. `conn.execute(sa.text("COMMIT"))` before CONCURRENTLY — asyncpg prepare-execute protocol blocks it

### is_advanced wiring — confirmed correct, no code changes needed
ADVANCED_CANONICAL_NAMES = {"group_id"} at line 84 of scripts/build_template_schemas.py (D2-locked).
3566 templates have group_id field with is_advanced=true. 0 templates have product_name as advanced.

### CRITICAL: is_advanced JSONB test query pattern
The LIKE pattern `schema_jsonb::text LIKE '%"canonical_name": "product_name"%' AND '%"is_advanced": true%'`
gives false positives — both strings match anywhere in the JSON blob. Use jsonb_array_elements instead:
```sql
SELECT count(*) FROM templates t
WHERE EXISTS (
    SELECT 1 FROM jsonb_array_elements(t.schema_jsonb -> 'fields') AS f
    WHERE f->>'canonical_name' = 'product_name'
    AND (f->>'is_advanced')::boolean = true
)
```

### Parallel migration chain awareness
Always run `alembic current` before `downgrade -1`. The -1 flag goes one step back from CURRENT head.
If other agents have applied migrations since your revision, -1 undoes their work, not yours.
Full chain as of this session: 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61

### Test suite
42/42 tests pass (was 40/40 after Phase 4; Phase 5 added more; +2 is_advanced tests in Session 2)

---
