"""Structured error envelope + handler registration.

Vendored from the monolith ``app.core.errors`` (BACKEND_ARCHITECTURE.md §4.F).
Owns ``MeesellError`` (the root every export exception subclasses), the locked
envelope shape, and ``register_error_handlers(app)``.  The i18n resolver is
wired to the vendored ``app.i18n.resolver`` subset.

Envelope (locked, no module customises this shape)::

    {
      "detail": "Human-readable resolved message",
      "code": "machine_readable_slug",
      "validation_message_id": "i18n.lookup.key",
      "request_id": "x-request-id-value"
    }
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
    the i18n resolver lookup misses.
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

    Delegates to :func:`app.i18n.resolver.resolve` per §5A.I.  When the
    resolver returns the message_id verbatim (registry gap), prefer the
    caller's ``fallback`` prose so the envelope's ``detail`` is human-readable.
    Locale is hard-coded to ``"en"`` per V1.
    """
    try:
        resolved = _i18n_resolve(mid, locale="en")
    except Exception as exc:  # pragma: no cover — never block the error path
        logger.warning("i18n resolver failed for %s: %s", mid, exc)
        return fallback if fallback is not None else mid

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
    """Priority 2 — pydantic body/query validation failure → 422."""
    errors = exc.errors()
    first = errors[0] if errors else {"loc": ("_",), "type": "unknown"}
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
    """Priority 3 — framework/legacy HTTPException."""
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

    Full traceback is logged server-side; the response NEVER contains it.
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
    """Register the five handlers on ``app`` in priority order."""
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
