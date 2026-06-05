"""Auth flow tests: OTP issuance, verification, JWT, /me."""

import pytest


@pytest.mark.asyncio
async def test_send_otp_validates_phone(client):
    resp = await client.post("/api/v1/auth/otp/send", json={"phone": "9876543210"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_full_login_flow(client):
    phone = "+919999999999"
    resp = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    assert resp.status_code == 200
    assert resp.json()["sent"] is True

    resp = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "1234"})
    assert resp.status_code == 200
    body = resp.json()
    token = body["token"]
    assert token and len(token) > 20
    assert body["user"]["plan"] == "free"

    # /me requires Authorization header.
    bad = await client.get("/api/v1/auth/me")
    assert bad.status_code == 401

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["phone"] == phone


@pytest.mark.asyncio
async def test_wrong_otp_locks_after_three_attempts(client):
    phone = "+918888888888"
    await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    for _ in range(3):
        r = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "0000"})
        assert r.status_code == 401
    # 4th attempt — key already evicted, still 401, but key is gone.
    r = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "1234"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_returning_user_is_deduped(client):
    phone = "+917777777777"
    await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    a = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "1234"})
    await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    b = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "1234"})
    assert a.json()["user"]["id"] == b.json()["user"]["id"]
