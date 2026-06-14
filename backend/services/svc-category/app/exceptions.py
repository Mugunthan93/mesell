"""``category`` module exceptions — subclasses of :class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §9.G (LOCKED 2026-06-05).

3-segment validation_message_id normalisation (FLAGGED)
-------------------------------------------------------
§9.G prose lists the 4 IDs in 2-segment shorthand (``category.not_found``,
``category.field_enum_not_found``).  However §5A.H locks the registry
regex at ``^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$`` (exactly 3 dot-
separated segments) and the §5A construction dispatch already shipped the
canonical 3-segment variants in :mod:`app.i18n.messages_en`:

================================================  =======  =====================================
Class                                             status   validation_message_id
================================================  =======  =====================================
CategoryError (base)                              —        — (inherits MeesellError defaults)
CategoryNotFoundError                             404      category.lookup.not_found
FieldEnumNotFoundError                            404      category.field_enum.not_found
SuggestQueryInvalidError                          400      validation.suggest_q.too_short_or_long
BrowseQueryInvalidError                           400      validation.browse.invalid_pagination
================================================  =======  =====================================

This matches the §7 iam + §8 customer normalisation precedent (memory D2
and D5 entries).  ESCALATION QUEUED if master prefers updating §5A.H to
permit 2-segment shorthand instead.
"""

from __future__ import annotations

from app.core.errors import MeesellError


class CategoryError(MeesellError):
    """Base class for ``category`` module failures.  Never raised directly."""

    code = "category.base"


class CategoryNotFoundError(CategoryError):
    """Raised when a ``category_id`` is not present in ``categories``.

    Per §9.B.4 / §9.B.5 / §9.C cross-module callers (``catalog`` /
    ``pricing`` / Smart Picker Layer 2 guardrail).
    """

    code = "category.not_found"
    status_code = 404
    validation_message_id = "category.lookup.not_found"

    def __init__(self, detail: str = "Category not found.") -> None:
        super().__init__(detail=detail)


class FieldEnumNotFoundError(CategoryError):
    """Raised when ``(category_id, field_name)`` has no row in ``field_enum_values``.

    Distinct from :class:`CategoryNotFoundError` — the ``category_id`` is
    valid, the field itself does not carry an enum for this category.
    """

    code = "category.field_enum_not_found"
    status_code = 404
    validation_message_id = "category.field_enum.not_found"

    def __init__(
        self,
        detail: str = "Field enum lookup not found for this category.",
    ) -> None:
        super().__init__(detail=detail)


class SuggestQueryInvalidError(CategoryError):
    """Raised when ``GET /api/v1/categories/suggest?q=`` violates the
    1 ≤ len(q.strip()) ≤ 500 contract per §9.B.1 / §9.E ``SuggestQuery``.

    Pydantic normally fires this at schema-construction time; the service-
    layer raise here is a defensive guard for callers that bypass the
    Pydantic boundary (e.g. internal cache pre-warm probes).
    """

    code = "category.suggest_query_invalid"
    status_code = 400
    validation_message_id = "validation.suggest_q.too_short_or_long"

    def __init__(
        self,
        detail: str = "Search query must be between 1 and 500 characters.",
    ) -> None:
        super().__init__(detail=detail)


class BrowseQueryInvalidError(CategoryError):
    """Raised when ``GET /api/v1/categories/browse`` pagination is out of range
    per §9.B.2 / §9.E ``BrowseQuery`` (limit must be 1-100, offset >= 0).
    """

    code = "category.browse_query_invalid"
    status_code = 400
    validation_message_id = "validation.browse.invalid_pagination"

    def __init__(
        self,
        detail: str = (
            "Invalid pagination — limit must be 1-100 and offset >= 0."
        ),
    ) -> None:
        super().__init__(detail=detail)


__all__ = [
    "BrowseQueryInvalidError",
    "CategoryError",
    "CategoryNotFoundError",
    "FieldEnumNotFoundError",
    "SuggestQueryInvalidError",
]
