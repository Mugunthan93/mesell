"""Catalog and SKU CRUD with ownership guards."""

import pytest


@pytest.mark.asyncio
async def test_catalog_crud_and_ownership(client):
    # Seller A
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919000000001"})
    a = await client.post("/api/v1/auth/verify-otp", json={"phone": "+919000000001", "otp": "1234"})
    a_token = a.json()["token"]
    a_headers = {"Authorization": f"Bearer {a_token}"}

    create = await client.post(
        "/api/v1/catalogs",
        json={"name": "Test Catalog", "category": "Kurtis"},
        headers=a_headers,
    )
    assert create.status_code == 201
    catalog_id = create.json()["id"]

    # Add SKU.
    sku = await client.post(
        f"/api/v1/catalogs/{catalog_id}/skus",
        json={"product_name": "Saree", "selling_price": 599, "cost_price": 250},
        headers=a_headers,
    )
    assert sku.status_code == 201

    # List filtered by status.
    listed = await client.get("/api/v1/catalogs?status=draft&page=1&limit=10", headers=a_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    # Get detail includes nested SKUs.
    detail = await client.get(f"/api/v1/catalogs/{catalog_id}", headers=a_headers)
    assert detail.status_code == 200
    assert len(detail.json()["skus"]) == 1

    # Seller B cannot see seller A's catalog.
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919000000002"})
    b = await client.post("/api/v1/auth/verify-otp", json={"phone": "+919000000002", "otp": "1234"})
    b_headers = {"Authorization": f"Bearer {b.json()['token']}"}

    forbidden = await client.get(f"/api/v1/catalogs/{catalog_id}", headers=b_headers)
    assert forbidden.status_code == 403

    # Soft delete.
    deleted = await client.delete(f"/api/v1/catalogs/{catalog_id}", headers=a_headers)
    assert deleted.status_code == 204
    after = await client.get(f"/api/v1/catalogs/{catalog_id}", headers=a_headers)
    assert after.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client):
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919000000003"})
    auth = await client.post("/api/v1/auth/verify-otp", json={"phone": "+919000000003", "otp": "1234"})
    headers = {"Authorization": f"Bearer {auth.json()['token']}"}
    for i in range(7):
        await client.post(
            "/api/v1/catalogs", json={"name": f"C{i}", "category": "Tops"}, headers=headers
        )
    page1 = await client.get("/api/v1/catalogs?page=1&limit=3", headers=headers)
    page2 = await client.get("/api/v1/catalogs?page=2&limit=3", headers=headers)
    assert page1.status_code == page2.status_code == 200
    assert page1.json()["total"] == 7
    assert len(page1.json()["data"]) == 3
    assert len(page2.json()["data"]) == 3
    assert {c["id"] for c in page1.json()["data"]} & {c["id"] for c in page2.json()["data"]} == set()
