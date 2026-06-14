"""Structured error envelope + handler registration.

Per BACKEND_ARCHITECTURE.md §4.F, this module owns:

1. ``MeesellError`` — the root exception every domain module subclasses.
2. The single, locked **error envelope shape** the whole backend emits.
3. ``register_error_handlers(app)`` — wires 4 handlers (MeesellError,
   pydantic.ValidationError, fastapi.HTTPException, Exception) on a
   FastAPI app, in priority order.

Envelope (locked, no module customises this shape)::

    {
      "detail": "Human-readable resolved message",
      "code": "machine_readable_slug",
      "validation_message_id": "i18n.lookup.key",
      "request_id": "x-request-id-value"
    }

i18n resolver — WIRED (§5A.I)
-----------------------------
``app.i18n.resolver.resolve`` is wired directly. The private helper
:func:`_resolve_message_id` delegates to it and applies the §5A.I locked
fallback contract: locale → en → verbatim ID. When the resolver returns
the message_id verbatim (last-resort tier — registry gap surfaced for
observability), this helper falls back to the caller-supplied
``fallback`` string so the envelope's ``detail`` field carries the
exception's draft prose rather than the lookup key.

Locked rules (§4.F)
-------------------
* Route handlers do NOT format error responses — they raise the appropriate
  exception subclass.
* No module customises the envelope shape.
* The ``request_id`` field is read from ``request.state.request_id`` (set by
  the ``request_id_mw`` middleware — §4.G); when absent (e.g. error fired
  before the middleware ran) the field falls back to ``"unknown"``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


# ── Root exception ─────────────────────────────────────────────────────────
class MeesellError(Exception):
    """Root of every domain/core error envelope.

    Subclasses set class-level defaults for :attr:`code`, :attr:`status_code`,
    and :attr:`validation_message_id`.  ``__init__`` lets a caller override
    any field on a per-instance basis.  ``detail`` is an optional fallback if
    the i18n resolver lookup misses (V1 ships English-only — see deferred
    wire above).

    Example subclass::

        class TenantViolationError(MeesellError):
            code = "tenancy.cross_user_access"
            status_code = 403
            validation_message_id = "tenancy.cross_user_access"
    """

    code: str = "internal.unknown"
    status_code: int = 500
    validation_message_id: str = "server.internal_error"

    def __init__(
        self,
        code: str | None = None,
        status_code: int | None = None,
        validation_message_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        if validation_message_id is not None:
            self.validation_message_id = validation_message_id
        self.detail = detail
        super().__init__(detail or self.code)


# ── i18n resolver (wired — §5A.I) ──────────────────────────────────────────
from app.i18n.resolver import resolve as _i18n_resolve  # noqa: E402


def _resolve_message_id(mid: str, fallback: str | None = None) -> str:
    """Resolve a ``validation_message_id`` to a human string.

    Delegates to :func:`app.i18n.resolver.resolve` per §5A.I. The resolver
    itself implements the locale → en → verbatim fallback chain. When the
    resolver returns the message_id verbatim (registry gap), this helper
    additionally falls back to ``fallback`` — typically the exception's
    draft ``detail`` prose — so the envelope's ``detail`` is always
    human-readable.

    Locale is currently hard-coded to ``"en"`` per V1 (§5A.I item 4 — V1
    logs the ``Accept-Language`` header but always renders English).
    V1.5 will plumb the locale from ``request.state.locale`` set by an
    ``Accept-Language`` middleware.
    """
    try:
        resolved = _i18n_resolve(mid, locale="en")
    except Exception as exc:  # pragma: no cover — defensive, never block error path
        logger.warning("i18n resolver failed for %s: %s", mid, exc)
        return fallback if fallback is not None else mid

    # When the resolver returned the ID verbatim (last-resort tier), prefer
    # the caller's fallback prose if one was supplied.
    if resolved == mid and fallback is not None:
        return fallback
    return resolved


# ── Envelope builder ───────────────────────────────────────────────────────
def _build_envelope(
    request: Request,
    code: str,
    validation_message_id: str,
    detail: str,
) -> dict[str, Any]:
    """Build the locked envelope.  Reads ``request.state.request_id``."""
    request_id = getattr(request.state, "request_id", None) or "unknown"
    return {
        "detail": detail,
        "code": code,
        "validation_message_id": validation_message_id,
        "request_id": request_id,
    }


# ── Handlers ───────────────────────────────────────────────────────────────
async def _meesell_error_handler(
    request: Request, exc: MeesellError
) -> JSONResponse:
    """Priority 1 — every domain/core exception lands here."""
    detail = _resolve_message_id(exc.validation_message_id, fallback=exc.detail)
    envelope = _build_envelope(
        request,
        code=exc.code,
        validation_message_id=exc.validation_message_id,
        detail=detail,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope)


async def _pydantic_validation_handler(
    request: Request,
    exc: PydanticValidationError | RequestValidationError,
) -> JSONResponse:
    """Priority 2 — pydantic body/query validation failure → 422.

    Per MVP_ARCH §5.6.7 convention: ``validation.<field>.<constraint>``.
    The first error in the list drives the envelope; remaining errors are
    surfaced under ``"errors"`` for client-side enumeration.

    Catches both ``fastapi.exceptions.RequestValidationError`` (raised when
    FastAPI validates the request body/query/path) and bare
    ``pydantic.ValidationError`` (raised when service-layer code calls
    ``Model.model_validate(...)`` directly).
    """
    errors = exc.errors()
    first = errors[0] if errors else {"loc": ("_",), "type": "unknown"}
    # loc tuple looks like ("body", "field", "subfield"); drop the source
    # ("body" / "query" / "path") and use the remaining path joined by ".".
    loc = first.get("loc", ()) or ()
    field_path = ".".join(str(p) for p in loc if str(p) not in ("body", "query", "path"))
    field_path = field_path or "_"
    constraint = first.get("type", "unknown")
    mid = f"validation.{field_path}.{constraint}"
    detail = _resolve_message_id(mid, fallback=first.get("msg", "Validation failed"))
    envelope = _build_envelope(
        request,
        code="validation.error",
        validation_message_id=mid,
        detail=detail,
    )
    envelope["errors"] = [
        {
            "field": ".".join(str(p) for p in (e.get("loc") or ()) if str(p) not in ("body", "query", "path")) or "_",
            "constraint": e.get("type", "unknown"),
            "msg": e.get("msg", ""),
        }
        for e in errors
    ]
    return JSONResponse(status_code=422, content=envelope)


async def _http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Priority 3 — framework/legacy HTTPException.

    Envelope ``validation_message_id`` follows the ``http.<status>``
    convention so clients can localise without parsing the detail string.
    """
    mid = f"http.{exc.status_code}"
    detail = _resolve_message_id(mid, fallback=str(exc.detail))
    envelope = _build_envelope(
        request,
        code=f"http.{exc.status_code}",
        validation_message_id=mid,
        detail=detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope,
        headers=getattr(exc, "headers", None) or None,
    )


