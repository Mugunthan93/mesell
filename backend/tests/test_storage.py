"""LocalStorage backend tests + GCSStorage import sanity."""

import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.services.storage import LocalStorage, _guess_content_type


@pytest.mark.asyncio
async def test_upload_returns_file_url_with_readable_contents(tmp_path):
    s = LocalStorage(tmp_path)
    url = await s.upload(b"hello", "originals/u-1/a.jpg")
    # LocalStorage returns an http:// URL served by the /dev-static mount.
    assert url.startswith("http://localhost:8001/dev-static/")
    # Verify the bytes were actually written to the storage root.
    assert (tmp_path / "originals" / "u-1" / "a.jpg").read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_upload_writes_content_type_sidecar(tmp_path):
    s = LocalStorage(tmp_path)
    await s.upload(b"x", "originals/u-1/a.png")
    sidecar = tmp_path / "originals" / "u-1" / "a.png.ct"
    assert sidecar.read_text() == "image/png"


@pytest.mark.asyncio
async def test_explicit_content_type_overrides_inference(tmp_path):
    s = LocalStorage(tmp_path)
    await s.upload(b"x", "exports/u-1/cat.csv", content_type="application/csv")
    sidecar = tmp_path / "exports" / "u-1" / "cat.csv.ct"
    assert sidecar.read_text() == "application/csv"


@pytest.mark.asyncio
async def test_upload_from_file_copies_bytes(tmp_path):
    src = tmp_path / "src.csv"
    src.write_text("a,b\n1,2\n")
    store_root = tmp_path / "store"
    s = LocalStorage(store_root)
    url = await s.upload_from_file(str(src), "exports/u-1/cat.csv")
    # URL is served via /dev-static; check the actual bytes via the storage root.
    assert url.startswith("http://localhost:8001/dev-static/")
    assert (store_root / "exports" / "u-1" / "cat.csv").read_text() == "a,b\n1,2\n"


@pytest.mark.asyncio
async def test_get_signed_url_embeds_expiry(tmp_path):
    s = LocalStorage(tmp_path)
    await s.upload(b"x", "originals/u-1/a.jpg")
    before = int(time.time())
    signed = await s.get_signed_url("originals/u-1/a.jpg", expiry_minutes=15)
    after = int(time.time())
    q = parse_qs(urlparse(signed).query)
    exp = int(q["expires"][0])
    assert before + 15 * 60 <= exp <= after + 15 * 60 + 1


@pytest.mark.asyncio
async def test_delete_removes_object_and_sidecar(tmp_path):
    s = LocalStorage(tmp_path)
    await s.upload(b"x", "originals/u-1/a.jpg")
    await s.delete("originals/u-1/a.jpg")
    assert not (tmp_path / "originals" / "u-1" / "a.jpg").exists()
    assert not (tmp_path / "originals" / "u-1" / "a.jpg.ct").exists()


@pytest.mark.asyncio
async def test_delete_missing_object_is_idempotent(tmp_path):
    s = LocalStorage(tmp_path)
    await s.delete("originals/never-existed.jpg")  # should not raise


@pytest.mark.asyncio
async def test_path_traversal_blocked(tmp_path):
    s = LocalStorage(tmp_path)
    with pytest.raises(ValueError, match="escape"):
        await s.upload(b"x", "../escape.txt")


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a.jpg", "image/jpeg"),
        ("a.JPG", "image/jpeg"),
        ("a.jpeg", "image/jpeg"),
        ("b.PNG", "image/png"),
        ("c.csv", "text/csv"),
        ("d.zip", "application/zip"),
        ("unknown.bin", "application/octet-stream"),
    ],
)
def test_content_type_inference(path, expected):
    assert _guess_content_type(path) == expected


def test_gcsstorage_module_imports_without_google_sdk():
    """Lazy import — module should always be importable; only instantiation requires the SDK."""
    from app.services import storage  # noqa: F401
