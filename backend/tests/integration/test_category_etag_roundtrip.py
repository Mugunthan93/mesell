"""Integration test §9.J integration 3 — ETag round-trip on /categories.

Per BACKEND_ARCHITECTURE.md §9.J integration 3:

    "ETag round-trip — GET ``/categories`` returns ETag ``X``; second
    GET with ``If-None-Match: X`` → 304 Not Modified per §4.D."

End-to-end HTTP test.  Skips when the category router has not been
mounted yet (api-routes-builder dispatched in parallel).
"""

from __future__ import annotations

import hashlib
import json
import os
import time

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

pytestmark = pytest.mark.integration


async def _create_user_via_otp_verify(iam_client) -> tuple[str, str]:
    from app.shared import valkey as _vk_mod

    phone = "+915550000903"
    otp = "555903"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", payload, ex=300)

    resp = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["access_token"], phone


async def _categories_have_rows() -> bool:
    try:
        engine = create_async_engine(
            os.environ["DATABASE_URL"], poolclass=NullPool, echo=False
        )
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1 FROM categories LIMIT 1"))
                return result.first() is not None
        finally:
            await engine.dispose()
    except Exception:
        return False


async def test_categories_etag_roundtrip(iam_client):
    if not await _categories_have_rows():
        pytest.skip("categories not seeded — dev tunnel required")

    access_token, _phone = await _create_user_via_otp_verify(iam_client)
    iam_client.headers["Authorization"] = f"Bearer {access_token}"

    # First GET — expect 200 + ETag header.
    first_resp = await iam_client.get("/api/v1/categories")
    if first_resp.status_code == 404:
        pytest.skip(
            "category router not yet mounted by api-routes-builder dispatch"
        )

    assert first_resp.status_code == 200, first_resp.text
    etag = first_resp.headers.get("etag") or first_resp.headers.get("ETag")
    assert etag is not None, (
        f"ETag header missing on /categories response; headers="
        f"{dict(first_resp.headers)}"
    )

    # Second GET with If-None-Match — expect 304.
    second_resp = await iam_client.get(
        "/api/v1/categories", headers={"If-None-Match": etag}
    )
    assert second_resp.status_code == 304, (
        f"Expected 304 Not Modified, got {second_resp.status_code}: "
        f"{second_resp.text}"
    )
