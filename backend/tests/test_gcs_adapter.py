"""Unit tests for ``app.adapters.gcs`` (§6.D + §6.G).

Verifies the locked path convention from ``MVP_ARCH §10.8``:
``meesell-images/{user_id}/{product_id}/{idx}.jpg`` for images;
``meesell-exports/{user_id}/{export_id}/sheet.xlsx`` for exports.

Signed-URL TTL default = 3600 s (1 h) per ``MVP_ARCH §10.8``.

Mocks the per-method ``_*_sync`` helpers — the SDK is never invoked.
"""

from __future__ import annotations

import inspect

import pytest
from google.api_core import exceptions as gcore_exc

from app.adapters import AdapterError, GcsAdapterError
from app.adapters import gcs as gcs_mod
from app.core.errors import MeesellError
from app.shared.config import settings


@pytest.fixture(autouse=True)
def _reset_module():
    gcs_mod._reset_for_testing()
    # Install a sentinel client so _get_client() returns immediately without
    # hitting ADC.  The sync helpers are monkeypatched per test so the value
    # is never actually used by SDK calls.
    gcs_mod._client = object()  # type: ignore[assignment]
    yield
    gcs_mod._reset_for_testing()


# ── Exception hierarchy ────────────────────────────────────────────────────
def test_gcs_adapter_error_is_meesell_error():
    assert issubclass(GcsAdapterError, AdapterError)
    assert issubclass(GcsAdapterError, MeesellError)
    assert GcsAdapterError().status_code == 502
    assert GcsAdapterError().validation_message_id == "gcs.unavailable"


# ── upload_bytes ───────────────────────────────────────────────────────────
async def test_upload_bytes_happy_path(monkeypatch):
    """upload_bytes returns gs:// URI and forwards all args to the SDK."""
    captured: dict = {}

    def _mock(client, bucket, path, data, content_type):
        captured.update(
            bucket=bucket, path=path, data=data, content_type=content_type
        )
        return f"gs://{bucket}/{path}"

    monkeypatch.setattr(gcs_mod, "_upload_sync", _mock)

    uri = await gcs_mod.upload_bytes(
        path="meesell-images/u-1/p-2/1.jpg",
        data=b"\xff\xd8\xff",
        content_type="image/jpeg",
    )
    assert uri == f"gs://{settings.GCS_BUCKET}/meesell-images/u-1/p-2/1.jpg"
    assert captured["bucket"] == settings.GCS_BUCKET
    assert captured["path"] == "meesell-images/u-1/p-2/1.jpg"
    assert captured["data"] == b"\xff\xd8\xff"
    assert captured["content_type"] == "image/jpeg"


async def test_upload_bytes_uses_image_path_convention(monkeypatch):
    """§6.D path convention: meesell-images/{user_id}/{product_id}/{idx}.jpg."""
    captured_paths: list[str] = []

    def _mock(client, bucket, path, *_):
        captured_paths.append(path)
        return f"gs://{bucket}/{path}"

    monkeypatch.setattr(gcs_mod, "_upload_sync", _mock)
    await gcs_mod.upload_bytes(
        path="meesell-images/aaaa-1111/bbbb-2222/3.jpg",
        data=b"x",
        content_type="image/jpeg",
    )
    assert captured_paths[0] == "meesell-images/aaaa-1111/bbbb-2222/3.jpg"


