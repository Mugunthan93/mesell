"""Object storage backends.

Two implementations expose the same async interface:

* :class:`GCSStorage` writes to Google Cloud Storage (production, staging).
* :class:`LocalStorage` writes to ``/tmp/meesell`` (development).

The active backend is selected by :func:`get_storage` based on
``settings.APP_ENV``. All public methods are ``async``; blocking SDK / disk
calls are dispatched to a worker thread via :func:`asyncio.to_thread`.

Canonical path conventions::

    originals/{user_id}/{image_id}.jpg
    processed/{user_id}/{image_id}.jpg
    exports/{user_id}/{catalog_id}.csv
    exports/{user_id}/{catalog_id}_images.zip
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import shutil
import time
from datetime import timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from app.config import settings

logger = logging.getLogger(__name__)


_EXT_CONTENT_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".csv": "text/csv",
    ".zip": "application/zip",
}


def _guess_content_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return _EXT_CONTENT_TYPE.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"


class Storage(Protocol):
    async def upload(self, file_bytes: bytes, path: str, content_type: str | None = None) -> str: ...
    async def upload_from_file(self, file_path: str, gcs_path: str) -> str: ...
    async def get_signed_url(self, path: str, expiry_minutes: int = 60) -> str: ...
    async def delete(self, path: str) -> None: ...


class GCSStorage:
    """Google Cloud Storage backend."""

    def __init__(self, bucket_name: str | None = None, project_id: str | None = None):
        # Lazy import so dev mode does not require google-cloud-storage at all.
        from google.cloud import storage  # type: ignore

        self._client = storage.Client(project=project_id or settings.GCS_PROJECT_ID or None)
        self._bucket = self._client.bucket(bucket_name or settings.GCS_BUCKET)

    def _public_url(self, path: str) -> str:
        return f"https://storage.googleapis.com/{self._bucket.name}/{quote(path)}"

    async def upload(
        self, file_bytes: bytes, path: str, content_type: str | None = None
    ) -> str:
        ct = content_type or _guess_content_type(path)

        def _do():
            blob = self._bucket.blob(path)
            blob.upload_from_string(file_bytes, content_type=ct)
            return self._public_url(path)

        url = await asyncio.to_thread(_do)
        logger.info(f"GCS upload: {path} ({len(file_bytes)} bytes, {ct})")
        return url

    async def upload_from_file(self, file_path: str, gcs_path: str) -> str:
        ct = _guess_content_type(gcs_path)

        def _do():
            blob = self._bucket.blob(gcs_path)
            blob.upload_from_filename(file_path, content_type=ct)
            return self._public_url(gcs_path)

        url = await asyncio.to_thread(_do)
        logger.info(f"GCS upload_from_file: {file_path} -> {gcs_path}")
        return url

    async def get_signed_url(self, path: str, expiry_minutes: int = 60) -> str:
        def _do():
            blob = self._bucket.blob(path)
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiry_minutes),
                method="GET",
            )

        return await asyncio.to_thread(_do)

    async def delete(self, path: str) -> None:
        def _do():
            blob = self._bucket.blob(path)
            blob.delete()

        await asyncio.to_thread(_do)
        logger.info(f"GCS delete: {path}")


class LocalStorage:
    """Filesystem-backed storage for development.

    Files live under ``root`` (default ``/tmp/meesell``). ``upload`` returns a
    ``file://`` URL pointing at the on-disk path; ``get_signed_url`` returns
    that same URL with an ``?expires=<unix_ts>`` query parameter so callers
    can verify expiry behavior end to end.
    """

    def __init__(self, root: str | Path = "/tmp/meesell"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _abs(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not str(target).startswith(str(self.root.resolve())):
            raise ValueError(f"Path escapes storage root: {path}")
        return target

    def _url(self, path: str) -> str:
        return f"file://{self._abs(path)}"

    async def upload(
        self, file_bytes: bytes, path: str, content_type: str | None = None
    ) -> str:
        ct = content_type or _guess_content_type(path)

        def _do():
            target = self._abs(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file_bytes)
            # Sidecar for content-type round-trip parity with GCS metadata.
            target.with_suffix(target.suffix + ".ct").write_text(ct)

        await asyncio.to_thread(_do)
        logger.info(f"Local upload: {path} ({len(file_bytes)} bytes, {ct})")
        return self._url(path)

    async def upload_from_file(self, file_path: str, gcs_path: str) -> str:
        def _do():
            target = self._abs(gcs_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file_path, target)
            target.with_suffix(target.suffix + ".ct").write_text(_guess_content_type(gcs_path))

        await asyncio.to_thread(_do)
        logger.info(f"Local upload_from_file: {file_path} -> {gcs_path}")
        return self._url(gcs_path)

    async def get_signed_url(self, path: str, expiry_minutes: int = 60) -> str:
        expires = int(time.time()) + expiry_minutes * 60
        return f"{self._url(path)}?expires={expires}"

    async def delete(self, path: str) -> None:
        def _do():
            target = self._abs(path)
            target.unlink(missing_ok=True)
            target.with_suffix(target.suffix + ".ct").unlink(missing_ok=True)

        await asyncio.to_thread(_do)
        logger.info(f"Local delete: {path}")


_storage: Storage | None = None


def get_storage() -> Storage:
    """Return the active storage backend (cached, picked by APP_ENV)."""
    global _storage
    if _storage is None:
        _storage = LocalStorage() if settings.is_dev else GCSStorage()
        logger.info(f"Storage backend: {type(_storage).__name__}")
    return _storage
