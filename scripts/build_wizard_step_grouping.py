#!/usr/bin/env python3
"""Build the catalog-wizard step-grouping manifest from the seeded DB.

DETERMINISTIC, READ-ONLY data+doc tool. It reads every template's
``schema_jsonb`` from the seeded ``templates`` table, groups each template's
fields into wizard steps, and emits a machine-readable manifest that the
upcoming multi-step catalog-form wizard consumes so its build hits no
surprises.

What it does NOT do
-------------------
- It NEVER writes to the DB. Only ``SELECT`` statements are issued.
- It does NOT re-seed, re-parse, or touch ``step_assignment.py``,
  ``schema_jsonb``, or any runtime code.
- It is NOT wired into CI: CI has no DB. Run it locally/operator-side after
  ``make seed`` whenever the seeded schema changes (e.g. a quarterly refresh).

Grouping rule (the only rule — kept identical to STEP_GROUPING.md)
------------------------------------------------------------------
1. Group fields by their pre-assigned ``step_id`` (assigned at seed time by
   ``app.i18n.step_assignment.assign_step`` — this script does NOT re-derive
   step assignment, it only reads ``field["step_id"]``).
2. Render only NON-EMPTY steps, in canonical ``STEP_ORDER``.
3. Order fields within a step COMPULSORY-FIRST, then original schema order
   (``meesho_column_index`` ascending, with a stable fallback to the field's
   position in ``schema_jsonb.fields``). This is fully deterministic.

Requirements
------------
- ``DATABASE_URL`` env var pointing at the seeded Postgres (read-only is fine).
  Async URL form (``postgresql+asyncpg://``) is accepted and normalised.
- The master venv (Python 3.12) so ``app.i18n.step_assignment`` imports cleanly:

    set -a; . backend/.env; set +a
    PYTHONPATH=<worktree>/backend <venv>/bin/python \\
        scripts/build_wizard_step_grouping.py

Output
------
- ``docs/plans/catalog-wizard/step_grouping_manifest.json`` (overwritten;
  re-runnable). See module ``OUT_MANIFEST``.

The script logs progress per chunk (``--chunk-size``, default 200 templates).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import asyncpg

# Import the canonical step ordering. This is the ONLY thing pulled from the
# runtime — we read step_id values verbatim from schema_jsonb and only need the
# ordering to render non-empty steps in canonical sequence.
from app.i18n.step_assignment import STEP_ORDER  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("build_wizard_step_grouping")

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_MANIFEST = REPO_ROOT / "docs" / "plans" / "catalog-wizard" / "step_grouping_manifest.json"

# Friendly, seller-facing step labels (plain English — never a generated code).
# Source of truth for labels is this doc/script pair; FE may localise later.
STEP_LABELS: dict[str, str] = {
    "basics": "Product Basics",
    "pricing": "Pricing",
    "inventory": "Inventory & Packaging",
    "sizing": "Size & Fit",
    "materials": "Material & Pattern",
    "food": "Food & Nutrition",
    "tech_specs": "Technical Specs",
    "safety": "Safety & Age",
    "warranty": "Warranty",
    "compliance": "Compliance",
    "photos": "Photos",
    "description": "Description",
    "advanced": "Advanced (optional)",
}

# Drop-down primitives + the rich data_type marker for an enum field.
_DROPDOWN_DATA_TYPE = "dropdown"


def _normalise_dsn(url: str) -> str:
    """Normalise an async SQLAlchemy URL into an asyncpg-friendly DSN."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")


def _derive_enum_resolver(field: dict[str, Any]) -> str | None:
    """Mirror ``category.service._map_field_to_dto`` enum_resolver derivation.

    This is the SAME rule the runtime uses so the manifest matches what the FE
    will actually receive:
      - data_type != "dropdown"                 -> None
      - dropdown WITH inline enum_codes_map      -> "static"
      - dropdown WITHOUT inline map (V1 reality) -> "category" (FE lazy-loads
        the option list via GET field-enum; empty-options risk if unseeded).
    """
    if field.get("data_type") != _DROPDOWN_DATA_TYPE:
        return None
    return "static" if field.get("enum_codes_map") else "category"


def _field_summary(field: dict[str, Any], schema_index: int) -> dict[str, Any]:
    """Project a rich schema field into the manifest's compact field record."""
    label = field.get("display_label")
    name = ""
    if isinstance(label, dict):
        name = str(label.get("en", "") or "")
    canonical = str(field.get("canonical_name", "") or "")
    if not name:
        name = canonical.replace("_", " ").title()
    return {
        "canonical_name": canonical,
        "name": name,
        "marker": field.get("marker", "optional") or "optional",
        "data_type": field.get("data_type", "text") or "text",
        "primitive": field.get("primitive", "text_short") or "text_short",
        "is_advanced": bool(field.get("is_advanced", False)),
        "enum_resolver_derived": _derive_enum_resolver(field),
        "_schema_index": schema_index,  # stripped before emit; kept for sort
    }


