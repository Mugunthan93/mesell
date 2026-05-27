"""CSV + ZIP export service."""

import csv
import io
import uuid
import zipfile
from urllib.parse import urlparse

import pytest

from app.models.catalog import Catalog
from app.models.image import Image
from app.models.sku import SKU
from app.models.user import User
from app.services.export_service import (
    MEESHO_CSV_COLUMNS,
    generate_images_zip,
    generate_meesho_csv,
)


async def _seed(db, *, image_payload: bytes | None = None):
    user = User(phone=f"+919{uuid.uuid4().int % 10**10:010d}", plan="free")
    db.add(user)
    await db.flush()
    cat = Catalog(user_id=user.id, name="Diwali Kurtis", category="Kurtis", status="generated")
    db.add(cat)
    await db.flush()
    sku = SKU(
        catalog_id=cat.id,
        product_name="Cotton Kurti Red",
        ai_title="Trendy Cotton Kurti",
        ai_description="Soft cotton kurti for daily wear.",
        ai_keywords="kurti, cotton, women",
        ai_category="Kurtis",
        cost_price=250,
        selling_price=599,
        weight_grams=480,
        sizes="S,M,L",
        colors="red",
        material="cotton blend",
    )
    db.add(sku)
    await db.flush()

    if image_payload is not None:
        from app.services.storage import get_storage
        url = await get_storage().upload(image_payload, f"originals/{user.id}/{sku.id}.jpg", "image/jpeg")
        img = Image(
            sku_id=sku.id,
            original_url=url,
            processed_url=url,  # in dev mode both point at the same file
            bg_removed=True,
            resized=True,
            width=1024,
            height=1024,
        )
        db.add(img)

    await db.commit()
    return cat


@pytest.mark.asyncio
async def test_csv_column_order_matches_meesho_template(db_session):
    cat = await _seed(db_session)
    data, _ = await generate_meesho_csv(db_session, cat.id)
    # UTF-8 BOM for Excel.
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == MEESHO_CSV_COLUMNS
    row = next(reader)
    assert row["product_title"] == "Trendy Cotton Kurti"
    assert row["selling_price"] == "599.00"
    assert row["country_of_origin"] == "India"


@pytest.mark.asyncio
async def test_csv_handles_catalog_without_skus(db_session):
    user = User(phone="+919777000111", plan="free")
    db_session.add(user)
    await db_session.flush()
    cat = Catalog(user_id=user.id, name="Empty", category="Tops", status="draft")
    db_session.add(cat)
    await db_session.commit()
    data, _ = await generate_meesho_csv(db_session, cat.id)
    text = data.decode("utf-8-sig").splitlines()
    assert text[0].split(",")[0] == "catalog_name"
    assert len(text) == 1  # header only


@pytest.mark.asyncio
async def test_csv_signed_url_has_expiry(db_session):
    cat = await _seed(db_session)
    _, signed = await generate_meesho_csv(db_session, cat.id)
    parsed = urlparse(signed)
    assert parsed.scheme in {"file", "https"}
    assert "expires=" in parsed.query


@pytest.mark.asyncio
async def test_zip_uses_product_name_in_filenames(db_session):
    cat = await _seed(db_session, image_payload=b"fake-jpeg-bytes")
    data, _ = await generate_images_zip(db_session, cat.id)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    assert names == ["Cotton_Kurti_Red_1.jpg"]
