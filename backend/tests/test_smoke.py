"""End-to-end smoke test with stub data.

Walks a single seller through the entire MeeSell happy path:
  signup → catalog → SKU → image upload → AI patch → QualityGate →
  PriceIntel → CSV export → ZIP export
Every external service is stubbed: OTP uses dev mode, storage uses
LocalStorage, AI fields are set manually (no Gemini call).
"""

import csv
import io
import uuid
import zipfile
from urllib.parse import urlparse

import pytest
from PIL import Image as PILImage


def _jpeg(size=(400, 400), color=(220, 80, 40)) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", size, color).save(buf, "JPEG", quality=85)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_full_seller_journey(client, db_engine):
    phone = f"+9199{uuid.uuid4().int % 10**8:08d}"

    # 1. SIGN UP / LOGIN
    sent = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert sent.status_code == 200
    assert sent.json()["dev_otp"] == "1234"

    verified = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": phone, "otp": "1234"}
    )
    assert verified.status_code == 200
    token = verified.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # /me reflects the freshly created free-plan user.
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["plan"] == "free"

    # 2. CREATE CATALOG
    cat_resp = await client.post(
        "/api/v1/catalogs",
        json={"name": "Diwali Kurtis", "category": "Kurtis"},
        headers=headers,
    )
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    # 3. CREATE SKU
    sku_resp = await client.post(
        f"/api/v1/catalogs/{cat_id}/skus",
        json={
            "product_name": "Cotton Kurti Red",
            "cost_price": 250,
            "selling_price": 599,
            "weight_grams": 480,
            "sizes": "S,M,L",
            "colors": "red",
            "material": "cotton blend",
        },
        headers=headers,
    )
    assert sku_resp.status_code == 201
    sku_id = sku_resp.json()["id"]

    # 4. IMAGE UPLOAD
    upload = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("kurti.jpg", _jpeg(), "image/jpeg")},
    )
    assert upload.status_code == 201
    image_id = upload.json()["id"]

    # 5. STUB AI OUTPUT (worker isn't running in this test).
    patched = await client.put(
        f"/api/v1/skus/{sku_id}",
        headers=headers,
        json={
            "ai_title": "Trendy Cotton Kurti for Women - Red Daily Wear",
            "ai_description": "Soft breathable cotton kurti perfect for office and casual wear. Easy to wash. Stylish round-neck design and straight fit.",
            "ai_keywords": "kurti, women, red kurti, cotton, daily wear, casual, ethnic, indian wear",
            "ai_category": "Kurtis",
            "ai_attributes": {
                "fabric": "cotton blend",
                "fit": "regular",
                "sleeve_length": "3/4th",
                "neck_type": "round",
                "length": "knee",
                "occasion": "casual",
            },
        },
    )
    assert patched.status_code == 200

    # Mark the image as processed (mimics what T06 worker would do).
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        from app.models.image import Image as ImageModel

        await db.execute(
            update(ImageModel)
            .where(ImageModel.id == uuid.UUID(image_id))
            .values(
                bg_removed=True,
                resized=True,
                width=1024,
                height=1024,
                processed_url=upload.json()["original_url"],
            )
        )
        await db.commit()

    # 6. QUALITY GATE
    quality = await client.post(
        f"/api/v1/catalogs/{cat_id}/validate", headers=headers
    )
    assert quality.status_code == 200
    qreport = quality.json()
    assert qreport["passed"] is True, qreport
    assert qreport["score"] == 100

    # 7. PRICING (public, no auth)
    pricing = await client.post(
        "/api/v1/pricing/calculate",
        json={
            "selling_price": 599,
            "cost_price": 250,
            "weight_grams": 480,
            "category": "Kurtis",
        },
    )
    assert pricing.status_code == 200
    pbody = pricing.json()
    assert pbody["net_profit"] == "98.57"
    assert pbody["margin_percent"] == "16.46"

    # 8. CSV EXPORT
    csv_resp = await client.post(
        f"/api/v1/catalogs/{cat_id}/export/meesho-csv", headers=headers
    )
    assert csv_resp.status_code == 200
    csv_url = csv_resp.json()["download_url"]
    # Fetch via test client — /dev-static is served by the in-process app.
    csv_file = await client.get(urlparse(csv_url).path)
    assert csv_file.status_code == 200
    raw = csv_file.content
    assert raw.startswith(b"\xef\xbb\xbf")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    row = next(reader)
    assert row["product_title"].startswith("Trendy Cotton Kurti")

    # 9. ZIP EXPORT
    zip_resp = await client.post(
        f"/api/v1/catalogs/{cat_id}/export/images-zip", headers=headers
    )
    assert zip_resp.status_code == 200
    zip_url = zip_resp.json()["download_url"]
    zip_file = await client.get(urlparse(zip_url).path)
    assert zip_file.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zip_file.content)) as zf:
        names = zf.namelist()
    assert names == ["Cotton_Kurti_Red_1.jpg"]
