"""svc-iam google-auth route tests (design §H.3).

Tests POST /api/v1/auth/google/verify against a FastAPI app that mounts the
flag-gated ``google_router`` directly, with the service + valkey dependency
overridden.  Asserts:

* 200 happy path → access_token + token_type + Set-Cookie refresh_token;
* 400 on empty / oversized credential (Pydantic);
* 401 on token-invalid / email-unverified (envelope shape);
* 409 on identity conflict;
* 503 on Google-unavailable;
* flag-off → route not present on the production app.

The service is overridden so no DB / Google network is touched.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import service as iam_service
from app.core.errors import register_error_handlers
from app.domain import VerifyOtpResult
from app.exceptions import (
    GoogleEmailUnverifiedError,
    GoogleIdentityConflictError,
    GoogleTokenInvalidError,
    GoogleUnavailableError,
)
from app.router import google_router
from app.shared.valkey import get_valkey_otp


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(google_router)
    # Override valkey so the route never touches a live Redis.
    app.dependency_overrides[get_valkey_otp] = lambda: AsyncMock()
    return TestClient(app, raise_server_exceptions=False)


def test_google_verify_200_happy_path(client, monkeypatch):
    monkeypatch.setattr(
        iam_service,
        "verify_google_and_issue_tokens",
        AsyncMock(
            return_value=VerifyOtpResult(
                access_token="access.jwt",
                refresh_token="refresh-opaque",
                access_expires_in=900,
                refresh_expires_in=604800,
            )
        ),
    )
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "good.id.token"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"] == "access.jwt"
    assert body["expires_in"] == 900
    assert body["token_type"] == "bearer"
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=refresh-opaque" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie.lower() or "samesite=strict" in set_cookie.lower()


def test_google_verify_400_empty_credential(client):
    resp = client.post("/api/v1/auth/google/verify", json={"credential": ""})
    assert resp.status_code in (400, 422)


def test_google_verify_400_oversized_credential(client):
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "x" * 5000})
    assert resp.status_code in (400, 422)


def test_google_verify_401_token_invalid(client, monkeypatch):
    monkeypatch.setattr(
        iam_service, "verify_google_and_issue_tokens",
        AsyncMock(side_effect=GoogleTokenInvalidError()),
    )
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "bad.token"})
    assert resp.status_code == 401
    assert resp.json()["validation_message_id"] == "auth.google.token_invalid"


def test_google_verify_401_email_unverified(client, monkeypatch):
    monkeypatch.setattr(
        iam_service, "verify_google_and_issue_tokens",
        AsyncMock(side_effect=GoogleEmailUnverifiedError()),
    )
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "unverified.token"})
    assert resp.status_code == 401
    assert resp.json()["validation_message_id"] == "auth.google.email_unverified"


def test_google_verify_409_identity_conflict(client, monkeypatch):
    monkeypatch.setattr(
        iam_service, "verify_google_and_issue_tokens",
        AsyncMock(side_effect=GoogleIdentityConflictError()),
    )
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "conflict.token"})
    assert resp.status_code == 409
    assert resp.json()["validation_message_id"] == "auth.google.identity_conflict"


def test_google_verify_503_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        iam_service, "verify_google_and_issue_tokens",
        AsyncMock(side_effect=GoogleUnavailableError()),
    )
    resp = client.post("/api/v1/auth/google/verify", json={"credential": "any.token"})
    assert resp.status_code == 503
    assert resp.json()["validation_message_id"] == "auth.google.unavailable"


def test_google_verify_route_absent_when_flag_off():
    """The production app (flag default off) must NOT mount the route."""
    from app.main import app as prod_app

    paths = {getattr(r, "path", None) for r in prod_app.routes}
    assert "/api/v1/auth/google/verify" not in paths
