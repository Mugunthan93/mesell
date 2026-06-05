"""Seed script: categories table.

Reads backend/app/data/meesho_category_tree.json and UPSERTs all 3,772 leaf entries.

Requires build_template_schemas.py to have run first (it writes
data/parsed/leaf_id_to_schema_hash.json which this script reads to look up template_id).

Run:
    PYTHONPATH=backend python scripts/seed_categories.py

Requires DATABASE_URL env var (or .env file in backend/).
"""

from __future__ import annotations

import asyncio
import json
import logging
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

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.category import Category
from app.models.template import Template

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("seed_categories")

CATEGORY_TREE_FILE = BACKEND_ROOT / "app" / "data" / "meesho_category_tree.json"
LEAF_HASH_MAP_FILE = DATA_ROOT / "leaf_id_to_schema_hash.json"

# Target count for smoke check
TARGET_CATEGORIES = 3772


async def load_hash_to_template_id(session: AsyncSession) -> dict[str, str]:
    """Build {schema_hash: template_id (as str)} from the templates table."""
    result = await session.execute(
        select(Template.schema_hash, Template.id)
    )
    rows = result.all()
    mapping = {row.schema_hash: str(row.id) for row in rows}
    logger.info("Loaded %d schema_hash → template_id mappings from DB", len(mapping))
    return mapping


async def seed(session: AsyncSession) -> int:
    """UPSERT all categories. Returns number of rows upserted."""
    # Load category tree
    logger.info("Loading category tree from %s", CATEGORY_TREE_FILE)
    with open(CATEGORY_TREE_FILE) as fh:
        tree = json.load(fh)

    all_entries = tree.get("categories", [])
    leaves = [e for e in all_entries if e.get("is_leaf", False)]
    logger.info("Total entries: %d | Leaf entries: %d", len(all_entries), len(leaves))

    if len(leaves) != TARGET_CATEGORIES:
        logger.warning(
            "Leaf count %d differs from expected %d", len(leaves), TARGET_CATEGORIES
        )

    # Load leaf_id → schema_hash intermediate map
    if not LEAF_HASH_MAP_FILE.exists():
        raise FileNotFoundError(
            f"{LEAF_HASH_MAP_FILE} not found — run build_template_schemas.py first"
        )
    with open(LEAF_HASH_MAP_FILE) as fh:
        leaf_id_to_hash: dict[str, str] = json.load(fh)
    logger.info("Loaded %d leaf_id → schema_hash entries", len(leaf_id_to_hash))

    # Load schema_hash → template_id (UUID as str) from the templates table
    hash_to_template_id = await load_hash_to_template_id(session)

    rows = []
    missing_hash = []
    missing_template = []

    for entry in leaves:
        leaf_id = entry["leaf_id"]
        leaf_name = entry["leaf_name"]
        super_id = entry["super_id"]

        # path array in the tree already includes leaf_name as the last element
        path_parts = entry.get("path", [])
        if not path_parts:
            path_parts = [leaf_name]
        path_str = " > ".join(path_parts)

        # super_name = first element of path
        super_name = path_parts[0] if path_parts else ""

        # Look up template_id via leaf_id → hash → template.id
        schema_hash = leaf_id_to_hash.get(leaf_id)
        if schema_hash is None:
            missing_hash.append(leaf_id)
            logger.warning("No schema_hash for leaf_id %s — skipping", leaf_id)
            continue

        template_id = hash_to_template_id.get(schema_hash)
        if template_id is None:
            missing_template.append(leaf_id)
            logger.warning(
                "No template_id for leaf_id %s (hash %s...) — skipping",
                leaf_id, schema_hash[:12],
            )
            continue

        rows.append({
            "meesho_leaf_id": leaf_id,
            "super_id": super_id,
            "super_name": super_name,
            "path": path_str,
            "leaf_name": leaf_name,
            "template_id": template_id,
            "commission_pct": None,
        })

    if missing_hash or missing_template:
        logger.error(
            "Missing hash: %d | Missing template: %d",
            len(missing_hash), len(missing_template),
        )
        raise RuntimeError(
            f"FK resolution failed: {len(missing_hash)} leaves have no hash, "
            f"{len(missing_template)} have no template"
        )

    logger.info("Built %d category rows", len(rows))

    # Validate count
    if len(rows) != TARGET_CATEGORIES:
        logger.error(
            "STOP CONDITION: category count %d != expected %d",
            len(rows), TARGET_CATEGORIES,
        )
        raise RuntimeError(f"Category count {len(rows)} != expected {TARGET_CATEGORIES}")

    # Bulk UPSERT — chunk to avoid single giant parameterized query
    CHUNK_SIZE = 500
    total_upserted = 0
    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i: i + CHUNK_SIZE]
        stmt = (
            pg_insert(Category)
            .values(chunk)
            .on_conflict_do_update(
                index_elements=["meesho_leaf_id"],
                set_={
                    "super_id": pg_insert(Category).excluded.super_id,
                    "super_name": pg_insert(Category).excluded.super_name,
                    "path": pg_insert(Category).excluded.path,
                    "leaf_name": pg_insert(Category).excluded.leaf_name,
                    "template_id": pg_insert(Category).excluded.template_id,
                    "commission_pct": pg_insert(Category).excluded.commission_pct,
                },
            )
        )
        await session.execute(stmt)
        total_upserted += len(chunk)
        logger.info("  Upserted chunk %d / %d", total_upserted, len(rows))

    await session.commit()
    logger.info("Committed %d category rows", len(rows))
    return len(rows)


async def main() -> int:
    """Entry point. Returns row count."""
    logger.info("=== seed_categories.py starting ===")
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    count = 0
    try:
        async with session_maker() as session:
            count = await seed(session)
        logger.info("categories seeded: %d rows", count)
    finally:
        await engine.dispose()
    return count


if __name__ == "__main__":
    asyncio.run(main())
