"""Shared HTTP transport for the 4 extracted_clients shims (spec §5.E).

Locked transport contract (merge-gate acceptance — spec §3.A):
* ``httpx.AsyncClient`` with timeout = 5 s read / 2 s connect.
* EXACTLY ONE retry, and ONLY on HTTP 503 / 504 (transient gateway).  NO
  retry on 500 or any 4xx (those are deterministic — retrying is pointless
  and masks the real error).
* Forward the caller's user JWT in the ``Authorization`` header and the
  request correlation ID in ``X-Request-ID``.

JWT / request-id propagation
----------------------------
The export ``service.py`` call sites are byte-for-byte preserved and do NOT
pass a JWT — so the shims read the bearer token + request-id from
context-vars populated per-request by
:class:`app.core.middleware.request_context_mw.RequestContextMiddleware`
(API path) or by ``set_worker_context`` (Celery worker path, where the task
re-asserts the principal).  In the worker path the JWT context-var may be
empty; the shim still forwards ``X-Request-ID`` and relies on the monolith's
internal-network trust boundary for the ``/internal/*`` routes.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

import httpx

from app.shared.config import settings

logger = logging.getLogger(__name__)

# ── Per-request propagation context ─────────────────────────────────────────
# Populated by RequestContextMiddleware (API) or set_worker_context (worker).
_bearer_token: ContextVar[str | None] = ContextVar("svc_export_bearer_token", default=None)
_request_id: ContextVar[str | None] = ContextVar("svc_export_request_id", default=None)

# ── Locked transport config (spec §5.E) ─────────────────────────────────────
_TIMEOUT = httpx.Timeout(timeout=5.0, connect=2.0)  # 5 s read / 2 s connect
_RETRYABLE_STATUSES = frozenset({503, 504})  # ONLY transient gateway codes


def set_request_context(*, bearer_token: str | None, request_id: str | None) -> None:
    """Populate the per-request propagation context.  Called by the API
    middleware on every inbound request.
    """
    _bearer_token.set(bearer_token)
    _request_id.set(request_id)


def set_worker_context(*, request_id: str | None) -> None:
    """Populate the worker propagation context (no JWT — internal-network
    trust for the ``/internal/*`` routes).  Called from the Celery task path.
    """
    _bearer_token.set(None)
    _request_id.set(request_id)


def _build_headers() -> dict[str, str]:
    """Assemble the forwarded headers: Authorization (if present) + X-Request-ID."""
    headers: dict[str, str] = {}
    token = _bearer_token.get()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    rid = _request_id.get()
    if rid:
        headers["X-Request-ID"] = rid
    return headers


def _base_url() -> str:
    """The monolith internal base URL (R4 hybrid posture)."""
    return settings.MONOLITH_INTERNAL_BASE_URL.rstrip("/")


async def request_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
    """Issue an internal HTTP request and return the parsed JSON body.

    Applies the locked transport contract: 5 s/2 s timeout, exactly one retry
    on 503/504 only, JWT + X-Request-ID forwarding.  Raises
    :class:`httpx.HTTPStatusError` on a non-2xx final response (the shim
    callers translate the typed 4xx bodies into their own exceptions; an
    unexpected 5xx surfaces as a pipeline failure).
    """
    url = f"{_base_url()}{path}"
    headers = _build_headers()

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # First attempt.
        response = await client.request(method, url, params=params, headers=headers)
        if response.status_code in _RETRYABLE_STATUSES:
            logger.warning(
                "extracted_clients: %s %s returned %s — retrying ONCE (transient)",
                method,
                path,
                response.status_code,
            )
            # EXACTLY ONE retry, ONLY on 503/504.
            response = await client.request(method, url, params=params, headers=headers)

    response.raise_for_status()
    return response.json()


__all__ = [
    "set_request_context",
    "set_worker_context",
    "request_json",
]
