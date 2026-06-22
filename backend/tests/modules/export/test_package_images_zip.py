"""PQE Wave A — _package_images_zip unit tests (Wave-1 P1.11 un-skip).

Covers:
  PQE-BE-22  ZIP member structure — 2 refs → ZIP with 2 members named by basename
  PQE-BE-23  empty refs → b""
  PQE-BE-24  per-image download failure → that image skipped, others packed

Previously the Wave-1 test (test_export_zip_member_structure.py) self-skipped
because it assumed a non-existent ``_build_xlsx_bytes`` function.  This file
targets the REAL worker API:

  ``_package_images_zip(image_refs, user_id, db)`` (async, returns bytes)
  ``gcs_adapter.download_bytes`` (mocked — no real GCS call)

All tests are ``unit`` — no DB, no real GCS, no network.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from app.modules.export.service import _package_images_zip


_USER_ID = uuid4()
_SENTINEL_DB = AsyncMock(name="sentinel_db")  # noqa: S106 — not a real credential


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-22  ZIP member structure — 2 refs → 2 members named by basename
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_22_zip_member_names_are_basenames(monkeypatch):
    """_package_images_zip packs 2 image refs; member names are GCS path basenames.

    Arrange: two GCS refs with distinct basenames; stub download_bytes to return
             distinct small byte strings (no real GCS call).
    Act: call _package_images_zip.
    Assert: returned bytes form a valid ZIP; ZIP namelist == ["a.jpg", "b.jpg"].
    """
    from app.modules.export import service as svc

    # Stub: each download returns a small sentinel byte-string.
    download_calls: list[str] = []

    async def fake_download(path: str, **_kwargs) -> bytes:
        download_calls.append(path)
        return b"fake-image-bytes-" + path.encode()

    monkeypatch.setattr(svc.gcs_adapter, "download_bytes", fake_download)

    image_refs = (
        "meesell-images/user1/product1/a.jpg",
        "meesell-images/user1/product1/b.jpg",
    )

    result = await _package_images_zip(
        image_refs=image_refs,
        user_id=_USER_ID,
        db=_SENTINEL_DB,
    )

    assert isinstance(result, bytes) and len(result) > 0, (
        "_package_images_zip must return non-empty bytes for non-empty refs"
    )
    with zipfile.ZipFile(BytesIO(result)) as zf:
        members = sorted(zf.namelist())

    assert members == ["a.jpg", "b.jpg"], (
        f"ZIP member names must be basenames of GCS paths; got {members!r}"
    )
    assert len(download_calls) == 2, (
        f"Expected 2 GCS download calls, got {len(download_calls)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-23  empty refs → b""
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_23_empty_refs_returns_empty_bytes(monkeypatch):
    """_package_images_zip with empty image_refs returns b"".

    No GCS download should be attempted.

    Arrange: stub download_bytes to raise AssertionError if called (sentinel).
    Act: call _package_images_zip with image_refs=().
    Assert: returns b""; no download called.
    """
    from app.modules.export import service as svc

    async def should_not_be_called(path: str, **_kwargs) -> bytes:
        raise AssertionError(
            "_package_images_zip must NOT call download_bytes when image_refs is empty"
        )

    monkeypatch.setattr(svc.gcs_adapter, "download_bytes", should_not_be_called)

    result = await _package_images_zip(
        image_refs=(),
        user_id=_USER_ID,
        db=_SENTINEL_DB,
    )

    assert result == b"", (
        f"Empty image_refs must return b'', got {result!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-24  per-image download failure → that image skipped, others packed
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_24_download_failure_skips_image_others_packed(monkeypatch):
    """A failing download for one ref is logged and skipped; other images packed.

    Arrange: 3 refs; second raises an exception; first and third download normally.
    Act: call _package_images_zip.
    Assert: ZIP contains exactly the first and third basename; no exception raised.
    """
    from app.modules.export import service as svc

    GOOD_REF_1 = "meesell-images/user1/prod/ok_one.jpg"
    BAD_REF = "meesell-images/user1/prod/fail_me.jpg"
    GOOD_REF_2 = "meesell-images/user1/prod/ok_two.png"

    async def fake_download(path: str, **_kwargs) -> bytes:
        if path == BAD_REF:
            raise OSError("simulated GCS failure")
        return b"image-bytes-for-" + path.encode()

    monkeypatch.setattr(svc.gcs_adapter, "download_bytes", fake_download)

    result = await _package_images_zip(
        image_refs=(GOOD_REF_1, BAD_REF, GOOD_REF_2),
        user_id=_USER_ID,
        db=_SENTINEL_DB,
    )

    # Must return non-empty bytes (the 2 good images ARE packed).
    assert isinstance(result, bytes) and len(result) > 0, (
        "Partial failure must not return empty bytes"
    )

    with zipfile.ZipFile(BytesIO(result)) as zf:
        members = sorted(zf.namelist())

    # Only the successful downloads appear in the archive.
    assert members == ["ok_one.jpg", "ok_two.png"], (
        f"ZIP must contain only the successfully downloaded images; got {members!r}"
    )
    assert "fail_me.jpg" not in members, (
        "The failed download must NOT appear in the ZIP"
    )
