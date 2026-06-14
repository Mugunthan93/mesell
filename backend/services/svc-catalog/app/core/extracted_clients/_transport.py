"""Shared HTTP transport for catalog's OUTBOUND extracted_clients shims (recipe §4).

catalog is the FIRST extraction whose outbound shims target REAL sibling pods
(category-svc + customer-svc are extracted pods by MS-5, NOT the monolith).  So
unlike the earlier hybrid-posture services (which all pointed at one
``MONOLITH_INTERNAL_BASE_URL``), catalog's transport takes a PER-CALLEE base URL
— ``CATEGORY_SVC_BASE_URL`` for the 3 category shims and ``CUSTOMER_SVC_BASE_URL``
for the 2 customer shims (SUB_PLAN_0H §H5).

Locked transport contract (merge-gate acceptance — recipe §4):
* ``httpx.AsyncClient`` with timeout = 5 s read / 2 s connect.
* EXACTLY ONE retry, and ONLY on HTTP 503 / 504 (transient gateway).  NO
  retry on 500 or any 4xx (deterministic — retrying masks the real error).
* Forward the caller's user JWT in the ``Authorization`` header and the
  request correlation ID in ``X-Request-ID`` (§5.A line 338 — the callee
  validates the forwarded JWT locally, same as a public request).

JWT / request-id propagation
----------------------------
The catalog ``service.py`` outbound call sites are byte-for-byte preserved and
do NOT pass a JWT — so the shims read the bearer token + request-id from
context-vars populated per-request by
:class:`app.core.middleware.request_context_mw.RequestContextMiddleware`
(API path).  catalog runs NO Celery worker, so there is no worker context path
— but ``set_worker_context`` is retained for transport-contract parity with the
pilot (svc-export) and is harmless.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Per-request propagation context ─────────────────────────────────────────
# Populated by RequestContextMiddleware (API).
_bearer_token: ContextVar[str | None] = ContextVar("svc_catalog_bearer_token", default=None)
_request_id: ContextVar[str | None] = ContextVar("svc_catalog_request_id", default=None)

# ── Locked transport config (recipe §4) ─────────────────────────────────────
_TIMEOUT = httpx.Timeout(timeout=5.0, connect=2.0)  # 5 s read / 2 s connect
_RETRYABLE_STATUSES = frozenset({503, 504})  # ONLY transient gateway codes


def set_request_context(*, bearer_token: str | None, request_id: str | None) -> None:
    """Populate the per-request propagation context.  Called by the API
    middleware on every inbound request.
    """
    _bearer_token.set(bearer_token)
    _request_id.set(request_id)


def set_worker_context(*, request_id: str | None) -> None:
    """Populate the worker propagation context (no JWT).  Retained for
    transport-contract parity; svc-catalog runs no Celery worker so it has no
    call site.
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


async def request_json(
    method: str,
    path: str,
    *,
    base_url: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """Issue an internal HTTP request to a sibling pod and return parsed JSON.

    ``base_url`` is the CALLEE's ClusterIP base (category-svc or customer-svc)
    — catalog targets real sibling pods (NOT the monolith), so each client
    supplies its own callee base URL (SUB_PLAN_0H §H5).

    Applies the locked transport contract: 5 s/2 s timeout, exactly one retry
    on 503/504 only, JWT + X-Request-ID forwarding.  Raises
    :class:`httpx.HTTPStatusError` on a non-2xx final response (the shim
    callers translate the typed 4xx bodies into their own exceptions).
    """
    url = f"{base_url.rstrip('/')}{path}"
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
