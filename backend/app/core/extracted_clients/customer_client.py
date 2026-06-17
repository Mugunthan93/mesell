"""Monolith-side REVERSE shim → customer-svc (MS Sub-Plan E, FROZEN contracts).

The monolith ``catalog.service`` is the caller of two customer cross-module
methods (per BACKEND_ARCHITECTURE §8.C / §10):

* ``assert_eligible_for_super_id(user_id, super_id, db)`` — catalog/service.py:406
* ``get_compliance_block(user_id, db)``                   — catalog/service.py:839

AT CUTOVER (founder-gated, NOT this PR) ``catalog/service.py`` flips its
import from::

    from app.modules.customer import service as customer_service

to::

    from app.core.extracted_clients import customer_client as customer_service

This module re-exports the SAME symbol names with the SAME signatures so the
call sites at :406 / :839 are byte-for-byte unchanged (§16.G).

The 2 FROZEN customer-svc contracts honored here
------------------------------------------------
1. ``get_compliance_block`` →
   ``GET customer-svc/internal/seller-profile/{user_id}/compliance-block``
   200 → 10-field :class:`ComplianceBlock` JSON (deserialised into the
   monolith's existing ``app.modules.customer.domain.ComplianceBlock`` —
   attribute access ``.manufacturer_name`` etc. preserved for the catalog
   call site).
   404 → ``customer.profile_not_found`` → re-raised as :class:`ProfileNotFoundError`.

2. ``assert_eligible_for_super_id`` →
   ``GET customer-svc/internal/seller-profile/{user_id}/eligibility?super_id=...``
   200 ``{}`` → returns ``None`` (eligible).
   422 ``customer.profile_incomplete_for_category`` → re-raised as
   :class:`ProfileIncompleteForCategoryError` (with ``super_id`` + ``missing_keys``
   forwarded from the envelope when present).

STRANGLER POSTURE
-----------------
This shim is NOT wired in (the live ``catalog.service`` import is unchanged)
and NOT cut over.  It is additive + hybrid-CI-tested only.  During the hybrid
window the shim base URL points at the customer-svc ClusterIP; before the
service is deployed the in-process customer module remains the live path.

Transport contract (mirrors the svc-side ``_transport`` — spec §5.E)
--------------------------------------------------------------------
* ``httpx.AsyncClient``, 5 s read / 2 s connect timeout.
* EXACTLY ONE retry, ONLY on 503/504 (transient gateway).
* Forward the caller's user JWT (``Authorization: Bearer``) + ``X-Request-ID``
  from the per-request context populated by the monolith request middleware.

Base URL config
---------------
Read from ``CUSTOMER_SVC_BASE_URL`` (default ``http://customer-svc:8001``) via
``os.environ`` — deliberately NOT added to the LOCKED §5.D Settings class
(§7.3: no self-amendment of a LOCKED section).  Wiring the field into Settings
is a cutover-time task flagged in the founder-gate PR body.
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer.domain import ComplianceBlock
from app.modules.customer.exceptions import (
    ProfileIncompleteForCategoryError,
    ProfileNotFoundError,
)

logger = logging.getLogger(__name__)

# ── Per-request propagation context (populated by the monolith request mw) ───
_bearer_token: ContextVar[str | None] = ContextVar(
    "monolith_customer_client_bearer", default=None
)
_request_id: ContextVar[str | None] = ContextVar(
    "monolith_customer_client_request_id", default=None
)

# ── Locked transport config (spec §5.E) ─────────────────────────────────────
_TIMEOUT = httpx.Timeout(timeout=5.0, connect=2.0)  # 5 s read / 2 s connect
_RETRYABLE_STATUSES = frozenset({503, 504})  # ONLY transient gateway codes

_DEFAULT_BASE_URL = "http://customer-svc:8001"


def set_request_context(*, bearer_token: str | None, request_id: str | None) -> None:
    """Populate the per-request propagation context (called by request mw)."""
    _bearer_token.set(bearer_token)
    _request_id.set(request_id)


def _base_url() -> str:
    return os.environ.get("CUSTOMER_SVC_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    token = _bearer_token.get()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    rid = _request_id.get()
    if rid:
        headers["X-Request-ID"] = rid
    return headers


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    """Issue the internal request with the locked transport contract.

    Returns the raw response (callers translate typed 4xx bodies into the
    monolith's own exception types BEFORE ``raise_for_status``).
    """
    url = f"{_base_url()}{path}"
    headers = _headers()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.request(method, url, params=params, headers=headers)
        if response.status_code in _RETRYABLE_STATUSES:
            logger.warning(
                "customer_client: %s %s returned %s — retrying ONCE (transient)",
                method,
                path,
                response.status_code,
            )
            response = await client.request(
                method, url, params=params, headers=headers
            )
    return response


def _envelope_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


# ── Re-exported customer service surface (SAME signatures as the in-process
#    monolith customer.service — §16.G byte-for-byte call-site preservation) ──


async def get_compliance_block(user_id: UUID, db: AsyncSession) -> ComplianceBlock:
    """FROZEN-0A reverse shim of ``customer.service.get_compliance_block``.

    ``db`` is retained in the signature for call-site parity (catalog passes
    ``db=db``) but is unused on the HTTP path — the schema lives in customer-svc.

    Raises :class:`ProfileNotFoundError` on a 404 ``customer.profile_not_found``
    envelope (the exact behavior the in-process method has).
    """
    response = await _request(
        "GET", f"/internal/seller-profile/{user_id}/compliance-block"
    )
    if response.status_code == 404:
        raise ProfileNotFoundError(
            detail="Seller profile not found.",
        )
    response.raise_for_status()
    data = response.json()
    # Deserialise the 10-field JSON into the monolith's ComplianceBlock dataclass
    # so the catalog call site's attribute access (.manufacturer_name etc.) is
    # byte-for-byte unchanged.
    return ComplianceBlock(**data)


async def assert_eligible_for_super_id(
    user_id: UUID,
    super_id: str,
    db: AsyncSession,
) -> None:
    """frozen-0H reverse shim of ``customer.service.assert_eligible_for_super_id``.

    200 ``{}`` → eligible → returns ``None``.
    422 ``customer.profile_incomplete_for_category`` → re-raises
    :class:`ProfileIncompleteForCategoryError` with ``super_id`` + ``missing_keys``
    forwarded from the envelope when the service supplies them.

    ``db`` is retained for call-site parity (catalog passes ``db=db``) but is
    unused on the HTTP path.
    """
    response = await _request(
        "GET",
        f"/internal/seller-profile/{user_id}/eligibility",
        params={"super_id": super_id},
    )
    if response.status_code == 422:
        body = _envelope_body(response)
        raise ProfileIncompleteForCategoryError(
            detail=body.get("detail")
            if isinstance(body.get("detail"), str)
            else (
                "Your seller profile is incomplete for this category. "
                "Please update your profile to list here."
            ),
            super_id=body.get("super_id", super_id),
            missing_keys=body.get("missing_keys"),
        )
    response.raise_for_status()
    return None


__all__ = [
    "set_request_context",
    "get_compliance_block",
    "assert_eligible_for_super_id",
]
