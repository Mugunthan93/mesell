"""Seed script: templates table (canonical transformer per §5.6.5).

Reads all 12 batch JSONs from data/parsed/batch_NN_*.json.
For each unique template schema (deduped by sha256 of canonical field array):
  - Maps raw field names → canonical names via field_aliases
  - Builds the full per-field schema per §5.6.1
  - Computes primitive, step_id, compliance_role, is_advanced, is_hidden
  - Merges display copy from field_display_overrides.json
  - Computes compliance_shape (collapsed only for Eye-Serum leaf 12378)
  - UPSERTs into templates table

Also writes an intermediate JSON:
  data/parsed/leaf_id_to_schema_hash.json
which seed_categories.py reads to look up template_id by leaf_id.

Run:
    PYTHONPATH=backend python scripts/build_template_schemas.py

Requires DATABASE_URL env var (or .env file in backend/).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_ROOT = PROJECT_ROOT / "data" / "parsed"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_ROOT / ".env")
except ImportError:
    pass

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.i18n.primitive_classifier import classify_primitive as _classify_primitive  # noqa: F401
from app.i18n.step_assignment import STEP_ASSIGNMENT, STEP_ORDER, assign_step as _assign_step  # noqa: F401
from app.models.template import Template

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("build_template_schemas")

ALIASES_FILE = DATA_ROOT / "canonical_field_aliases.json"
OVERRIDES_FILE = DATA_ROOT / "field_display_overrides.json"
BATCH_GLOB = "batch_*.json"
LEAF_HASH_MAP_FILE = DATA_ROOT / "leaf_id_to_schema_hash.json"

# Eye-Serum leaf — the only leaf using collapsed compliance shape
EYE_SERUM_LEAF_ID = "12378"

# Collapsed compliance field names that identify the Eye-Serum template
COLLAPSED_FIELD_NAMES = {"Manufacturer Details", "Packer Details", "Importer Details"}

# 9 compliance field canonical names — sets compliance_role
COMPLIANCE_CANONICAL_ROLES = {
    "manufacturer_name",
    "manufacturer_address",
    "manufacturer_pincode",
    "packer_name",
    "packer_address",
    "packer_pincode",
    "importer_name",
    "importer_address",
    "importer_pincode",
}

# V1 is_advanced allowlist (canonical names that are always advanced)
ADVANCED_CANONICAL_NAMES = {"group_id"}

# STEP_ASSIGNMENT and STEP_ORDER are now imported from backend/app/i18n/step_assignment.py.
# Do NOT re-define them here — any edits must go to that module (bump RULESET_VERSION too).


def slugify(name: str) -> str:
    """Convert a raw field name to a canonical slug when no alias match exists."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def build_alias_map(aliases_data: dict) -> dict[str, str]:
    """Build {variant_name: canonical_name} lookup from canonical_field_aliases.json."""
    alias_map: dict[str, str] = {}
    aliases = aliases_data.get("aliases", {})

    for _family_key, family_data in aliases.items():
        if "variants" in family_data:
            canonical = family_data["canonical"]
            for v in family_data["variants"]:
                alias_map[v] = canonical

        elif "variants_3field" in family_data:
            for v in family_data.get("variants_3field", []):
                vl = v.lower()
                if "manufacturer" in vl:
                    if "name" in vl:
                        alias_map[v] = "manufacturer_name"
                    elif "address" in vl:
                        alias_map[v] = "manufacturer_address"
                    elif "pincode" in vl:
                        alias_map[v] = "manufacturer_pincode"
                elif "packer" in vl:
                    if "name" in vl:
                        alias_map[v] = "packer_name"
                    elif "address" in vl:
                        alias_map[v] = "packer_address"
                    elif "pincode" in vl:
                        alias_map[v] = "packer_pincode"
                elif "importer" in vl:
                    if "name" in vl:
                        alias_map[v] = "importer_name"
                    elif "address" in vl:
                        alias_map[v] = "importer_address"
                    elif "pincode" in vl:
                        alias_map[v] = "importer_pincode"

            for v in family_data.get("variants_combined", []):
                vl = v.lower()
                if "manufacturer" in vl:
                    alias_map[v] = "manufacturer_details"
                elif "packer" in vl:
                    alias_map[v] = "packer_details"
                elif "importer" in vl:
                    alias_map[v] = "importer_details"

        elif "canonical_set" in family_data:
            for sub_canonical, sub_variants in family_data["canonical_set"].items():
                for v in sub_variants:
                    alias_map[v] = sub_canonical

    return alias_map


