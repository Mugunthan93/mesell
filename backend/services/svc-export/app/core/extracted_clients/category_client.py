"""category-svc HTTP shim — re-exports the ``category_service`` symbol surface.

Shims 2 of the 6 cross-module methods export consumes (spec §0.4):

* :func:`fetch_schema` ← category/service.py:467
  → ``GET /internal/categories/{id}/schema`` (returns the §5A.B 7-key
  envelope dict).
* :func:`get_field_enum` ← category/service.py:491
  → ``GET /internal/categories/{id}/field-enum/{field}`` (returns the enum
  payload dict).

Also re-exports :class:`CategoryNotFoundError` + :class:`FieldEnumNotFoundError`
because the export pipeline's ``_translate_enums`` step imports and catches
them (monolith imported them from ``app.modules.category.exceptions``; in
svc-export that import line is rewritten to this shim — both are HTTP 404
contract responses from the field-enum route).

``fetch_schema`` accepts ``db=`` and ``get_field_enum`` accepts a positional
``db`` (matching ``service.py`` call sites ``fetch_schema(category_id, db=db)``
and ``get_field_enum(category_id, col.canonical_name, db)``).  ``db`` is
accepted + IGNORED (HTTP shim).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json


# ── Typed errors raised on the monolith's 4xx contract responses ────────────
class CategoryNotFoundError(MeesellError):
    """Mirror of ``category.exceptions.CategoryNotFoundError`` — 404."""

    code = "category.not_found"
    status_code = 404
    validation_message_id = "category.lookup.not_found"

    def __init__(self, detail: str = "Category not found.") -> None:
        super().__init__(detail=detail)


class FieldEnumNotFoundError(MeesellError):
    """Mirror of ``category.exceptions.FieldEnumNotFoundError`` — 404.

    Raised when a field has no enum (free-text field).  The export pipeline
    catches this and passes the value through untranslated.
    """

    code = "category.field_enum_not_found"
    status_code = 404
    validation_message_id = "category.field_enum.not_found"

    def __init__(self, detail: str = "Field enum not found.") -> None:
        super().__init__(detail=detail)


# ── Shimmed methods (re-export the category_service symbol surface) ─────────
async def fetch_schema(
    category_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> dict:
    """Category schema envelope ← ``GET /internal/categories/{id}/schema``."""
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/categories/{category_id}/schema",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise CategoryNotFoundError() from exc
        raise
    return dict(payload)


async def get_field_enum(
    category_id: UUID,
    field_name: str,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> dict[str, Any]:
    """Field enum payload ← ``GET /internal/categories/{id}/field-enum/{field}``.

    Raises :class:`FieldEnumNotFoundError` / :class:`CategoryNotFoundError` on
    a 404 contract response (the pipeline catches both and passes the value
    through untranslated).
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/categories/{category_id}/field-enum/{field_name}",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            # The monolith uses one 404 for both not-found conditions; the
            # pipeline catches both identically, so map to FieldEnumNotFoundError.
            raise FieldEnumNotFoundError() from exc
        raise
    return dict(payload)


__all__ = [
    "CategoryNotFoundError",
    "FieldEnumNotFoundError",
    "fetch_schema",
    "get_field_enum",
]