async def _generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Priority 4 (last resort) — any uncaught exception → 500.

    Full traceback is logged server-side via ``logger.exception``; the
    response NEVER contains the traceback.
    """
    logger.exception(
        "unhandled exception: request_id=%s path=%s",
        getattr(request.state, "request_id", "unknown"),
        request.url.path,
    )
    mid = "server.internal_error"
    detail = _resolve_message_id(mid, fallback="Internal server error")
    envelope = _build_envelope(
        request,
        code="server.internal_error",
        validation_message_id=mid,
        detail=detail,
    )
    return JSONResponse(status_code=500, content=envelope)


# ── Public registration ────────────────────────────────────────────────────
def register_error_handlers(app: FastAPI) -> None:
    """Register the four handlers on ``app`` in priority order.

    Called from ``app/main.py`` after middleware setup.  FastAPI dispatches
    by exception type; registration order is irrelevant to runtime priority,
    but we register here in priority order for code-review readability.
    """
    app.add_exception_handler(MeesellError, _meesell_error_handler)
    app.add_exception_handler(RequestValidationError, _pydantic_validation_handler)
    app.add_exception_handler(PydanticValidationError, _pydantic_validation_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
    logger.info(
        "Registered 5 error handlers (MeesellError, RequestValidationError, "
        "PydanticValidationError, HTTPException, Exception)"
    )


__all__ = [
    "MeesellError",
    "register_error_handlers",
]