async def test_upload_bytes_uses_export_path_convention(monkeypatch):
    """§6.D path convention: meesell-exports/{user_id}/{export_id}/sheet.xlsx."""
    captured_paths: list[str] = []

    def _mock(client, bucket, path, *_):
        captured_paths.append(path)
        return f"gs://{bucket}/{path}"

    monkeypatch.setattr(gcs_mod, "_upload_sync", _mock)
    await gcs_mod.upload_bytes(
        path="meesell-exports/aaaa-1111/cccc-3333/sheet.xlsx",
        data=b"PK\x03\x04",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert captured_paths[0] == "meesell-exports/aaaa-1111/cccc-3333/sheet.xlsx"


async def test_upload_bytes_raises_gcs_adapter_error_on_forbidden(monkeypatch):
    """Forbidden → GcsAdapterError, not silent swallow per §6.D failure mode."""
    def _mock(*_args, **_kwargs):
        raise gcore_exc.Forbidden("permission denied")

    monkeypatch.setattr(gcs_mod, "_upload_sync", _mock)
    with pytest.raises(GcsAdapterError):
        await gcs_mod.upload_bytes(
            path="meesell-images/x/y/1.jpg", data=b"x", content_type="image/jpeg"
        )


async def test_upload_bytes_raises_on_generic_api_error(monkeypatch):
    """GoogleAPICallError (parent class) → GcsAdapterError."""
    def _mock(*_args, **_kwargs):
        raise gcore_exc.GoogleAPICallError("generic failure")

    monkeypatch.setattr(gcs_mod, "_upload_sync", _mock)
    with pytest.raises(GcsAdapterError):
        await gcs_mod.upload_bytes(
            path="any/path.jpg", data=b"x", content_type="image/jpeg"
        )


# ── download_bytes ─────────────────────────────────────────────────────────
async def test_download_bytes_happy_path(monkeypatch):
    """download_bytes returns the blob bytes."""
    def _mock(client, bucket, path):
        assert path == "meesell-images/u-1/p-2/1.jpg"
        return b"image-bytes"

    monkeypatch.setattr(gcs_mod, "_download_sync", _mock)
    out = await gcs_mod.download_bytes("meesell-images/u-1/p-2/1.jpg")
    assert out == b"image-bytes"


async def test_download_bytes_raises_on_not_found(monkeypatch):
    """NotFound → GcsAdapterError (the adapter does NOT silently return None)."""
    def _mock(*_args, **_kwargs):
        raise gcore_exc.NotFound("missing")

    monkeypatch.setattr(gcs_mod, "_download_sync", _mock)
    with pytest.raises(GcsAdapterError):
        await gcs_mod.download_bytes("missing/path.jpg")


# ── generate_signed_url ────────────────────────────────────────────────────
async def test_signed_url_default_ttl_is_3600(monkeypatch):
    """§10.8 lock: default TTL = settings.GCS_SIGNED_URL_TTL_SECONDS = 3600 s."""
    captured: dict = {}

    def _mock(client, bucket, path, ttl_seconds, method):
        captured.update(ttl_seconds=ttl_seconds, method=method, path=path)
        return f"https://storage.googleapis.com/signed?path={path}&ttl={ttl_seconds}"

    monkeypatch.setattr(gcs_mod, "_sign_sync", _mock)
    url = await gcs_mod.generate_signed_url("meesell-images/u/p/1.jpg")
    assert captured["ttl_seconds"] == 3600
    assert captured["method"] == "GET"
    assert "signed" in url


async def test_signed_url_custom_ttl(monkeypatch):
    """ttl_seconds override propagates."""
    captured: dict = {}

    def _mock(client, bucket, path, ttl_seconds, method):
        captured.update(ttl_seconds=ttl_seconds, method=method)
        return "url"

    monkeypatch.setattr(gcs_mod, "_sign_sync", _mock)
    await gcs_mod.generate_signed_url("any/path.jpg", ttl_seconds=300)
    assert captured["ttl_seconds"] == 300


async def test_signed_url_put_method(monkeypatch):
    """method='PUT' reserved for V1.5 direct-upload — supported."""
    captured: dict = {}

    def _mock(client, bucket, path, ttl_seconds, method):
        captured.update(method=method)
        return "url"

    monkeypatch.setattr(gcs_mod, "_sign_sync", _mock)
    await gcs_mod.generate_signed_url("any/path", method="PUT")
    assert captured["method"] == "PUT"


async def test_signed_url_raises_on_sdk_error(monkeypatch):
    """SDK error → GcsAdapterError."""
    def _mock(*_args, **_kwargs):
        raise gcore_exc.Unauthorized("bad creds")

    monkeypatch.setattr(gcs_mod, "_sign_sync", _mock)
    with pytest.raises(GcsAdapterError):
        await gcs_mod.generate_signed_url("any/path.jpg")


# ── delete ─────────────────────────────────────────────────────────────────
async def test_delete_happy_path(monkeypatch):
    """delete returns None on success."""
    called = {"n": 0}

    def _mock(client, bucket, path):
        called["n"] += 1
        assert path == "meesell-images/u/p/1.jpg"

    monkeypatch.setattr(gcs_mod, "_delete_sync", _mock)
    result = await gcs_mod.delete("meesell-images/u/p/1.jpg")
    assert result is None
    assert called["n"] == 1


async def test_delete_raises_on_not_found(monkeypatch):
    """NotFound is converted (callers wanting idempotent delete catch + ignore)."""
    def _mock(*_args, **_kwargs):
        raise gcore_exc.NotFound("already gone")

    monkeypatch.setattr(gcs_mod, "_delete_sync", _mock)
    with pytest.raises(GcsAdapterError):
        await gcs_mod.delete("missing/path.jpg")


# ── Settings sourcing ─────────────────────────────────────────────────────
async def test_bucket_override_propagates(monkeypatch):
    """Explicit bucket arg overrides settings.GCS_BUCKET."""
    captured: dict = {}

    def _mock(client, bucket, path, data, content_type):
        captured["bucket"] = bucket
        return f"gs://{bucket}/{path}"

    monkeypatch.setattr(gcs_mod, "_upload_sync", _mock)
    await gcs_mod.upload_bytes(
        path="a/b/c.jpg",
        data=b"x",
        content_type="image/jpeg",
        bucket="override-bucket",
    )
    assert captured["bucket"] == "override-bucket"


# ── Boundary discipline ───────────────────────────────────────────────────
def test_no_os_getenv_in_gcs():
    """§6.G — credentials via settings only."""
    src = inspect.getsource(gcs_mod)
    assert "os.getenv" not in src


def test_no_business_logic_in_gcs():
    """Adapter does not import from app.modules.*"""
    src = inspect.getsource(gcs_mod)
    assert "from app.modules" not in src
    assert "import app.modules" not in src
