"""QualityGate engine: each rule and overall scoring."""

import pytest
from sqlalchemy import select

from app.models.catalog import Catalog
from app.models.image import Image
from app.models.sku import SKU
from app.models.user import User
from app.services.quality_engine import QualityEngine, PASS_SCORE_THRESHOLD


async def _seed_catalog(db, *, category="Kurtis", with_images=True, perfect=True):
    user = User(phone=f"+9190{(hash(category) & 0xFFFFFFFF) % 10**9:09d}", plan="free")
    db.add(user)
    await db.flush()
    catalog = Catalog(user_id=user.id, name="Test", category=category, status="generated")
    db.add(catalog)
    await db.flush()
    sku = SKU(
        catalog_id=catalog.id,
        product_name="Saree A",
        ai_title="Beautiful Cotton Kurti for Women Daily Wear" if perfect else "kurti",
        ai_description=(
            "Soft cotton kurti suitable for office and casual wear. Easy to wash and breathable fabric. "
            "Comfortable fit and elegant design for daily wear."
        ) if perfect else "Short.",
        ai_keywords="kurti, women, cotton, casual, daily wear, ethnic, indian, comfortable" if perfect else "k,k",
        ai_category=category,
        ai_attributes=(
            {
                "fabric": "cotton blend", "fit": "regular", "sleeve_length": "3/4th",
                "neck_type": "round", "length": "knee", "occasion": "casual",
            }
            if perfect
            else {}
        ),
    )
    db.add(sku)
    await db.flush()
    if with_images:
        db.add(Image(
            sku_id=sku.id,
            original_url="file:///tmp/x.jpg",
            processed_url="file:///tmp/p.jpg" if perfect else None,
            bg_removed=perfect,
            resized=perfect,
            width=1024 if perfect else 400,
            height=1024 if perfect else 400,
            has_watermark=False,
        ))
    await db.commit()
    return catalog


@pytest.mark.asyncio
async def test_clean_catalog_passes(db_session):
    catalog = await _seed_catalog(db_session, perfect=True)
    report = await QualityEngine(db_session).validate_catalog(catalog.id)
    failed = [c.name for c in report.checks if c.status == "fail"]
    assert failed == [], f"unexpected failures: {failed}"
    assert report.passed is True
    assert report.score >= PASS_SCORE_THRESHOLD


@pytest.mark.asyncio
async def test_banned_word_fails_catalog(db_session):
    catalog = await _seed_catalog(db_session, perfect=True)
    sku = (await db_session.execute(select(SKU).where(SKU.catalog_id == catalog.id))).scalar_one()
    sku.ai_title = "Premium Nike-style Kurti for Women Daily Wear"
    await db_session.commit()
    report = await QualityEngine(db_session).validate_catalog(catalog.id)
    banned = next(c for c in report.checks if c.name == "banned_words")
    assert banned.status == "fail"
    assert report.passed is False


@pytest.mark.asyncio
async def test_bad_image_size_fails(db_session):
    catalog = await _seed_catalog(db_session, perfect=False)
    report = await QualityEngine(db_session).validate_catalog(catalog.id)
    rule = next(c for c in report.checks if c.name == "image_size")
    assert rule.status == "fail"
    assert report.passed is False


@pytest.mark.asyncio
async def test_unknown_category_fails(db_session):
    catalog = await _seed_catalog(db_session, category="Quantum Foam", perfect=True)
    report = await QualityEngine(db_session).validate_catalog(catalog.id)
    rule = next(c for c in report.checks if c.name == "category_mapping")
    assert rule.status == "fail"


@pytest.mark.asyncio
async def test_required_attributes_fails_when_missing(db_session):
    catalog = await _seed_catalog(db_session, perfect=True)
    sku = (await db_session.execute(select(SKU).where(SKU.catalog_id == catalog.id))).scalar_one()
    sku.ai_attributes = {"fabric": "cotton"}
    await db_session.commit()
    report = await QualityEngine(db_session).validate_catalog(catalog.id)
    rule = next(c for c in report.checks if c.name == "required_attributes")
    assert rule.status == "fail"
