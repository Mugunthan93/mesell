"""Integration tests for the third-party seams: MSG91, Gemini, GCS.

All three services are mocked. The point is to verify the integration
*surface* of our code — that we send the right payload to MSG91, decode the
right shape from Gemini, and call the right GCS methods — without making any
network calls.
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
import redis.asyncio as redis

from app.services.ai_engine import GeminiEngine
from app.services.otp_service import OTPService


# ============================================================
# MSG91 (OTP SMS)
# ============================================================

@pytest.mark.asyncio
async def test_msg91_dispatched_with_correct_params(monkeypatch):
    """We POST to MSG91 with the configured template, mobile sans '+', and auth key.

    We bypass the dev/production gate by calling ``_dispatch_msg91`` directly —
    that is the unit responsible for the HTTP call, and it works the same way
    regardless of ``APP_ENV``.
    """

    monkeypatch.setattr("app.services.otp_service.settings.MSG91_AUTH_KEY", "test-key")
    monkeypatch.setattr("app.services.otp_service.settings.MSG91_TEMPLATE_ID", "tmpl-1")

    calls = []

    class FakeAsyncClient:
        def __init__(self, *_a, **_kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a, **_kw):
            pass

        async def post(self, url, params=None):
            calls.append((url, params))
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            return resp

    r = redis.from_url("redis://localhost:6381/12", decode_responses=True)
    await r.flushdb()
    try:
        with patch("app.services.otp_service.httpx.AsyncClient", FakeAsyncClient):
            svc = OTPService(r)
            await svc._dispatch_msg91("+919876543210", "5678")
        assert len(calls) == 1
        url, params = calls[0]
        assert url == "https://control.msg91.com/api/v5/otp"
        assert params["mobile"] == "919876543210"   # no leading +
        assert params["template_id"] == "tmpl-1"
        assert params["authkey"] == "test-key"
        assert params["otp"] == "5678"
    finally:
        await r.flushdb()
        await r.aclose()


@pytest.mark.asyncio
async def test_msg91_network_failure_is_swallowed(monkeypatch):
    """A 5xx / connection error from MSG91 must not crash the OTP flow."""

    monkeypatch.setattr("app.services.otp_service.settings.MSG91_AUTH_KEY", "test-key")
    monkeypatch.setattr("app.services.otp_service.settings.MSG91_TEMPLATE_ID", "tmpl-1")

    class ExplodingClient:
        def __init__(self, *_a, **_kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a, **_kw):
            pass

        async def post(self, *_a, **_kw):
            raise httpx.ConnectError("boom")

    r = redis.from_url("redis://localhost:6381/12", decode_responses=True)
    try:
        with patch("app.services.otp_service.httpx.AsyncClient", ExplodingClient):
            svc = OTPService(r)
            await svc._dispatch_msg91("+919876543210", "1234")  # must not raise
    finally:
        await r.aclose()


@pytest.mark.asyncio
async def test_msg91_skipped_when_auth_key_missing(monkeypatch):
    monkeypatch.setattr("app.services.otp_service.settings.MSG91_AUTH_KEY", "")

    calls = []

    class FakeAsyncClient:
        def __init__(self, *_a, **_kw):
            pass

        async def __aenter__(self):
            calls.append("entered")
            return self

        async def __aexit__(self, *_a, **_kw):
            pass

        async def post(self, *_a, **_kw):
            calls.append("posted")
            return MagicMock()

    r = redis.from_url("redis://localhost:6381/12", decode_responses=True)
    try:
        with patch("app.services.otp_service.httpx.AsyncClient", FakeAsyncClient):
            svc = OTPService(r)
            await svc._dispatch_msg91("+919876543210", "1234")
        assert calls == []
    finally:
        await r.aclose()


# ============================================================
# Gemini (AI text generation)
# ============================================================

@pytest.mark.asyncio
async def test_gemini_engine_passes_json_mime_type_and_returns_structured_output():
    """We tell Gemini we want JSON, and we accept the structured response."""

    captured = {}

    payload = {
        "title": "Trendy Cotton Kurti",
        "description": "Soft cotton kurti, breathable, easy wash.",
        "keywords": "kurti, cotton, women",
        "category": "Kurtis",
        "attributes": {"fabric": "cotton", "fit": "regular"},
    }

    class FakeModel:
        def generate_content(self, prompt, generation_config=None, **_):
            captured["prompt"] = prompt
            captured["generation_config"] = generation_config
            return type("R", (), {"text": json.dumps(payload)})

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        out = await engine.generate_listing(
            product_name="Cotton Kurti",
            category="Kurtis",
            material="Cotton",
            sizes="S, M, L",
            colors="red",
            price=599,
        )

    assert captured["generation_config"]["response_mime_type"] == "application/json"
    assert captured["generation_config"]["temperature"] == 0.7
    assert "Cotton Kurti" in captured["prompt"]
    assert out["category"] == "Kurtis"
    assert out["attributes"] == {"fabric": "cotton", "fit": "regular"}


@pytest.mark.asyncio
async def test_gemini_engine_variation_hint_changes_with_index():
    """Two calls with different variation_index should send different hints."""

    seen_prompts = []
    payload = {
        "title": "X",
        "description": "Y" * 50,
        "keywords": "k",
        "category": "Kurtis",
        "attributes": {},
    }

    class FakeModel:
        def generate_content(self, prompt, **_):
            seen_prompts.append(prompt)
            return type("R", (), {"text": json.dumps(payload)})

    engine = GeminiEngine(api_key="dummy")
    with patch.object(engine, "_get_model", return_value=FakeModel()):
        await engine.generate_listing(product_name="X", category="Kurtis", variation_index=0)
        await engine.generate_listing(product_name="X", category="Kurtis", variation_index=1)
        await engine.generate_listing(product_name="X", category="Kurtis", variation_index=2)
    assert "Lead with the fabric" in seen_prompts[0]
    assert "Lead with the style" in seen_prompts[1]
    assert "Lead with the festival" in seen_prompts[2]


# ============================================================
# GCS (object storage)
# ============================================================

def _install_fake_gcs(monkeypatch):
    """Inject a fake google.cloud.storage module that records calls."""

    class FakeBlob:
        def __init__(self, name):
            self.name = name
            self.uploaded = None
            self.deleted = False

        def upload_from_string(self, data, content_type):
            self.uploaded = (bytes(data), content_type)

        def upload_from_filename(self, path, content_type):
            with open(path, "rb") as fh:
                self.uploaded = (fh.read(), content_type)

        def generate_signed_url(self, version, expiration, method):
            return f"https://signed.example/{self.name}?v={version}&exp={expiration.total_seconds()}&m={method}"

        def delete(self):
            self.deleted = True

    class FakeBucket:
        def __init__(self, name):
            self.name = name
            self.blobs = {}

        def blob(self, name):
            return self.blobs.setdefault(name, FakeBlob(name))

    class FakeClient:
        def __init__(self, project=None):
            self.project = project

        def bucket(self, name):
            return FakeBucket(name)

    storage_mod = MagicMock()
    storage_mod.Client = FakeClient
    cloud_mod = MagicMock(storage=storage_mod)
    google_mod = MagicMock(cloud=cloud_mod)

    monkeypatch.setitem(__import__("sys").modules, "google", google_mod)
    monkeypatch.setitem(__import__("sys").modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(__import__("sys").modules, "google.cloud.storage", storage_mod)


@pytest.mark.asyncio
async def test_gcs_upload_writes_correct_blob_and_content_type(monkeypatch):
    _install_fake_gcs(monkeypatch)
    from app.services import storage

    gcs = storage.GCSStorage(bucket_name="meesell-test")
    url = await gcs.upload(b"\x00\x01\x02", "originals/u-1/img-1.jpg")
    assert "meesell-test" in url and "originals/u-1/img-1.jpg" in url

    blob = gcs._bucket.blobs["originals/u-1/img-1.jpg"]   # type: ignore[attr-defined]
    assert blob.uploaded == (b"\x00\x01\x02", "image/jpeg")


@pytest.mark.asyncio
async def test_gcs_signed_url_uses_v4_with_correct_expiry(monkeypatch):
    _install_fake_gcs(monkeypatch)
    from app.services import storage

    gcs = storage.GCSStorage(bucket_name="meesell-test")
    url = await gcs.get_signed_url("originals/u-1/img-1.jpg", expiry_minutes=30)
    assert "v=v4" in url
    assert "exp=1800.0" in url    # 30 min × 60 s
    assert "m=GET" in url


@pytest.mark.asyncio
async def test_gcs_delete_calls_blob_delete(monkeypatch):
    _install_fake_gcs(monkeypatch)
    from app.services import storage

    gcs = storage.GCSStorage(bucket_name="meesell-test")
    await gcs.upload(b"x", "exports/u-1/c.csv")
    await gcs.delete("exports/u-1/c.csv")
    blob = gcs._bucket.blobs["exports/u-1/c.csv"]   # type: ignore[attr-defined]
    assert blob.deleted is True
