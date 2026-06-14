"""category-svc HTTP shim — re-exports the ``category_service`` symbol surface.

catalog's ``service.py`` imports this module ``as category_service`` so the 8
outbound call sites stay BYTE-FOR-BYTE identical (§16.G).  The 3 shimmed methods
mirror the monolith ``app.modules.category.service`` surface catalog consumes
(SUB_PLAN_0H §H5):

* :func:`assert_category_exists` ← service.py:401 (create_product 404 gate)
  → ``GET /internal/categories/{id}/schema`` used as the EXISTENCE PROBE
  (200 ⇒ exists ⇒ return None; 404 ⇒ CategoryNotFoundError).  See the
  Open-Q #1 resolution note below — category-svc serves ``/schema`` but NOT a
  dedicated ``/exists``, so the schema endpoint is the zero-amendment probe.
* :func:`fetch_schema` ← service.py:463,:506,:620,:800,:962,:1034 (6 sites —
  the autosave HOT PATH, Risk #1)  → ``GET /internal/categories/{id}/schema``
  [MS-A/MS-F FROZEN shim — category-svc serves it from its top-100 pre-warm
  cache, ≥99% hit, so the hot-path hop is ~10 ms cached, not a cold DB read]
* :func:`get_field_enum` ← service.py:309 (autofill enum resolution)
  → ``GET /internal/categories/{id}/field-enum/{field}`` [MS-A/MS-F FROZEN]

Target pod (SUB_PLAN_0H §H5)
----------------------------
catalog is the FIRST extraction whose outbound shims target a REAL sibling pod:
category-svc is an extracted service by MS-5, so these shims point at
``settings.CATEGORY_SVC_BASE_URL`` (the category-svc ClusterIP), NOT the
monolith (unlike the MS-1..4 hybrid-posture shims).

OPEN QUESTION / cross-wave coordination — RESOLVED (SUB_PLAN_0H Open Q #1)
-------------------------------------------------------------------------
``assert_category_exists`` is reached on EVERY ``POST /api/v1/products``
(create_product step 2, service.py:401 — a PUBLIC catalog route), so it MUST
work at runtime.  SUB_PLAN_0F §F4 DEFERRED a dedicated ``/exists`` server shim;
as-built ``feature/microservices-category/svc``'s ``internal_router.py`` serves
``/schema``, ``/field-enum/{field}``, ``/commission``, ``/super-categories`` —
but NOT ``/exists``.

**LEAD MERGE-GATE RULING (Open Q #1, Option (a) — 2026-06-14):** use the
already-served ``GET /internal/categories/{id}/schema`` as the existence probe.
A 200 response ⇒ the category exists ⇒ return None (byte-for-byte parity with
the monolith's None-on-success contract); a 404 ⇒ raise
:class:`CategoryNotFoundError` (the same 404 the monolith raised on miss).  This
requires ZERO category-svc amendment — the schema endpoint already returns the
exact 200/404 split the existence gate needs.  The autosave hot-path
``fetch_schema`` already hits ``/schema`` and is served from category-svc's
top-100 pre-warm cache (≥99% hit), so this probe is also cache-served (~10 ms),
not a cold DB read.  The dedicated ``/exists`` server shim is therefore NOT
required for V1.5 and is dropped from the cross-wave coordination list.

Call-site signature parity
--------------------------
Every method accepts the monolith call-site signature (``db=db`` kwarg or
positional ``db``) — the ``db`` arg is accepted and IGNORED (the shim talks
HTTP, not SQL), so the preserved ``service.py`` call sites are byte-for-byte
unchanged.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json
from app.shared.config import settings


# ── Typed errors raised on the category-svc 4xx contract responses ──────────
class CategoryNotFoundError(MeesellError):
    """Mirror of ``category.exceptions.CategoryNotFoundError`` — 404 on a
    category that does not exist (``GET /internal/categories/{id}/schema``
    existence probe or the ``fetch_schema`` hot path).
    """

    code = "category.lookup.not_found"
    status_code = 404
    validation_message_id = "category.lookup.not_found"

    def __init__(self, detail: str = "Category not found.") -> None:
        super().__init__(detail=detail)


def _base_url() -> str:
    """The category-svc ClusterIP base URL (real sibling pod by MS-5)."""
    return settings.CATEGORY_SVC_BASE_URL


# ── Shimmed methods (re-export the category_service symbol surface) ──────────
async def assert_category_exists(
    category_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> None:
    """Existence gate ← ``GET /internal/categories/{id}/schema`` (Open-Q #1
    Option (a): the schema endpoint IS the existence probe — category-svc serves
    ``/schema`` but not a dedicated ``/exists``).

    A 200 response ⇒ the category exists ⇒ return ``None`` (byte-for-byte parity
    with the monolith ``category.service.assert_category_exists`` None-on-success
    contract — used at service.py:401, reached on every ``POST /products``).
    A 404 ⇒ raise :class:`CategoryNotFoundError` (the same 404 the monolith
    raised on miss).  ZERO category-svc amendment; cache-served (~10 ms).
    """
    import httpx

    try:
        await request_json(
            "GET",
            f"/internal/categories/{category_id}/schema",
            base_url=_base_url(),
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise CategoryNotFoundError() from exc
        raise


async def fetch_schema(
    category_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> dict:
    """Category schema envelope ← ``GET /internal/categories/{id}/schema``.

    Returns the §5A.B schema dict verbatim (the catalog service reads
    ``schema["fields"]``, ``schema["super_id"]``, ``schema["category_path"]``
    etc.).  THE AUTOSAVE HOT PATH (Risk #1) — category-svc serves this from its
    top-100 pre-warm cache (≥99% hit).  Raises :class:`CategoryNotFoundError`
    on a 404 contract response.
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/categories/{category_id}/schema",
            base_url=_base_url(),
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise CategoryNotFoundError() from exc
        raise
    return payload if isinstance(payload, dict) else {}


async def get_field_enum(
    category_id: UUID,
    field_name: str,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> dict[str, Any]:
    """Field-enum lookup ← ``GET /internal/categories/{id}/field-enum/{field}``.

    Returns the FROZEN ``{enum_entries:[{canonical, meesho, labels}], total,
    truncated}`` shape (the catalog service reads
    ``payload["enum_entries"][*]["canonical"]`` in ``_resolve_allowed_enums``).
    Raises :class:`CategoryNotFoundError` on a 404 contract response.
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/categories/{category_id}/field-enum/{field_name}",
            base_url=_base_url(),
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise CategoryNotFoundError() from exc
        raise
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "CategoryNotFoundError",
    "assert_category_exists",
    "fetch_schema",
    "get_field_enum",
]