def _group_template(schema: dict[str, Any]) -> dict[str, Any]:
    """Apply the grouping rule to one template's schema_jsonb.

    Returns the per-schema manifest record: ordered, non-empty steps with
    compulsory-first field ordering inside each step.
    """
    fields = schema.get("fields") or []

    # Build compact field records, retaining schema order index for the
    # deterministic in-step sort.
    buckets: dict[str, list[dict[str, Any]]] = {}
    for idx, f in enumerate(fields):
        if not isinstance(f, dict):
            continue
        # Original schema order = meesho_column_index when present, else the
        # field's position in the fields[] list (stable, deterministic).
        mci = f.get("meesho_column_index")
        order_key = mci if isinstance(mci, int) else 10_000 + idx
        rec = _field_summary(f, order_key)
        buckets.setdefault(f.get("step_id") or "basics", []).append(rec)

    steps: list[dict[str, Any]] = []
    for step_id in STEP_ORDER:
        recs = buckets.get(step_id)
        if not recs:
            continue  # render only non-empty steps
        # COMPULSORY-FIRST, then schema order. marker rank: compulsory=0 else 1.
        recs.sort(key=lambda r: (0 if r["marker"] == "compulsory" else 1, r["_schema_index"]))
        required = sum(1 for r in recs if r["marker"] == "compulsory")
        for r in recs:
            r.pop("_schema_index", None)
        steps.append(
            {
                "step_id": step_id,
                "label": STEP_LABELS.get(step_id, step_id),
                "field_count": len(recs),
                "required_count": required,
                "fields": recs,
            }
        )

    return {
        "step_ids": [s["step_id"] for s in steps],
        "step_count": len(steps),
        "steps": steps,
    }


async def build(dsn: str, chunk_size: int) -> dict[str, Any]:
    conn = await asyncpg.connect(dsn)
    try:
        n_templates = await conn.fetchval("SELECT count(*) FROM templates")
        n_categories = await conn.fetchval("SELECT count(*) FROM categories")
        n_null_tpl = await conn.fetchval(
            "SELECT count(*) FROM categories WHERE template_id IS NULL"
        )
        log.info(
            "DB: %s templates, %s categories (%s with NULL template_id)",
            n_templates,
            n_categories,
            n_null_tpl,
        )

        template_rows = await conn.fetch("SELECT id::text AS id, schema_jsonb FROM templates")

        schemas: dict[str, dict[str, Any]] = {}
        ungrouped_fields = 0
        step_usage: Counter[str] = Counter()
        stepcount_dist: Counter[int] = Counter()
        max_step = {"field_count": 0, "step_id": None, "schema_key": None}
        all_optional_steps: Counter[str] = Counter()

        total = len(template_rows)
        for start in range(0, total, chunk_size):
            chunk = template_rows[start : start + chunk_size]
            for row in chunk:
                schema = row["schema_jsonb"]
                if isinstance(schema, str):
                    schema = json.loads(schema)
                key = row["id"]
                grouped = _group_template(schema)
                schemas[key] = grouped
                stepcount_dist[grouped["step_count"]] += 1
                for s in grouped["steps"]:
                    step_usage[s["step_id"]] += 1
                    if s["required_count"] == 0:
                        all_optional_steps[s["step_id"]] += 1
                    if s["field_count"] > max_step["field_count"]:
                        max_step = {
                            "field_count": s["field_count"],
                            "step_id": s["step_id"],
                            "schema_key": key,
                        }
                # Defensive: count fields with no step_id (expected 0).
                ungrouped_fields += sum(
                    1
                    for f in (schema.get("fields") or [])
                    if isinstance(f, dict) and not f.get("step_id")
                )
            log.info(
                "processed templates %d-%d / %d",
                start + 1,
                min(start + chunk_size, total),
                total,
            )

        # category_index: every category_id -> its schema key, so all
        # categories (not just distinct templates) are covered.
        cat_rows = await conn.fetch(
            "SELECT id::text AS id, template_id::text AS template_id, "
            "meesho_leaf_id, leaf_name, super_name FROM categories"
        )
        category_index: dict[str, dict[str, Any]] = {}
        for c in cat_rows:
            category_index[c["id"]] = {
                "schema_key": c["template_id"],
                "meesho_leaf_id": c["meesho_leaf_id"],
                "leaf_name": c["leaf_name"],
                "super_name": c["super_name"],
            }

        universal_steps = [s for s in STEP_ORDER if step_usage.get(s, 0) == n_templates]
        conditional_steps = {
            s: step_usage[s]
            for s in STEP_ORDER
            if 0 < step_usage.get(s, 0) < n_templates
        }
        unused_steps = [s for s in STEP_ORDER if step_usage.get(s, 0) == 0]

        manifest = {
            "_meta": {
                "generator": "scripts/build_wizard_step_grouping.py",
                "grouping_rule": (
                    "group fields by step_id; render non-empty steps in "
                    "STEP_ORDER; within a step order compulsory-first then "
                    "schema order (meesho_column_index)"
                ),
                "step_order": STEP_ORDER,
                "step_labels": STEP_LABELS,
                "source": "templates.schema_jsonb (read-only)",
                "ci_wired": False,
            },
            "summary": {
                "category_count": n_categories,
                "template_count": n_templates,
                "categories_with_null_template": n_null_tpl,
                "ungrouped_fields": ungrouped_fields,
                "universal_steps": universal_steps,
                "conditional_steps": conditional_steps,
                "unused_steps": unused_steps,
                "step_usage": {s: step_usage.get(s, 0) for s in STEP_ORDER},
                "all_optional_step_occurrences": dict(all_optional_steps),
                "step_count_distribution": {
                    str(k): stepcount_dist[k] for k in sorted(stepcount_dist)
                },
                "max_fields_in_a_step": max_step,
            },
            "schemas": schemas,
            "category_index": category_index,
        }
        return manifest
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chunk-size", type=int, default=200)
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT_MANIFEST,
        help="manifest output path (default: docs/plans/catalog-wizard/step_grouping_manifest.json)",
    )
    args = ap.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        log.error("DATABASE_URL not set. Source backend/.env first (read-only is fine).")
        return 1
    dsn = _normalise_dsn(url)

    manifest = asyncio.run(build(dsn, args.chunk_size))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    s = manifest["summary"]
    log.info(
        "WROTE %s | %d schemas, %d categories, %d ungrouped fields",
        args.out,
        s["template_count"],
        s["category_count"],
        s["ungrouped_fields"],
    )
    log.info("step-count distribution: %s", s["step_count_distribution"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
