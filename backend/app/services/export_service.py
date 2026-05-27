"""Meesho bulk-upload CSV and processed-images ZIP export."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
import uuid
import zipfile

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Catalog
from app.models.export import Export
from app.models.image import Image
from app.models.sku import SKU
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

# Meesho-bulk-upload column order (approximation of the public template).
MEESHO_CSV_COLUMNS = [
    "catalog_name",
    "product_title",
    "product_description",
    "category",
    "sub_category",
    "mrp",
    "selling_price",
    "gst_percentage",
    "hsn_code",
    "size",
    "color",
    "brand",
    "material",
    "country_of_origin",
    "manufacturer_name",
    "image_1",
    "image_2",
    "image_3",
    "image_4",
    "weight_grams",
]

DEFAULT_GST = "5"
DEFAULT_COUNTRY = "India"
DEFAULT_BRAND = "Generic"


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_") or "product"


async def _load_catalog(db: AsyncSession, catalog_id: uuid.UUID) -> Catalog:
    catalog = (
        await db.execute(
            select(Catalog)
            .where(Catalog.id == catalog_id)
            .options(selectinload(Catalog.skus).selectinload(SKU.images))
        )
    ).scalar_one()
    return catalog


def _row(catalog: Catalog, sku: SKU) -> dict:
    images = sorted(sku.images, key=lambda i: i.sort_order)
    img_urls = [i.processed_url or i.original_url for i in images][:4]
    img_urls += [""] * (4 - len(img_urls))
    return {
        "catalog_name": catalog.name,
        "product_title": sku.ai_title or sku.product_name,
        "product_description": sku.ai_description or "",
        "category": catalog.category or "",
        "sub_category": catalog.subcategory or "",
        "mrp": str(sku.selling_price or ""),
        "selling_price": str(sku.selling_price or ""),
        "gst_percentage": DEFAULT_GST,
        "hsn_code": "",
        "size": sku.sizes or "Free Size",
        "color": sku.colors or "",
        "brand": DEFAULT_BRAND,
        "material": sku.material or "",
        "country_of_origin": DEFAULT_COUNTRY,
        "manufacturer_name": "Self",
        "image_1": img_urls[0],
        "image_2": img_urls[1],
        "image_3": img_urls[2],
        "image_4": img_urls[3],
        "weight_grams": str(sku.weight_grams or ""),
    }


async def generate_meesho_csv(db: AsyncSession, catalog_id: uuid.UUID) -> tuple[bytes, str]:
    catalog = await _load_catalog(db, catalog_id)
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM for Excel compatibility.
    writer = csv.DictWriter(buf, fieldnames=MEESHO_CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for sku in sorted(catalog.skus, key=lambda s: s.sort_order):
        writer.writerow(_row(catalog, sku))
    data = buf.getvalue().encode("utf-8")
    path = f"exports/{catalog.user_id}/{catalog.id}.csv"

    storage = get_storage()
    url = await storage.upload(data, path, content_type="text/csv")
    signed = await storage.get_signed_url(path, expiry_minutes=60)

    db.add(Export(user_id=catalog.user_id, catalog_id=catalog.id, export_type="csv", file_url=url))
    await db.commit()
    return data, signed


async def generate_images_zip(db: AsyncSession, catalog_id: uuid.UUID) -> tuple[bytes, str]:
    catalog = await _load_catalog(db, catalog_id)

    def _fetch_local(path: str) -> bytes:
        if path.startswith("file://"):
            with open(path[len("file://") :], "rb") as fh:
                return fh.read()
        raise ValueError("not a file:// URL")

    async def _fetch(url: str) -> bytes:
        if url.startswith("file://"):
            return await asyncio.to_thread(_fetch_local, url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        for sku in sorted(catalog.skus, key=lambda s: s.sort_order):
            base = _slug(sku.product_name)
            for idx, image in enumerate(sorted(sku.images, key=lambda i: i.sort_order), start=1):
                target_url = image.processed_url or image.original_url
                if not target_url:
                    continue
                try:
                    content = await _fetch(target_url)
                except Exception as exc:
                    logger.warning(f"Skipping {target_url} in ZIP: {exc}")
                    continue
                zf.writestr(f"{base}_{idx}.jpg", content)
    data = zbuf.getvalue()

    path = f"exports/{catalog.user_id}/{catalog.id}_images.zip"
    storage = get_storage()
    url = await storage.upload(data, path, content_type="application/zip")
    signed = await storage.get_signed_url(path, expiry_minutes=60)

    db.add(Export(user_id=catalog.user_id, catalog_id=catalog.id, export_type="zip", file_url=url))
    await db.commit()
    return data, signed
