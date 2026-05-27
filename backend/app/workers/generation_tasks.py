"""Celery tasks for AI catalog generation."""

import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_generation(catalog_id: uuid.UUID) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.database import async_session_maker
    from app.models.catalog import Catalog
    from app.models.sku import SKU
    from app.services.ai_engine import get_ai_engine

    engine = get_ai_engine()
    summary = {"catalog_id": str(catalog_id), "skus_generated": 0, "errors": []}

    async with async_session_maker() as db:
        catalog = (
            await db.execute(
                select(Catalog)
                .where(Catalog.id == catalog_id)
                .options(selectinload(Catalog.skus))
            )
        ).scalar_one_or_none()
        if catalog is None:
            raise ValueError(f"Catalog {catalog_id} not found")

        for sku in catalog.skus:
            try:
                result = await engine.generate_listing(
                    product_name=sku.product_name,
                    category=catalog.category,
                    subcategory=catalog.subcategory,
                    material=sku.material,
                    sizes=sku.sizes,
                    colors=sku.colors,
                    price=float(sku.selling_price) if sku.selling_price else None,
                )
                sku.ai_title = result["title"]
                sku.ai_description = result["description"]
                sku.ai_keywords = result["keywords"]
                sku.ai_category = result["category"]
                sku.ai_attributes = result["attributes"]
                summary["skus_generated"] += 1
            except Exception as exc:
                logger.exception(f"Generation failed for SKU {sku.id}: {exc}")
                summary["errors"].append({"sku_id": str(sku.id), "error": str(exc)})

        catalog.status = "generated"

        from app.models.user import User
        user = await db.get(User, catalog.user_id)
        if user is not None:
            user.catalogs_used = (user.catalogs_used or 0) + 1
        await db.commit()

    return summary


@celery_app.task(name="catalog.generate", bind=True, max_retries=1)
def generate_catalog(self, catalog_id: str) -> dict:
    try:
        return asyncio.run(_run_generation(uuid.UUID(catalog_id)))
    except Exception as exc:
        logger.exception(f"generate_catalog({catalog_id}) failed: {exc}")
        raise self.retry(exc=exc, countdown=15)


async def _regenerate_sku(sku_id: uuid.UUID, variation_index: int) -> dict:
    from app.database import async_session_maker
    from app.models.catalog import Catalog
    from app.models.sku import SKU
    from app.services.ai_engine import get_ai_engine

    async with async_session_maker() as db:
        sku = await db.get(SKU, sku_id)
        if sku is None:
            raise ValueError(f"SKU {sku_id} not found")
        catalog = await db.get(Catalog, sku.catalog_id)
        engine = get_ai_engine()
        result = await engine.generate_listing(
            product_name=sku.product_name,
            category=catalog.category if catalog else None,
            subcategory=catalog.subcategory if catalog else None,
            material=sku.material,
            sizes=sku.sizes,
            colors=sku.colors,
            price=float(sku.selling_price) if sku.selling_price else None,
            variation_index=variation_index,
        )
        sku.ai_title = result["title"]
        sku.ai_description = result["description"]
        sku.ai_keywords = result["keywords"]
        sku.ai_category = result["category"]
        sku.ai_attributes = result["attributes"]
        await db.commit()
        return {"sku_id": str(sku.id), "variation": variation_index}


@celery_app.task(name="sku.regenerate")
def regenerate_sku(sku_id: str, variation_index: int = 1) -> dict:
    return asyncio.run(_regenerate_sku(uuid.UUID(sku_id), variation_index))
