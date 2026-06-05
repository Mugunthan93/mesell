"""Seed script: field_aliases table.

Reads data/parsed/canonical_field_aliases.json and UPSERTS all (canonical_name, variant)
pairs into the field_aliases table.

for_xlsx_export semantics:
  TRUE  — the variant differs from the canonical_name (i.e., it is a Meesho-wire-format name
          that the Export Adapter must restore verbatim, including intentional typos like
          "Primiary" / "Seconadry").
  FALSE — the variant equals the canonical_name (rare; only when the canonical is its own
          variant, which does not occur in V1 data).

Run:
    PYTHONPATH=backend python scripts/seed_field_aliases.py

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

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.field_alias import FieldAlias

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("seed_field_aliases")

ALIASES_FILE = DATA_ROOT / "canonical_field_aliases.json"


def _compliance_3field_canonical(variant: str) -> str | None:
    """Map a compliance 3-field variant header to its canonical name."""
    vl = variant.lower()
    if "manufacturer" in vl:
        if "name" in vl:
            return "manufacturer_name"
        if "address" in vl:
            return "manufacturer_address"
        if "pincode" in vl:
            return "manufacturer_pincode"
    elif "packer" in vl:
        if "name" in vl:
            return "packer_name"
        if "address" in vl:
            return "packer_address"
        if "pincode" in vl:
            return "packer_pincode"
    elif "importer" in vl:
        if "name" in vl:
            return "importer_name"
        if "address" in vl:
            return "importer_address"
        if "pincode" in vl:
            return "importer_pincode"
    logger.warning("Could not map 3-field compliance variant: %r", variant)
    return None


def _compliance_combined_canonical(variant: str) -> str | None:
    """Map a combined compliance variant (e.g. 'Manufacturer Details') to its canonical."""
    vl = variant.lower()
    if "manufacturer" in vl:
        return "manufacturer_details"
    if "packer" in vl:
        return "packer_details"
    if "importer" in vl:
        return "importer_details"
    logger.warning("Could not map combined compliance variant: %r", variant)
    return None


def build_alias_rows(aliases_data: dict) -> list[dict]:
    """Parse canonical_field_aliases.json → list of row dicts for field_aliases table.

    Handles three family shapes:
      1. Standard: {"canonical": "...", "variants": [...]}
      2. Compliance block: {"variants_3field": [...], "variants_combined": [...]}
      3. Multi-canonical: {"canonical_set": {sub_canonical: [variants]}}
    """
    aliases = aliases_data.get("aliases", {})
    rows: list[dict] = []
    seen: set[str] = set()

    for _family_key, family_data in aliases.items():

        if "variants" in family_data:
            # Standard family — one canonical, N variants
            canonical = family_data["canonical"]
            for variant in family_data["variants"]:
                if variant in seen:
                    logger.warning("Duplicate variant %r — skipping", variant)
                    continue
                seen.add(variant)
                rows.append({
                    "variant_name": variant,
                    "canonical_name": canonical,
                    "source": "corpus",
                    "for_xlsx_export": variant != canonical,
                })

        elif "variants_3field" in family_data:
            # Compliance block — each 3-field variant maps to its specific canonical
            for variant in family_data.get("variants_3field", []):
                canonical = _compliance_3field_canonical(variant)
                if canonical is None:
                    continue
                if variant in seen:
                    logger.warning("Duplicate variant %r — skipping", variant)
                    continue
                seen.add(variant)
                rows.append({
                    "variant_name": variant,
                    "canonical_name": canonical,
                    "source": "corpus",
                    "for_xlsx_export": variant != canonical,
                })
            for variant in family_data.get("variants_combined", []):
                canonical = _compliance_combined_canonical(variant)
                if canonical is None:
                    continue
                if variant in seen:
                    logger.warning("Duplicate variant %r — skipping", variant)
                    continue
                seen.add(variant)
                rows.append({
                    "variant_name": variant,
                    "canonical_name": canonical,
                    "source": "corpus",
                    "for_xlsx_export": variant != canonical,
                })

        elif "canonical_set" in family_data:
            # Multi-canonical family — e.g. warranty_family, wireless_certification
            for sub_canonical, sub_variants in family_data["canonical_set"].items():
                for variant in sub_variants:
                    if variant in seen:
                        logger.warning("Duplicate variant %r — skipping", variant)
                        continue
                    seen.add(variant)
                    rows.append({
                        "variant_name": variant,
                        "canonical_name": sub_canonical,
                        "source": "corpus",
                        "for_xlsx_export": variant != sub_canonical,
                    })

    return rows


async def seed(session: AsyncSession) -> int:
    """UPSERT all alias rows. Returns number of rows processed."""
    logger.info("Loading %s", ALIASES_FILE)
    with open(ALIASES_FILE) as fh:
        aliases_data = json.load(fh)

    rows = build_alias_rows(aliases_data)
    n_families = len(aliases_data.get("aliases", {}))
    logger.info("Built %d alias rows from %d families", len(rows), n_families)

    if not rows:
        logger.warning("No alias rows generated — check canonical_field_aliases.json format")
        return 0

    stmt = (
        pg_insert(FieldAlias)
        .values(rows)
        .on_conflict_do_update(
            index_elements=["variant_name"],
            set_={
                "canonical_name": pg_insert(FieldAlias).excluded.canonical_name,
                "source": pg_insert(FieldAlias).excluded.source,
                "for_xlsx_export": pg_insert(FieldAlias).excluded.for_xlsx_export,
            },
        )
    )
    await session.execute(stmt)
    await session.commit()
    logger.info("Committed %d field_alias row(s)", len(rows))
    return len(rows)


async def main() -> int:
    """Entry point. Returns row count."""
    logger.info("=== seed_field_aliases.py starting ===")
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    count = 0
    try:
        async with session_maker() as session:
            count = await seed(session)
        logger.info("field_aliases seeded: %d rows", count)
    finally:
        await engine.dispose()
    return count


if __name__ == "__main__":
    asyncio.run(main())
