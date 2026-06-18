"""google-auth integration test (coordinator-owned, design §H.5).

Full route → service → repository → DB → token-issuance round-trip for
POST /api/v1/auth/google/verify, with ONLY the Google adapter mocked (we
cannot mint a real Google ID-token in CI).  Proves:

* a first Google login creates a Google-only user (phone NULL) and issues an
  access JWT + refresh cookie that participate in the shared FE-D5 session;
* the issued access token authenticates GET /api/v1/auth/me;
* the issued refresh cookie rotates via POST /api/v1/auth/refresh (the
  Google-issued session uses the SAME provider-agnostic refresh path);
* cross-provider linking: a phone user who later Google-verifies the SAME
  verified email resolves to the SAME user_id (auto-link).

DB-fidelity policy (conftest): these tests run ONLY when ``TEST_DATABASE_URL``
is set (CI Gate 4) and auto-skip on a laptop with no provisioned test DB.  The
google-route is flag-gated, so the test mounts ``iam_google_router`` onto the
app and forces ``FEATURE_GOOGLE_AUTH_ENABLED`` true for the duration.

NOTE: the linking-rule matrix + adapter edge cases are unit-covered in
``backend/services/svc-iam/tests/test_service_google.py`` and
``test_adapter_google.py`` (byte-parity twins of the monolith iam code).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.adapters.google import GoogleClaims


def _claims(email, sub):
    return GoogleClaims(sub=sub, email=email, email_verified=True, name="S", picture=None)


@pytest.fixture
def google_client(client, monkeypatch):
    """The standard DB-backed ``client`` with the google_router mounted.

    Mocks the Google adapter so no network/real token is needed; the rest of
    the pipeline (service, repository, DB, token issuance) runs for real.
    """
    from app.modules.iam import iam_google_router
    from app.modules.iam import service as iam_service

    # The app behind ``client`` is the real monolith app; mount the flag-gated
    # router explicitly (the production mount is off by default).
    app = client.app
    if not any(getattr(r, "path", "") == "/api/v1/auth/google/verify" for r in app.routes):
        app.include_router(iam_google_router)
    return client, iam_service, monkeypatch


@pytest.mark.asyncio
async def test_google_first_login_then_me_then_refresh(google_client):
    client, iam_service, monkeypatch = google_client
    monkeypatch.setattr(
        iam_service.google_adapter,
        "verify_id_token",
        AsyncMock(return_value=_claims("newseller@example.com", "g-sub-int-1")),
    )

    # 1. First Google login → 200 + access token + refresh cookie.
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    access = body["access_token"]
    assert access and body["token_type"] == "bearer"
    assert "refresh_token=" in resp.headers.get("set-cookie", "")

    # 2. The access token authenticates /me.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200, me.text
    assert me.json()["phone"] is None  # Google-only user has no phone

    # 3. The refresh cookie rotates via the shared FE-D5 path.
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["access_token"]


@pytest.mark.asyncio
async def test_google_links_to_existing_phone_user_by_email(google_client, db_session):
    """Cross-provider: a phone user + a Google login on the SAME verified email
    resolve to the SAME user_id (auto-link, design §E rule 2)."""
    import uuid
    from datetime import datetime, timezone

    from app.shared.models.user import User

    client, iam_service, monkeypatch = google_client

    # Seed a phone user that already carries the email Google will present.
    shared_email = f"link-{uuid.uuid4().hex[:8]}@example.com"
    phone_user = User(
        phone=f"+9198{uuid.uuid4().int % 100000000:08d}",
        email=shared_email,
        plan="free",
        last_login_at=datetime.now(timezone.utc),
    )
    db_session.add(phone_user)
    await db_session.commit()
    await db_session.refresh(phone_user)
    original_id = phone_user.id

    monkeypatch.setattr(
        iam_service.google_adapter,
        "verify_id_token",
        AsyncMock(return_value=_claims(shared_email, "g-sub-int-link")),
    )

    resp = client.post("/api/v1/auth/google/verify", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text

    # The linked user is the SAME row, now carrying the google_sub.
    await db_session.refresh(phone_user)
    refreshed = await db_session.get(User, original_id)
    assert refreshed is not None
    assert refreshed.google_sub == "g-sub-int-link"
    assert refreshed.phone is not None  # phone preserved
