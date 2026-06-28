"""CAT-BE-17-GUARD — every seeded category resolves a non-empty schema.

Context
-------
QA Wave-1 E2E finding CAT-E2E-05/06 observed ``GET /categories/{id}/schema``
returning 404s in CI.  The data lead DIAGNOSED this as an environment
seed-state issue — NOT a data gap:

* ``scripts/build_template_schemas.py`` builds ``templates.schema_jsonb``
  for 3,566 deduped templates.
* ``scripts/seed_categories.py`` seeds 3,772 leaf categories, each with a
  valid ``template_id`` FK (the script raises on any FK miss).
* A live seeded DB shows ``categories_with_resolvable_schema = 3772``
  with ``min_fields = 25`` and ``max_fields = 71``.

The 404s therefore arose from running against an UNSEEDED DB (CI schema-only
mode), not from actual data corruption.  This guard test closes the class:
if the DB is seeded and even ONE category cannot resolve a non-empty schema,
the test fails loudly and bisects immediately rather than surfacing as a
mysterious runtime 404.

Guard contract
--------------
For every ``category.id`` row in a PROPERLY SEEDED database:

    category_service.fetch_schema_dto(category_id, db)

MUST return an envelope where ``len(fields) >= 1``.  Any 404
(``CategoryNotFoundError``) or empty ``fields[]`` is a failure.  Zero
failures are expected on a correctly seeded DB.

Seed-conditional skip (per §BE-SEED-1 / CI Gate-4 established pattern)
-----------------------------------------------------------------------
The test HONESTLY SKIPS when the reference seed is absent.  The
``_seed_data_absent`` helper (lifted into the top-level ``conftest.py``
at CI Gate-4 pass-3) is the canonical signal: it checks
``COUNT(field_enum_values) == 0``, which is the pollution-robust gate
(no test fixture ever commits to ``field_enum_values``).

Run scope
---------
``pytest.mark.integration`` — the test hits the DB via the shared ``db``
fixture (NullPool engine + per-test ROLLBACK).  It is NOT marked
``pytest.mark.slow``; on a seeded DB with 3,772 categories the JOINs
through ``categories → templates`` are all indexed (``template_id`` FK)
and the query is a single round-trip per category (capped by the cache
passthrough from ``_disable_category_cache`` in the category conftest).

DO NOT green-wash
-----------------
If the DB is unseeded this test MUST skip — not pass.  A skip is the
honest signal to the coordinator.  A seeded run must produce
"all N categories resolved, 0 failures".
"""

from __future__ import annotations

import logging
from uuid import UUID

import pytest
from sqlalchemy import text

from app.modules.category import service as category_service
from app.modules.category.exceptions import CategoryNotFoundError
# CI Gate-4 pass-3 (§2.3, Class C): seed-presence gate lifted into conftest.
from tests.conftest import _SEED_SKIP_REASON, _seed_data_absent


pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)


async def test_all_seeded_categories_resolve_nonempty_schema(db, use_live_valkey):
    """CAT-BE-17-GUARD: every seeded category resolves a schema with >= 1 field.

    This guard test closes the spurious category-schema-404 class
    (QA Wave-1 CAT-E2E-05/06).  Under-seeding now fails loudly here
    instead of manifesting as a runtime 404.

    Arrange:
        - Honest skip when the reference seed is absent (``field_enum_values == 0``).
        - Fetch ALL category IDs from the ``categories`` table (ordered by id
          for deterministic logging; does NOT materialise all 3,772 rows into
          memory at once — the category_id list is typically < 1 MB of UUIDs).

    Act:
        - Call ``category_service.fetch_schema_dto(category_id, db)`` for each
          category.  This exercises the full JOIN path:
          ``categories → templates ON template_id`` (repository.py L165-202)
          and applies the §5A.C DTO projection so the guard covers BOTH the
          raw envelope and the projected wire shape that the route serves.

    Assert:
        - Zero ``CategoryNotFoundError``s (no 404 on a seeded category).
        - Every envelope has ``len(fields) >= 1`` (no empty schema).
        - Collect ALL failures before asserting so the first run gives a
          complete picture (count + sample of failed IDs).
    """
    # ── Arrange ──────────────────────────────────────────────────────────────
    if await _seed_data_absent(db):
        pytest.skip(
            f"{_SEED_SKIP_REASON}  "
            "(CAT-BE-17-GUARD requires the full 3,772-category seed to be "
            "meaningful; honest skip rather than false-green)"
        )

    result = await db.execute(
        text("SELECT id FROM categories ORDER BY id")
    )
    all_ids: list[UUID] = [
        UUID(str(row[0])) if not isinstance(row[0], UUID) else row[0]
        for row in result.all()
    ]

    category_count = len(all_ids)
    if category_count == 0:
        # categories table is empty; _seed_data_absent already skipped on
        # field_enum_values==0.  Belt-and-suspenders guard.
        pytest.skip(
            "categories table is empty — no categories to resolve; "
            "honest skip (CAT-BE-17-GUARD owed on a seeded run)"
        )

    # ── Act + collect failures ───────────────────────────────────────────────
    failures: list[str] = []

    for category_id in all_ids:
        try:
            envelope = await category_service.fetch_schema_dto(category_id, db=db)
        except CategoryNotFoundError:
            failures.append(
                f"category_id={category_id}: "
                "CategoryNotFoundError (404) — categories→templates JOIN miss "
                "(template_id FK broken or template row missing)"
            )
            continue
        except Exception as exc:  # noqa: BLE001
            failures.append(
                f"category_id={category_id}: unexpected error {type(exc).__name__}: {exc}"
            )
            continue

        fields = envelope.get("fields") or []
        if len(fields) < 1:
            failures.append(
                f"category_id={category_id}: "
                f"schema resolved but fields[] is empty "
                f"(compliance_shape={envelope.get('compliance_shape')!r}, "
                f"template_id join may have returned an empty schema_jsonb)"
            )

    # ── Assert ───────────────────────────────────────────────────────────────
    # Report clean summary at INFO so CI logs are readable on pass.
    if not failures:
        logger.info(
            "CAT-BE-17-GUARD: all %d categories resolved, 0 failures.",
            category_count,
        )

    resolved_count = category_count - len(failures)
    assert len(failures) == 0, (
        f"CAT-BE-17-GUARD: {len(failures)}/{category_count} categories FAILED "
        f"to resolve a non-empty schema "
        f"({resolved_count} resolved cleanly).  "
        f"First 10 failures:\n"
        + "\n".join(failures[:10])
    )
