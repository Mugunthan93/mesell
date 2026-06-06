"""Integration tests for the third-party seams: Gemini, GCS.

NOTE: The MSG91 portion of this file was REMOVED during the §7 iam dispatch
(2026-06-06).  The legacy ``app.services.otp_service.OTPService`` it tested
was deleted in favour of ``app.modules.iam.service`` +
``app.adapters.msg91`` (per BACKEND_ARCHITECTURE.md §6.C + §7.B.1).
The MSG91 adapter is now covered by ``tests/test_msg91_adapter.py``; the
iam wiring around it is covered by ``tests/modules/iam/*`` +
``tests/integration/test_iam_*.py``.

Gemini and GCS coverage below remains in scope until §6A.x ai_ops and
§11 image dispatches re-platform them onto the §6 adapter contracts.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai_engine import GeminiEngine


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