def resolve_canonical(raw_name: str, alias_map: dict[str, str]) -> str:
    """Resolve raw Meesho field name to canonical name."""
    if raw_name in alias_map:
        return alias_map[raw_name]
    return slugify(raw_name)


def classify_primitive(field: dict, canonical_name: str) -> str:
    """Infer the input primitive from data_type + field name pattern.

    Delegates to ``app.i18n.primitive_classifier.classify_primitive``.
    The canonical implementation lives there — do NOT add logic here.
    See ``backend/app/i18n/primitive_classifier.py`` for the full rule table.
    """
    from app.i18n.primitive_classifier import classify_primitive as _cp

    data_type = field.get("data_type", "text")
    enum_count = field.get("enum_count", 0) or 0
    # has_unit_companion: not tracked in batch JSON at Phase 3 — False by default.
    # The unit-keyword pattern in UNIT_KEYWORDS covers the same set of fields.
    return _cp(
        name=canonical_name,
        data_type=data_type,
        enum_count=enum_count,
        has_unit_companion=False,
    )


def assign_step_id(canonical_name: str) -> str:
    """Assign a wizard step_id by pattern-matching against canonical_name.

    Delegates to ``app.i18n.step_assignment.assign_step``.
    The canonical implementation lives there — do NOT add logic here.
    """
    from app.i18n.step_assignment import assign_step as _as

    return _as(canonical_name=canonical_name, primitive="", compliance_role=None)


def title_case_canonical(canonical_name: str) -> str:
    """Convert canonical_name (snake_case) to title-cased display label."""
    return canonical_name.replace("_", " ").title()


def build_field_schema(
    field: dict,
    canonical_name: str,
    display_overrides: dict,
) -> dict:
    """Build a single field's full §5.6.1 schema object."""
    raw_name = field["name"]
    data_type = field.get("data_type", "text")
    marker = field.get("marker", "optional")
    col = field.get("col", 0)
    enum_count = field.get("enum_count", 0) or 0
    help_text_raw = field.get("help_text") or None

    primitive = classify_primitive(field, canonical_name)
    step_id = assign_step_id(canonical_name)
    compliance_role = canonical_name if canonical_name in COMPLIANCE_CANONICAL_ROLES else None
    is_advanced = canonical_name in ADVANCED_CANONICAL_NAMES

    # Check display overrides (strip underscore-prefixed comment markers)
    override = display_overrides.get(canonical_name)

    if override and not canonical_name.startswith("_"):
        display_label = override.get("display_label", {"en": title_case_canonical(canonical_name)})
        display_help = override.get("display_help", {"en": help_text_raw})
        display_placeholder = override.get("display_placeholder")
        display_unit_label = override.get("display_unit_label")
        # is_advanced can be overridden by the overrides file
        if override.get("is_advanced") is True:
            is_advanced = True
    else:
        display_label = {"en": title_case_canonical(canonical_name)}
        display_help = {"en": help_text_raw} if help_text_raw else None
        display_placeholder = None
        display_unit_label = None

    schema_field: dict[str, Any] = {
        # Canonical layer
        "canonical_name": canonical_name,
        "data_type": data_type,
        "primitive": primitive,
        "marker": marker,
        "is_advanced": is_advanced,
        "is_hidden": False,
        "compliance_role": compliance_role,
        "step_id": step_id,
        "max_length": None,
        "min_length": None,
        "regex": None,
        "min_value": None,
        "max_value": None,
        "unit_suffix": None,
        # Display layer
        "display_label": display_label,
        "display_help": display_help,
        "display_placeholder": display_placeholder,
        "display_unit_label": display_unit_label,
        "validation_message": None,
        "help_url": None,
        # Export layer
        "meesho_column_header": raw_name,
        "meesho_column_index": col,
        "meesho_default": None,
        # Enum (null at template level — per-category enums in field_enum_values)
        "enum_codes_map": None,
        "enum_labels": None,
    }
    return schema_field


def compute_schema_hash(raw_fields: list[dict], alias_map: dict[str, str]) -> str:
    """Compute sha256 of canonical-JSON-serialization of a fields[] array.

    Hash is computed over all raw field properties EXCEPT enum_values (which are
    per-category and live in the field_enum_values table). Includes enum_source,
    help_text, enum_count, and the resolved canonical_name.

    This approach gives ~3,566 distinct templates which is within ±0.5% of the
    §1 SSoT target of 3,557 (tolerance: 3,539–3,575).

    We hash the raw field data rather than the post-transformation schema objects
    because the transformation is deterministic; the distinguishing properties are
    all present in the raw input.
    """
    canonical_repr = []
    for f in raw_fields:
        # Build a reduced representation: all raw properties except enum_values
        entry = {k: v for k, v in f.items() if k != "enum_values"}
        # Override raw name with resolved canonical name for normalisation
        entry["canonical_name"] = resolve_canonical(f["name"], alias_map)
        entry.pop("name", None)
        canonical_repr.append(entry)
    # Preserve original column order (col is already in each entry)
    canonical_repr.sort(key=lambda x: x.get("col", 0))
    return hashlib.sha256(json.dumps(canonical_repr, sort_keys=True).encode()).hexdigest()


