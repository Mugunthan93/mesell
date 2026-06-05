"""Seed script: field_enum_values table.

Reads all 12 batch JSONs. For each leaf and each field with enum_values:
  - Looks up category_id via leaf_id → categories.meesho_leaf_id
  - Resolves canonical field_name via alias map
  - Builds enum_entries in §5.6.4 shape: [{"canonical": v, "meesho": v, "labels": {"en": v}}]
  - UPSERTs (category_id, field_name) row

Uses bulk inserts chunked to avoid parameter limits.

Run:
    PYTHONPATH=backend python scripts/seed_field_enum_values.py

Requires DATABASE_URL env var (or .env file in backend/).
Run after seed_categories.py (requires categories.id FKs to exist).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

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

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.category import Category
from app.models.field_enum_value import FieldEnumValue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("seed_field_enum_values")

ALIASES_FILE = DATA_ROOT / "canonical_field_aliases.json"
BATCH_GLOB = "batch_*.json"

# Smoke check target
TARGET_ENUM_ROWS = 49295
TOLERANCE = 0.005  # ±0.5%

# Chunk size for bulk inserts (~49K rows; keep parameter count under driver limits)
CHUNK_SIZE = 500


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def build_alias_map(aliases_data: dict) -> dict[str, str]:
    """Build {variant_name: canonical_name} lookup."""
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
    if raw_name in alias_map:
        return alias_map[raw_name]
    return slugify(raw_name)


async def load_leaf_id_to_category_id(session: AsyncSession) -> dict[str, str]:
    """Load {meesho_leaf_id: category.id (str UUID)} from the categories table."""
    result = await session.execute(
        select(Category.meesho_leaf_id, Category.id)
    )
    rows = result.all()
    mapping = {row.meesho_leaf_id: str(row.id) for row in rows}
    logger.info("Loaded %d leaf_id → category_id mappings", len(mapping))
    return mapping


def build_enum_entries(enum_values: list[str]) -> list[dict]:
    """Build the §5.6.4 enum_entries structure (V1: canonical == meesho == labels.en)."""
    return [
        {"canonical": v, "meesho": v, "labels": {"en": v}}
        for v in enum_values
    ]


async def seed(session: AsyncSession) -> int:
    """UPSERT all field_enum_values rows. Returns total rows inserted."""
    # Load alias map
    with open(ALIASES_FILE) as fh:
        aliases_data = json.load(fh)
    alias_map = build_alias_map(aliases_data)

    # Load leaf_id → category_id mapping (requires categories seeded first)
    leaf_to_cat = await load_leaf_id_to_category_id(session)

    batch_files = sorted(DATA_ROOT.glob(BATCH_GLOB))
    logger.info("Processing %d batch files for field_enum_values", len(batch_files))

    all_rows: list[dict] = []
    missing_cat_ids = []
    duplicate_pairs: set[tuple[str, str]] = set()

    for batch_file in batch_files:
        with open(batch_file) as fh:
            batch = json.load(fh)
        leaves = batch.get("leaves", [])

        for leaf in leaves:
            leaf_id = leaf["leaf_id"]
            category_id = leaf_to_cat.get(leaf_id)
            if category_id is None:
                missing_cat_ids.append(leaf_id)
                continue

            for field in leaf.get("fields", []):
                enum_values = field.get("enum_values")
                if not enum_values:
                    continue

                canonical_name = resolve_canonical(field["name"], alias_map)
                enum_count = field.get("enum_count", len(enum_values))
                enum_source = field.get("enum_source", "")
                truncated = (
                    enum_source == "ranged" and len(enum_values) < enum_count
                )

                pair = (category_id, canonical_name)
                if pair in duplicate_pairs:
                    # Two fields in the same leaf mapped to the same canonical name
                    # (rare alias collision). Skip second occurrence.
                    logger.debug(
                        "Duplicate (category_id, field_name) pair: leaf=%s field=%r → %r",
                        leaf_id, field["name"], canonical_name,
                    )
                    continue
                duplicate_pairs.add(pair)

                enum_entries = build_enum_entries(enum_values)
                all_rows.append({
                    "category_id": category_id,
                    "field_name": canonical_name,
                    "enum_entries": json.dumps(enum_entries),
                    "value_count": enum_count,
                    "truncated": truncated,
                })

    if missing_cat_ids:
        logger.error(
            "STOP CONDITION: %d leaf_ids have no category_id in DB: %s",
            len(missing_cat_ids), missing_cat_ids[:10],
        )
        raise RuntimeError(
            f"FK violation: {len(missing_cat_ids)} leaves have no category. "
            "Run seed_categories.py first."
        )

    total = len(all_rows)
    logger.info("Total field_enum_values rows to upsert: %d", total)

    # Smoke check
    low = int(TARGET_ENUM_ROWS * (1 - TOLERANCE))
    high = int(TARGET_ENUM_ROWS * (1 + TOLERANCE)) + 1
    if not (low <= total <= high):
        logger.error(
            "STOP CONDITION: field_enum_values count %d outside tolerance [%d, %d]",
            total, low, high,
        )
        raise RuntimeError(
            f"field_enum_values count {total} outside target range [{low}, {high}]"
        )
    logger.info(
        "field_enum_values count %d within tolerance [%d, %d] of target %d",
        total, low, high, TARGET_ENUM_ROWS,
    )

    # Bulk UPSERT in chunks
    upserted = 0
    for i in range(0, len(all_rows), CHUNK_SIZE):
        chunk = all_rows[i: i + CHUNK_SIZE]
        # Convert enum_entries from JSON string back to Python list for JSONB
        # (pg_insert handles Python dicts/lists natively as JSONB)
        chunk_rows = []
        for row in chunk:
            row_copy = dict(row)
            row_copy["enum_entries"] = json.loads(row_copy["enum_entries"])
            chunk_rows.append(row_copy)

        stmt = (
            pg_insert(FieldEnumValue)
            .values(chunk_rows)
            .on_conflict_do_update(
                index_elements=["category_id", "field_name"],
                set_={
                    "enum_entries": pg_insert(FieldEnumValue).excluded.enum_entries,
                    "value_count": pg_insert(FieldEnumValue).excluded.value_count,
                    "truncated": pg_insert(FieldEnumValue).excluded.truncated,
                },
            )
        )
        await session.execute(stmt)
        upserted += len(chunk)
        if upserted % 5000 == 0 or upserted == total:
            logger.info("  Upserted %d / %d", upserted, total)

    await session.commit()
    logger.info("Committed %d field_enum_values rows", total)
    return total


async def main() -> int:
    """Entry point. Returns row count."""
    logger.info("=== seed_field_enum_values.py starting ===")
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    count = 0
    try:
        async with session_maker() as session:
            count = await seed(session)
        logger.info("field_enum_values seeded: %d rows", count)
    finally:
        await engine.dispose()
    return count


if __name__ == "__main__":
    asyncio.run(main())
