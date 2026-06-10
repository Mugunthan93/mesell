"""Integration test §9.J integration 2 — Browse → schema → catalog wizard.

Per BACKEND_ARCHITECTURE.md §9.J integration 2:

    "Browse → schema → catalog wizard flow — ``/browse?q=kurti`` returns
    ranked results → seller picks leaf → ``/{id}/schema`` → wizard
    renders per §5A.B."

End-to-end HTTP test.  Skips when the category router has not been
mounted yet (api-routes-builder dispatched in parallel).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


async def _create_user_via_otp_verify(iam_client) -> tuple[str, str]:
    from app.shared import valkey as _vk_mod

    phone = "+915550000902"
    otp = "555902"
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


async def test_browse_to_schema_flow(iam_client):
    if not await _categories_have_rows():
        pytest.skip("categories not seeded — dev tunnel required")

    access_token, _phone = await _create_user_via_otp_verify(iam_client)
    iam_client.headers["Authorization"] = f"Bearer {access_token}"

    # Step 1 — Browse.
    browse_resp = await iam_client.get(
        "/api/v1/categories/browse", params={"q": "kurti", "limit": 5, "offset": 0}
    )
    if browse_resp.status_code == 404:
        pytest.skip(
            "category router not yet mounted by api-routes-builder dispatch"
        )

    assert browse_resp.status_code == 200, browse_resp.text
    body = browse_resp.json()
    assert "results" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert isinstance(body["results"], list)
    if not body["results"]:
        pytest.skip("no browse results for 'kurti' — seed mismatch")

    leaf_id = body["results"][0]["category_id"]
    # Validate it's a UUID we can use.
    UUID(leaf_id)

    # Step 2 — schema fetch.
    schema_resp = await iam_client.get(
        f"/api/v1/categories/{leaf_id}/schema"
    )
    assert schema_resp.status_code == 200, schema_resp.text
    envelope = schema_resp.json()
    assert envelope.get("compliance_shape") in {"standard", "collapsed"}
    assert isinstance(envelope.get("fields"), list)