def compute_wizard_step_count(fields: list[dict]) -> int:
    """Compute wizard step count per §3 formula: ceiling(compulsory_count / 5), min 3 max 8."""
    import math
    compulsory_count = sum(1 for f in fields if f.get("marker") == "compulsory")
    raw = math.ceil(compulsory_count / 5)
    return max(3, min(8, raw))


def detect_compliance_shape(fields: list[dict]) -> str:
    """Detect compliance_shape: 'collapsed' if leaf contains collapsed compliance fields."""
    raw_names = {f.get("name", "") for f in fields}
    if raw_names & COLLAPSED_FIELD_NAMES:
        return "collapsed"
    return "standard"


def process_leaf(
    leaf: dict,
    alias_map: dict[str, str],
    display_overrides: dict,
) -> tuple[str, dict, str, str]:
    """Process one leaf and return (schema_hash, schema_jsonb, leaf_id, compliance_shape).

    Returns:
      schema_hash: dedup key
      schema_jsonb: full JSONB payload for templates.schema_jsonb
      leaf_id: leaf's meesho_leaf_id
      compliance_shape: 'standard' | 'collapsed'
    """
    leaf_id = leaf["leaf_id"]
    main_sheet = leaf.get("main_sheet", "")
    raw_fields = leaf.get("fields", [])

    compliance_shape = detect_compliance_shape(raw_fields)

    # Compute schema hash over raw fields (excluding enum_values, normalised names)
    schema_hash = compute_schema_hash(raw_fields, alias_map)

    # Build full schema fields for storage
    full_fields = []
    for field in raw_fields:
        canonical_name = resolve_canonical(field["name"], alias_map)
        field_schema = build_field_schema(field, canonical_name, display_overrides)
        full_fields.append(field_schema)

    compulsory_count = leaf.get("compulsory_count", 0)
    optional_count = leaf.get("optional_count", 0)
    total_count = leaf.get("field_count", len(raw_fields))
    wizard_step_count = compute_wizard_step_count(raw_fields)

    schema_jsonb = {
        "fields": full_fields,
        "compulsory_count": compulsory_count,
        "optional_count": optional_count,
        "total_count": total_count,
        "wizard_step_count": wizard_step_count,
        "main_sheet_label": main_sheet,
    }

    return schema_hash, schema_jsonb, leaf_id, compliance_shape


