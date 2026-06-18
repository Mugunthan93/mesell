"""svc-iam google-auth service linking-matrix tests (design §H.2).

Tests ``app.service.verify_google_and_issue_tokens`` orchestration by mocking
the adapter (verified claims) and the repository (linking outcome), with a
fakeredis Valkey.  Asserts:

* each linking outcome → tokens issued + the right audit events;
* identity conflict → GoogleIdentityConflictError (no tokens);
* the SAME issuance path as OTP (allowlist key written, correct format);
* IntegrityError race → single retry resolves to login.

No live DB needed — the repository is mocked; the audit write is patched so
no FK to a real users row is required.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from sqlalchemy.exc import IntegrityError

from app import service as iam_service
from app.adapters.google import GoogleClaims
from app.domain import GoogleUpsertOutcome
from app.exceptions import GoogleIdentityConflictError


@pytest.fixture
def valkey():
    return fakeredis.aioredis.FakeRedis(decode_responses=False)


@pytest.fixture
def fake_db():
    db = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _claims(email="seller@example.com", sub="g-sub-123"):
    return GoogleClaims(sub=sub, email=email, email_verified=True, name="S", picture=None)


def _user(phone=None, email="seller@example.com", google_sub="g-sub-123"):
    return SimpleNamespace(
        id=uuid.uuid4(), phone=phone, email=email, google_sub=google_sub, plan="free"
    )


@pytest.fixture(autouse=True)
def _patch_audit(monkeypatch):
    """Patch the direct-ORM audit write so no real users FK is needed."""
    audit = AsyncMock(return_value=1)
    monkeypatch.setattr(iam_service, "_write_audit_direct", audit)
    return audit


@pytest.mark.asyncio
async def test_login_existing_google_user(monkeypatch, valkey, fake_db, _patch_audit):
    """Rule 1: known google_sub → login, tokens issued, login.success audit."""
    user = _user()
    monkeypatch.setattr(iam_service.google_adapter, "verify_id_token", AsyncMock(return_value=_claims()))
    monkeypatch.setattr(
        iam_service.iam_repo,
        "upsert_user_on_google_login",
        AsyncMock(return_value=GoogleUpsertOutcome(user=user, linked=False, created=False, email_changed=False, conflict=False)),
    )
    result = await iam_service.verify_google_and_issue_tokens("cred", "1.2.3.4", fake_db, valkey)
    assert result.access_token
    assert result.refresh_token
    # allowlist entry written under the FE-D5 key format
    keys = [k.decode() if isinstance(k, bytes) else k for k in await valkey.keys("cache:refresh:*")]
    assert keys, "refresh allowlist entry must be written (same path as OTP)"
    events = [c.kwargs["event_type"] for c in _patch_audit.call_args_list]
    assert "auth.login.success" in events
    assert "auth.google.linked" not in events


@pytest.mark.asyncio
async def test_link_phone_user_on_email(monkeypatch, valkey, fake_db, _patch_audit):
    """Rule 2: email matches a phone user → link, auth.google.linked audit."""
    user = _user(phone="+919876543210")
    monkeypatch.setattr(iam_service.google_adapter, "verify_id_token", AsyncMock(return_value=_claims()))
    monkeypatch.setattr(
        iam_service.iam_repo,
        "upsert_user_on_google_login",
        AsyncMock(return_value=GoogleUpsertOutcome(user=user, linked=True, created=False, email_changed=False, conflict=False)),
    )
    result = await iam_service.verify_google_and_issue_tokens("cred", "1.2.3.4", fake_db, valkey)
    assert result.access_token
    events = [c.kwargs["event_type"] for c in _patch_audit.call_args_list]
    assert "auth.login.success" in events
    assert "auth.google.linked" in events


@pytest.mark.asyncio
async def test_create_google_only_user(monkeypatch, valkey, fake_db, _patch_audit):
    """Rule 3: no match → create Google-only user; tokens issued."""
    user = _user(phone=None)
    monkeypatch.setattr(iam_service.google_adapter, "verify_id_token", AsyncMock(return_value=_claims()))
    monkeypatch.setattr(
        iam_service.iam_repo,
        "upsert_user_on_google_login",
        AsyncMock(return_value=GoogleUpsertOutcome(user=user, linked=False, created=True, email_changed=False, conflict=False)),
    )
    result = await iam_service.verify_google_and_issue_tokens("cred", "1.2.3.4", fake_db, valkey)
    assert result.access_token and result.refresh_token


@pytest.mark.asyncio
async def test_identity_conflict_raises_409(monkeypatch, valkey, fake_db, _patch_audit):
    """Edge case 4: email owned by a different google_sub → 409, no tokens."""
    user = _user()
    monkeypatch.setattr(iam_service.google_adapter, "verify_id_token", AsyncMock(return_value=_claims()))
    monkeypatch.setattr(
        iam_service.iam_repo,
        "upsert_user_on_google_login",
        AsyncMock(return_value=GoogleUpsertOutcome(user=user, linked=False, created=False, email_changed=False, conflict=True)),
    )
    with pytest.raises(GoogleIdentityConflictError):
        await iam_service.verify_google_and_issue_tokens("cred", "1.2.3.4", fake_db, valkey)
    # No allowlist entry written on the conflict (fail-closed).
    assert not await valkey.keys("cache:refresh:*")


@pytest.mark.asyncio
async def test_email_changed_logs_audit(monkeypatch, valkey, fake_db, _patch_audit):
    """Edge case 3: returning google_sub with a different token email → email_changed audit."""
    user = _user(email="old@example.com")
    monkeypatch.setattr(iam_service.google_adapter, "verify_id_token", AsyncMock(return_value=_claims(email="new@example.com")))
    monkeypatch.setattr(
        iam_service.iam_repo,
        "upsert_user_on_google_login",
        AsyncMock(return_value=GoogleUpsertOutcome(user=user, linked=False, created=False, email_changed=True, conflict=False)),
    )
    await iam_service.verify_google_and_issue_tokens("cred", "1.2.3.4", fake_db, valkey)
    events = [c.kwargs["event_type"] for c in _patch_audit.call_args_list]
    assert "auth.google.email_changed" in events


@pytest.mark.asyncio
async def test_integrity_race_retries_once(monkeypatch, valkey, fake_db, _patch_audit):
    """Edge case 7: first upsert raises IntegrityError → rollback + retry → login."""
    user = _user()
    monkeypatch.setattr(iam_service.google_adapter, "verify_id_token", AsyncMock(return_value=_claims()))
    upsert = AsyncMock(
        side_effect=[
            IntegrityError("dup", None, Exception("unique violation")),
            GoogleUpsertOutcome(user=user, linked=False, created=False, email_changed=False, conflict=False),
        ]
    )
    monkeypatch.setattr(iam_service.iam_repo, "upsert_user_on_google_login", upsert)
    result = await iam_service.verify_google_and_issue_tokens("cred", "1.2.3.4", fake_db, valkey)
    assert result.access_token
    assert upsert.await_count == 2, "upsert must be retried exactly once"
    fake_db.rollback.assert_awaited_once()
