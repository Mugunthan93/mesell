"""End-to-end export endpoints (CSV + ZIP)."""

import csv
import io
import zipfile
from urllib.parse import urlparse

import pytest


async def _login(client, phone="+919900880077"):
    await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    r = await client.post("/api/v1/auth/verify-otp", json={"phone": phone, "otp": "1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def _seeded_catalog(client, headers):
    cat = await client.post(
        "/api/v1/catalogs", json={"name": "Diwali Kurtis", "category": "Kurtis"}, headers=headers
    )
    cat_id = cat.json()["id"]
    sku = await client.post(
        f"/api/v1/catalogs/{cat_id}/skus",
        json={
            "product_name": "Cotton Kurti Red",
            "cost_price": 250,
            "selling_price": 599,
            "weight_grams": 480,
        },
        headers=headers,
    )
    sku_id = sku.json()["id"]
    await client.put(
        f"/api/v1/skus/{sku_id}",
        headers=headers,
        json={
            "ai_title": "Trendy Cotton Kurti for Women - Daily Wear",
            "ai_description": "Soft cotton kurti for office and casual wear. Easy to wash. Round-neck design.",
            "ai_keywords": "kurti, cotton, women, daily wear, casual",
            "ai_category": "Kurtis",
            "ai_attributes": {"fabric": "cotton blend"},
        },
    )
    return cat_id


@pytest.mark.asyncio
async def test_csv_export_returns_signed_url_with_one_hour_expiry(client):
    headers = await _login(client)
    cat_id = await _seeded_catalog(client, headers)
    r = await client.post(f"/api/v1/catalogs/{cat_id}/export/meesho-csv", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["expiry_minutes"] == 60
    assert "expires=" in urlparse(body["download_url"]).query


@pytest.mark.asyncio
async def test_csv_export_content_round_trip(client):
    headers = await _login(client, phone="+919900880078")
    cat_id = await _seeded_catalog(client, headers)
    r = await client.post(f"/api/v1/catalogs/{cat_id}/export/meesho-csv", headers=headers)
    download = r.json()["download_url"]
    # Fetch via the test client — /dev-static is served by the in-process app.
    file_resp = await client.get(urlparse(download).path)
    assert file_resp.status_code == 200
    raw = file_resp.content
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    row = next(reader)
    assert row["catalog_name"] == "Diwali Kurtis"
    assert row["product_title"].startswith("Trendy Cotton Kurti")


@pytest.mark.asyncio
async def test_zip_export_membership(client):
    headers = await _login(client, phone="+919900880079")
    cat_id = await _seeded_catalog(client, headers)
    # Without any uploaded images the ZIP can still be generated (empty archive).
    r = await client.post(f"/api/v1/catalogs/{cat_id}/export/images-zip", headers=headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_export_requires_ownership(client):
    a_headers = await _login(client, phone="+919900880080")
    cat_id = await _seeded_catalog(client, a_headers)
    b_headers = await _login(client, phone="+919900880081")
    r = await client.post(f"/api/v1/catalogs/{cat_id}/export/meesho-csv", headers=b_headers)
    assert r.status_code in {403, 404}