async def seed(session: AsyncSession) -> tuple[int, dict[str, str]]:
    """Build and UPSERT all templates. Returns (template_count, leaf_id_to_hash_map)."""
    # Load alias map
    logger.info("Loading alias map from %s", ALIASES_FILE)
    with open(ALIASES_FILE) as fh:
        aliases_data = json.load(fh)
    alias_map = build_alias_map(aliases_data)
    logger.info("Alias map: %d entries", len(alias_map))

    # Load display overrides (strip comment-marker keys starting with _)
    logger.info("Loading display overrides from %s", OVERRIDES_FILE)
    with open(OVERRIDES_FILE) as fh:
        overrides_raw = json.load(fh)
    display_overrides = {
        k: v for k, v in overrides_raw.get("fields", {}).items()
        if not k.startswith("_")
    }
    logger.info("Display overrides: %d entries", len(display_overrides))

    # Process all batch files
    batch_files = sorted(DATA_ROOT.glob(BATCH_GLOB))
    logger.info("Processing %d batch files", len(batch_files))

    # template_hash → schema_jsonb + compliance_shape (dedup map)
    templates_by_hash: dict[str, dict] = {}
    # leaf_id → schema_hash (for seed_categories.py)
    leaf_id_to_hash: dict[str, str] = {}

    unmapped_count = 0
    total_leaves = 0

    for batch_file in batch_files:
        with open(batch_file) as fh:
            batch = json.load(fh)
        leaves = batch.get("leaves", [])
        logger.info("  %s: %d leaves", batch_file.name, len(leaves))

        for leaf in leaves:
            total_leaves += 1
            schema_hash, schema_jsonb, leaf_id, compliance_shape = process_leaf(
                leaf, alias_map, display_overrides
            )
            leaf_id_to_hash[leaf_id] = schema_hash

            if schema_hash not in templates_by_hash:
                templates_by_hash[schema_hash] = {
                    "schema_hash": schema_hash,
                    "schema_jsonb": schema_jsonb,
                    "compliance_shape": compliance_shape,
                    "parser_version": batch.get("parser_version", "0.2"),
                    "_leaf_id_first_seen": leaf_id,  # for logging; not a DB column
                }

    logger.info(
        "Total leaves processed: %d | Distinct templates: %d",
        total_leaves, len(templates_by_hash),
    )

    # Verify Eye-Serum compliance_shape
    eye_serum_hash = leaf_id_to_hash.get(EYE_SERUM_LEAF_ID)
    if eye_serum_hash:
        eye_serum_template = templates_by_hash.get(eye_serum_hash, {})
        logger.info(
            "Eye-Serum (leaf %s) compliance_shape: %s",
            EYE_SERUM_LEAF_ID,
            eye_serum_template.get("compliance_shape", "UNKNOWN"),
        )
        if eye_serum_template.get("compliance_shape") != "collapsed":
            logger.error("STOP CONDITION: Eye-Serum compliance_shape is not 'collapsed'!")
            raise RuntimeError("Eye-Serum compliance_shape detection failed")
    else:
        logger.error("STOP CONDITION: Eye-Serum leaf %s not found in any batch", EYE_SERUM_LEAF_ID)
        raise RuntimeError(f"Eye-Serum leaf {EYE_SERUM_LEAF_ID} not found")

    # Count collapsed templates
    collapsed_count = sum(
        1 for t in templates_by_hash.values() if t.get("compliance_shape") == "collapsed"
    )
    logger.info("Templates with compliance_shape='collapsed': %d (expected 1)", collapsed_count)
    if collapsed_count != 1:
        logger.error("STOP CONDITION: Expected exactly 1 collapsed template, found %d", collapsed_count)
        raise RuntimeError(f"Unexpected collapsed template count: {collapsed_count}")

    # Validate template count against target (3,557 ±0.5%)
    actual_count = len(templates_by_hash)
    target = 3557
    tolerance = 0.005
    low = int(target * (1 - tolerance))
    high = int(target * (1 + tolerance)) + 1  # +1 for ceiling
    if not (low <= actual_count <= high):
        logger.error(
            "STOP CONDITION: template count %d outside tolerance [%d, %d]",
            actual_count, low, high,
        )
        raise RuntimeError(
            f"Template count {actual_count} outside target range [{low}, {high}]"
        )
    logger.info(
        "Template count %d within tolerance [%d, %d] of target %d",
        actual_count, low, high, target,
    )

    # Build rows for DB insert (strip internal-only keys)
    rows = []
    for t in templates_by_hash.values():
        rows.append({
            "schema_hash": t["schema_hash"],
            "schema_jsonb": t["schema_jsonb"],
            "compliance_shape": t["compliance_shape"],
            "parser_version": t["parser_version"],
        })

    # Bulk UPSERT in chunks.
    # Templates have large schema_jsonb payloads — use small chunks to avoid
    # connection timeout and asyncpg parameter count limits.
    CHUNK_SIZE = 50
    upserted = 0
    total = len(rows)
    for i in range(0, total, CHUNK_SIZE):
        chunk = rows[i: i + CHUNK_SIZE]
        stmt = (
            pg_insert(Template)
            .values(chunk)
            .on_conflict_do_update(
                index_elements=["schema_hash"],
                set_={
                    "schema_jsonb": pg_insert(Template).excluded.schema_jsonb,
                    "compliance_shape": pg_insert(Template).excluded.compliance_shape,
                    "parser_version": pg_insert(Template).excluded.parser_version,
                },
            )
        )
        await session.execute(stmt)
        upserted += len(chunk)
        if upserted % 500 == 0 or upserted == total:
            logger.info("  Upserted %d / %d templates", upserted, total)

    await session.commit()
    logger.info("Committed %d template rows to DB", total)

    # Persist leaf_id → hash map for seed_categories.py
    with open(LEAF_HASH_MAP_FILE, "w") as fh:
        json.dump(leaf_id_to_hash, fh)
    logger.info("Wrote leaf_id→hash map to %s (%d entries)", LEAF_HASH_MAP_FILE, len(leaf_id_to_hash))

    return len(rows), leaf_id_to_hash


async def main() -> int:
    """Entry point. Returns template count."""
    logger.info("=== build_template_schemas.py starting ===")
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    count = 0
    try:
        async with session_maker() as session:
            count, _ = await seed(session)
        logger.info("templates seeded: %d rows", count)
    finally:
        await engine.dispose()
    return count


if __name__ == "__main__":
    asyncio.run(main())
