"""svc-iam google-auth adapter unit tests (design §H.1).

Covers ``app.adapters.google.verify_id_token``:
* happy path → returns GoogleClaims;
* email_verified=false → GoogleEmailUnverifiedError;
* library ValueError (bad sig/aud/exp) → GoogleTokenInvalidError;
* transport error → GoogleUnavailableError;
* raw credential never logged;
* singleton Request transport reused.

All tests mock ``google.oauth2.id_token.verify_oauth2_token`` — no network.
"""

from __future__ import annotations

import logging

import pytest

from app.adapters import google as google_adapter
from app.exceptions import (
    GoogleEmailUnverifiedError,
    GoogleTokenInvalidError,
    GoogleUnavailableError,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    google_adapter._reset_for_testing()
    yield
    google_adapter._reset_for_testing()


_GOOD_CLAIMS = {
    "sub": "1234567890",
    "email": "seller@example.com",
    "email_verified": True,
    "name": "Test Seller",
    "picture": "https://lh3.googleusercontent.com/x",
}


@pytest.mark.asyncio
async def test_verify_happy_path(monkeypatch):
    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", lambda *a, **k: dict(_GOOD_CLAIMS))
    claims = await google_adapter.verify_id_token("fake.jwt.token")
    assert claims.sub == "1234567890"
    assert claims.email == "seller@example.com"
    assert claims.email_verified is True
    assert claims.name == "Test Seller"
    assert claims.picture == "https://lh3.googleusercontent.com/x"


@pytest.mark.asyncio
async def test_verify_email_unverified_raises(monkeypatch):
    bad = dict(_GOOD_CLAIMS, email_verified=False)
    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", lambda *a, **k: bad)
    with pytest.raises(GoogleEmailUnverifiedError):
        await google_adapter.verify_id_token("fake.jwt.token")


@pytest.mark.asyncio
async def test_verify_email_verified_absent_raises(monkeypatch):
    bad = {k: v for k, v in _GOOD_CLAIMS.items() if k != "email_verified"}
    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", lambda *a, **k: bad)
    with pytest.raises(GoogleEmailUnverifiedError):
        await google_adapter.verify_id_token("fake.jwt.token")


@pytest.mark.asyncio
async def test_verify_value_error_maps_to_token_invalid(monkeypatch):
    def _boom(*a, **k):
        raise ValueError("Wrong audience.")

    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", _boom)
    with pytest.raises(GoogleTokenInvalidError):
        await google_adapter.verify_id_token("fake.jwt.token")


@pytest.mark.asyncio
async def test_verify_transport_error_maps_to_unavailable(monkeypatch):
    from google.auth.exceptions import TransportError

    def _boom(*a, **k):
        raise TransportError("certs endpoint unreachable")

    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", _boom)
    with pytest.raises(GoogleUnavailableError):
        await google_adapter.verify_id_token("fake.jwt.token")


@pytest.mark.asyncio
async def test_missing_sub_raises_token_invalid(monkeypatch):
    bad = dict(_GOOD_CLAIMS, sub="")
    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", lambda *a, **k: bad)
    with pytest.raises(GoogleTokenInvalidError):
        await google_adapter.verify_id_token("fake.jwt.token")


@pytest.mark.asyncio
async def test_raw_credential_never_logged(monkeypatch, caplog):
    secret_token = "SUPER.SECRET.CREDENTIAL.VALUE"

    def _boom(*a, **k):
        raise ValueError("bad sig")

    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", _boom)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(GoogleTokenInvalidError):
            await google_adapter.verify_id_token(secret_token)
    assert secret_token not in caplog.text


@pytest.mark.asyncio
async def test_singleton_request_transport_reused(monkeypatch):
    monkeypatch.setattr(google_adapter.id_token, "verify_oauth2_token", lambda *a, **k: dict(_GOOD_CLAIMS))
    await google_adapter.verify_id_token("a")
    first = google_adapter._request_transport
    await google_adapter.verify_id_token("b")
    second = google_adapter._request_transport
    assert first is second, "Request transport must be a reused singleton"
