"""adapters/gcs.py — Google Cloud Storage transport wrapper (§6.D).

Vendored verbatim from the monolith ``app.adapters.gcs``.  Async surface
wrapping the synchronous ``google-cloud-storage`` SDK via
:func:`asyncio.to_thread`.  Four public methods:

* :func:`upload_bytes` — write bytes to ``gs://{bucket}/{path}``
* :func:`download_bytes` — read bytes from ``gs://{bucket}/{path}``
* :func:`generate_signed_url` — issue a v4-signed URL with TTL (default 3600s)
* :func:`delete` — delete the blob at ``gs://{bucket}/{path}``

Credentials: GCP Application Default Credentials sourced from the K3s pod's
service account.  Signed-URL TTL = ``settings.GCS_SIGNED_URL_TTL_SECONDS``
(3600 = 1 h).  Failures convert to :class:`GcsAdapterError` (HTTP 502).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Literal

from google.api_core import exceptions as gcore_exc
from google.cloud import storage

from app.adapters import GcsAdapterError
from app.shared.config import settings

logger = logging.getLogger(__name__)


# ── Lazy singleton client ──────────────────────────────────────────────────
_client: storage.Client | None = None
_init_lock: asyncio.Lock | None = None


def _get_init_lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


async def _get_client() -> storage.Client:
    """Lazy GCS client — single instance per process.  ADC sourced from metadata."""
    global _client
    if _client is not None:
        return _client
    async with _get_init_lock():
        if _client is None:
            _client = await asyncio.to_thread(
                storage.Client, project=settings.GCS_PROJECT_ID
            )
    return _client


_FATAL_SDK_EXC: tuple[type[BaseException], ...] = (
    gcore_exc.NotFound,
    gcore_exc.Forbidden,
    gcore_exc.Unauthorized,
    gcore_exc.BadRequest,
    gcore_exc.GoogleAPICallError,
)


# ── Public API ─────────────────────────────────────────────────────────────
async def upload_bytes(
    path: str,
    data: bytes,
    content_type: str,
    *,
    bucket: str | None = None,
) -> str:
    """Upload ``data`` to ``gs://{bucket}/{path}``.  Returns ``gs://`` URI."""
    bucket_name = bucket or settings.GCS_BUCKET
    client = await _get_client()
    try:
        return await asyncio.to_thread(
            _upload_sync, client, bucket_name, path, data, content_type
        )
    except _FATAL_SDK_EXC as exc:
        logger.warning("gcs.upload_bytes failed path=%s: %r", path, exc)
        raise GcsAdapterError(
            detail=f"GCS upload failed: {type(exc).__name__}"
        ) from exc


def _upload_sync(
    client: storage.Client,
    bucket_name: str,
    path: str,
    data: bytes,
    content_type: str,
) -> str:
    blob = client.bucket(bucket_name).blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket_name}/{path}"


async def download_bytes(
    path: str,
    *,
    bucket: str | None = None,
) -> bytes:
    """Download bytes from ``gs://{bucket}/{path}``."""
    bucket_name = bucket or settings.GCS_BUCKET
    client = await _get_client()
    try:
        return await asyncio.to_thread(_download_sync, client, bucket_name, path)
    except _FATAL_SDK_EXC as exc:
        logger.warning("gcs.download_bytes failed path=%s: %r", path, exc)
        raise GcsAdapterError(
            detail=f"GCS download failed: {type(exc).__name__}"
        ) from exc


def _download_sync(client: storage.Client, bucket_name: str, path: str) -> bytes:
    blob = client.bucket(bucket_name).blob(path)
    return blob.download_as_bytes()


async def generate_signed_url(
    path: str,
    *,
    bucket: str | None = None,
    ttl_seconds: int | None = None,
    method: Literal["GET", "PUT"] = "GET",
) -> str:
    """Issue a v4-signed URL with TTL (default ``settings.GCS_SIGNED_URL_TTL_SECONDS``)."""
    bucket_name = bucket or settings.GCS_BUCKET
    ttl = (
        ttl_seconds
        if ttl_seconds is not None
        else settings.GCS_SIGNED_URL_TTL_SECONDS
    )
    client = await _get_client()
    try:
        return await asyncio.to_thread(
            _sign_sync, client, bucket_name, path, ttl, method
        )
    except _FATAL_SDK_EXC as exc:
        logger.warning("gcs.generate_signed_url failed path=%s: %r", path, exc)
        raise GcsAdapterError(
            detail=f"GCS sign failed: {type(exc).__name__}"
        ) from exc


def _sign_sync(
    client: storage.Client,
    bucket_name: str,
    path: str,
    ttl_seconds: int,
    method: str,
) -> str:
    blob = client.bucket(bucket_name).blob(path)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=ttl_seconds),
        method=method,
    )


async def delete(path: str, *, bucket: str | None = None) -> None:
    """Delete the blob at ``gs://{bucket}/{path}``."""
    bucket_name = bucket or settings.GCS_BUCKET
    client = await _get_client()
    try:
        await asyncio.to_thread(_delete_sync, client, bucket_name, path)
    except _FATAL_SDK_EXC as exc:
        logger.warning("gcs.delete failed path=%s: %r", path, exc)
        raise GcsAdapterError(
            detail=f"GCS delete failed: {type(exc).__name__}"
        ) from exc


def _delete_sync(client: storage.Client, bucket_name: str, path: str) -> None:
    blob = client.bucket(bucket_name).blob(path)
    blob.delete()


# ── Test helpers ───────────────────────────────────────────────────────────
def _reset_for_testing() -> None:
    """Reset module singletons.  Called from test fixtures only."""
    global _client, _init_lock
    _client = None
    _init_lock = None
