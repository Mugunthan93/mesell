"""adapters/gcs.py — Google Cloud Storage transport wrapper (§6.D).

Async surface wrapping the synchronous ``google-cloud-storage`` SDK via
:func:`asyncio.to_thread`.  Four public methods:

* :func:`upload_bytes` — write bytes to ``gs://{bucket}/{path}``
* :func:`download_bytes` — read bytes from ``gs://{bucket}/{path}``
* :func:`generate_signed_url` — issue a v4-signed URL with TTL (default 3600s)
* :func:`delete` — delete the blob at ``gs://{bucket}/{path}``

Credentials
-----------
GCP **Application Default Credentials** sourced from the K3s pod's service
account (the VM SA carries ``storage.objectAdmin`` post-Phase A per
``meesell-infra-builder`` memory).  NO env-injected service-account JSON
in V1; ADC reads from instance metadata.

Path convention (§6.D + ``MVP_ARCH §10.8``)
-------------------------------------------
* Images:  ``meesell-images/{user_id}/{product_id}/{idx}.jpg``
* Exports: ``meesell-exports/{user_id}/{export_id}/sheet.xlsx``
           ``meesell-exports/{user_id}/{export_id}/images.zip``

Signed-URL TTL = 3600 seconds (1 hour) per ``MVP_ARCH §10.8`` —
``settings.GCS_SIGNED_URL_TTL_SECONDS`` is the locked default.

Failure mode
------------
The native ``google-cloud-storage`` SDK handles transient transport
retries internally (built-in exponential backoff for idempotent ops).
Auth failures, bucket-not-found, permission errors, and final-retry
exhaustion are converted to :class:`GcsAdapterError` (HTTP 502 envelope).
Image and export services rely on raised exceptions to set row
``status='failed'`` — the adapter does NOT silently swallow upload
failures.
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
            # ``storage.Client`` reads ADC from environment / instance metadata.
            # ``project`` is wired explicitly so error responses include it
            # rather than the SDK's "unknown" placeholder.
            _client = await asyncio.to_thread(
                storage.Client, project=settings.GCS_PROJECT_ID
            )
    return _client


# Native SDK exceptions worth converting to our typed envelope.
# ``GoogleAPICallError`` is the SDK base class — it covers transient and
# fatal errors after the SDK's internal retry has already given up.
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
    """Upload ``data`` to ``gs://{bucket}/{path}``.  Returns ``gs://`` URI.

    Args:
        path: Object path inside the bucket.  Convention per §6.D.
        data: Object bytes.
        content_type: Mime type (e.g. ``"image/jpeg"``,
            ``"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"``).
        bucket: Bucket name; defaults to ``settings.GCS_BUCKET``.

    Raises:
        GcsAdapterError: On any SDK error after built-in retry exhaustion.
    """
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
    """Issue a v4-signed URL with TTL.

    Default TTL = ``settings.GCS_SIGNED_URL_TTL_SECONDS`` (3600 = 1 h per
    ``MVP_ARCH §10.8``).  Default method = ``"GET"``; ``"PUT"`` reserved
    for V1.5 direct-to-GCS browser uploads.
    """
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
    """Delete the blob at ``gs://{bucket}/{path}``.

    NotFound is converted to :class:`GcsAdapterError` — callers that want
    idempotent delete can catch and ignore.
    """
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
