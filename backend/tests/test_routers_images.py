"""Image upload, status, and delete endpoints (multipart + ownership + size guards)."""

import io

import pytest
from PIL import Image


async def _login(client, phone="+919000888777"):
    await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    r = await client.post("/api/v1/auth/verify-otp", json={"phone": phone, "otp": "1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def _make_sku(client, headers, category="Kurtis"):
    cat = await client.post("/api/v1/catalogs", json={"name": "C1", "category": category}, headers=headers)
    sku = await client.post(
        f"/api/v1/catalogs/{cat.json()['id']}/skus",
        json={"product_name": "P"},
        headers=headers,
    )
    return cat.json()["id"], sku.json()["id"]


def _jpeg_bytes(size=(200, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 0, 0)).save(buf, "JPEG", quality=85)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_accepts_jpeg(client):
    headers = await _login(client)
    _, sku_id = await _make_sku(client, headers)
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("p.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "processing"
    assert body["original_url"].startswith("http://") or body["original_url"].startswith("https://")


@pytest.mark.asyncio
async def test_upload_rejects_non_image(client):
    headers = await _login(client, phone="+919000888778")
    _, sku_id = await _make_sku(client, headers)
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "Unsupported content type" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_oversize(client):
    headers = await _login(client, phone="+919000888779")
    _, sku_id = await _make_sku(client, headers)
    big = b"\xff" * (10 * 1024 * 1024 + 1)
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 400
    assert "File too large" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(client):
    headers = await _login(client, phone="+919000888780")
    _, sku_id = await _make_sku(client, headers)
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_upload_other_users_sku_404(client):
    a_headers = await _login(client, phone="+919000888781")
    _, sku_id = await _make_sku(client, a_headers)
    b_headers = await _login(client, phone="+919000888782")
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=b_headers,
        files={"file": ("p.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_image_status_endpoint(client):
    headers = await _login(client, phone="+919000888783")
    _, sku_id = await _make_sku(client, headers)
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("p.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    image_id = r.json()["id"]
    status = await client.get(f"/api/v1/images/{image_id}/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["status"] in {"processing", "completed"}


@pytest.mark.asyncio
async def test_delete_image(client):
    headers = await _login(client, phone="+919000888784")
    _, sku_id = await _make_sku(client, headers)
    r = await client.post(
        f"/api/v1/skus/{sku_id}/images",
        headers=headers,
        files={"file": ("p.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    image_id = r.json()["id"]
    d = await client.delete(f"/api/v1/images/{image_id}", headers=headers)
    assert d.status_code == 204
    follow = await client.get(f"/api/v1/images/{image_id}/status", headers=headers)
    assert follow.status_code == 404
