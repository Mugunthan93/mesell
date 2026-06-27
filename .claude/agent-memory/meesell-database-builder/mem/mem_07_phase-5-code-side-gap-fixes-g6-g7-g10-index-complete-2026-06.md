## Phase 5 — Code-side Gap Fixes (G6, G7, G10-index) COMPLETE (2026-06-05)

### New head revision
`f31c75438e61` — `backend/alembic/versions/f31c75438e61_add_idx_product_drafts_saved_at.py`
Parent: `a1b2c3d4e5f6` (pg_trgm + category GIN indexes, applied by another agent between Phase 4 and Phase 5).
Applied to dev Postgres.

Note on `a1b2c3d4e5f6`: This revision was authored by database-builder in Session 2 (G4 gap pass).
It adds pg_trgm GIN indexes on categories (idx_categories_leaf_name_trgm, idx_categories_path_trgm,
idx_categories_super_name_trgm). These indexes are NOT declared in the Category ORM model.
`alembic revision --autogenerate` always reports these 3 as "removed" — that is expected drift,
not an error. Do NOT attempt to drop those indexes; they are live and required for the browse endpoint.

### Files created
| File | Purpose | LOC |
|---|---|---|
| `backend/app/i18n/__init__.py` | Package init with docstring explaining the versioning discipline | 16 |
| `backend/app/i18n/step_assignment.py` | STEP_ASSIGNMENT + STEP_ORDER + assign_step() + RULESET_VERSION="v1" | 108 |
| `backend/app/i18n/primitive_classifier.py` | UNIT_KEYWORDS + CURRENCY_PATTERNS + LONG_PATTERNS + classify_primitive() + CLASSIFIER_VERSION="v1" | 116 |
| `backend/tests/test_step_assignment.py` | 23 tests (3 smoke + 15 parametrised regression + 5 edge case) | 120 |
| `backend/tests/test_primitive_classifier.py` | 33 tests (4 smoke + 15 parametrised regression + 14 edge case) | 152 |
| `backend/alembic/versions/f31c75438e61_add_idx_product_drafts_saved_at.py` | G10 migration — idx_product_drafts_saved_at on saved_at | 45 |

### Files modified
- `scripts/build_template_schemas.py`: inline STEP_ASSIGNMENT/STEP_ORDER removed; classify_primitive()
  and assign_step_id() now delegate to i18n modules. Canonical source is backend/app/i18n/.
- `backend/app/models/product_draft.py`: Added Index("idx_product_drafts_saved_at", "saved_at") to
  __table_args__ so future autogenerate stays in sync.

### Test results
- test_step_assignment.py: 23/23 PASS
- test_primitive_classifier.py: 33/33 PASS
- test_database.py (Phase 4 suite): 40/40 PASS (no regression)
- Total: 96/96 tests pass

### Re-seed verification
- alembic current: f31c75438e61 (head)
- product_drafts has idx_product_drafts_saved_at btree (saved_at)
- seed_all.py re-run counts: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259 (identical)
- Spot-check: schema_hash=a315f724... → product_name step_id=basics primitive=text_short (IDENTICAL pre/post)
- CONCLUSION: Refactor is behavior-preserving. No schema_jsonb drift.

### backend/app/i18n/ pattern (for future agents)
- Versioned rule modules under backend/app/i18n/ for any constant/function driving schema_jsonb shape.
- Each module MUST have a *_VERSION constant (start "v1"; bump on any rule change).
- Seed script MUST import from these modules — never define constants inline in scripts/.
- Regression tests MUST pin ~15+ canonical tuples covering all output values.
- Bumping a version = re-seed + confirm row counts + spot-check schema_jsonb intentionally changed.

### Gotcha: autogenerate false positives for GIN trgm indexes
Migration a1b2c3d4e5f6 (database-builder, Session 2) added GIN trgm indexes on categories without
updating the Category ORM model (ORM models are intentionally not updated for indexes added in
post-baseline migrations). Autogenerate will always report idx_categories_*_trgm as "removed" in
future drift checks. When you see these 3 as false positives, discard them — the indexes are real
and correct, just not reflected in the ORM metadata.

---

---
