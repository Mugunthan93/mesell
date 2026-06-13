"""Audit middleware — append-only ``public.audit_events`` write after 2xx commit.

Vendored from the monolith ``app.core.middleware.audit_mw`` (§4.G + MVP_ARCH
§11) with the autosave-coalescing branch retained (harmless for export — export
paths never match the autosave regex, so it is a structural copy).

Writes a row IFF response is 2xx AND ``request.state.user_id`` is set AND the
method is a write method.  PII is scrubbed (phone hashed, FSSAI/GST stripped).
Drop-on-failure: audit failure NEVER blocks the response.

NOTE on cross-schema write: ``AuditEvent`` is the vendored model bound to
``public`` (see ``app.shared.models.audit_event``), so the middleware INSERT
lands in ``public.audit_events`` even though svc-export's own table lives in the
``export`` schema.  The ``POST /products/{id}/export-xlsx`` 202 response is a 2xx
write — this middleware emits the request-level ``post./api/v1/...`` audit fact;
the Celery task emits the separate terminal ``export.completed`` /
``export.failed`` rows.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Callable
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.shared.config import settings
from app.shared.database import AsyncSessionLocal
from app.shared.valkey import get_valkey_otp

logger = logging.getLogger(__name__)

# ── Decorators / tags ──────────────────────────────────────────────────────
_AUDIT_EVENT_ATTR = "__audit_event__"

_AUTOSAVE_PATH = re.compile(
    r"^/api/v1/products/[0-9a-fA-F-]+/(draft|autosave)/?$"
)

# ── PII scrubbing constants ────────────────────────────────────────────────
_PII_HASH_KEYS = ("phone",)
_PII_STRIP_KEYS = ("fssai_no", "FSSAI_no", "gst_no", "GST_no")

_COALESCE_WINDOW_SECONDS = 300


def audit_event(event_type: str) -> Callable:
    """Tag a route handler with its canonical audit event type."""

    def deco(fn: Callable) -> Callable:
        setattr(fn, _AUDIT_EVENT_ATTR, event_type)
        return fn

    return deco


# ── PII scrubbing ──────────────────────────────────────────────────────────
def _hash_phone(value: str) -> str:
    """SHA-256(phone + salt) — caller-side hex digest."""
    salt = settings.AUDIT_PII_SALT
    return hashlib.sha256((value + salt).encode()).hexdigest()


def _scrub_pii(payload: dict | None) -> dict | None:
    """Recursively scrub PII in a JSON-like dict (returns a NEW dict)."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        scrubbed = {}
        for k, v in payload.items():
            if k in _PII_STRIP_KEYS:
                continue
            if k.lower() == "phone" and isinstance(v, str):
                scrubbed[k] = _hash_phone(v)
                continue
            scrubbed[k] = _scrub_pii(v) if isinstance(v, (dict, list)) else v
        return scrubbed
    if isinstance(payload, list):
        return [_scrub_pii(item) if isinstance(item, (dict, list)) else item for item in payload]  # type: ignore[return-value]
    return payload  # type: ignore[return-value]


# ── Coalesce check ─────────────────────────────────────────────────────────
async def _autosave_should_coalesce(user_id: UUID, product_id: str) -> bool:
    """Return True if a previous autosave for this (user, product) is still in window."""
    key = f"audit:coalesce:{user_id}:{product_id}"
    try:
        client = await get_valkey_otp()
        acquired = await client.set(key, "1", nx=True, ex=_COALESCE_WINDOW_SECONDS)
        return not bool(acquired)
    except Exception as exc:  # noqa: BLE001 — drop-on-failure
        logger.warning("audit coalesce check failed (key=%s): %s", key, exc)
        return False


def _extract_product_id(path: str) -> str | None:
    """Pull the product UUID out of a ``/api/v1/products/{id}/...`` path."""
    m = re.match(r"^/api/v1/products/([0-9a-fA-F-]+)", path)
    return m.group(1) if m else None


def _derive_event_type(request: Request) -> str:
    """Use the ``@audit_event`` tag if present; else ``{method}.{path}``."""
    route = request.scope.get("route")
    endpoint = getattr(route, "endpoint", None)
    tag = getattr(endpoint, _AUDIT_EVENT_ATTR, None)
    if tag:
        return tag
    method = request.method.lower()
    path = getattr(route, "path", request.url.path)
    derived = f"{method}.{path}"
    return derived[:40]


def _derive_entity(request: Request, event_type: str) -> tuple[str | None, UUID | None]:
    """Best-effort entity_type + entity_id from path + event_type."""
    path = request.url.path
    product_match = re.match(r"^/api/v1/products/([0-9a-fA-F-]+)", path)
    if product_match:
        try:
            return ("product", UUID(product_match.group(1)))
        except ValueError:
            pass
    if event_type.startswith("seller_profile"):
        return ("seller_profile", None)
    if event_type.startswith("auth"):
        return (None, None)
    return (None, None)


# ── Middleware ─────────────────────────────────────────────────────────────
class AuditMiddleware(BaseHTTPMiddleware):
    """Write ``audit_events`` row AFTER a successful 2xx response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)

        try:
            await self._maybe_write(request, response)
        except Exception as exc:  # noqa: BLE001 — drop-on-failure per §1.E
            logger.warning(
                "audit write failed (path=%s, status=%s): %s",
                request.url.path,
                response.status_code,
                exc,
            )

        return response

    @staticmethod
    async def _maybe_write(request: Request, response: Response) -> None:
        # Gate 1: 2xx only.
        if not (200 <= response.status_code < 300):
            return

        # Gate 2: authenticated calls only.
        user_id: UUID | None = getattr(request.state, "user_id", None)
        if user_id is None:
            return

        # Gate 2.5 — write-method only.
        if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
            return

        path = request.url.path
        is_autosave = bool(_AUTOSAVE_PATH.match(path))

        # Gate 3: coalesce autosave hits within the 5-minute window.
        if is_autosave:
            product_id = _extract_product_id(path)
            if product_id is not None and await _autosave_should_coalesce(user_id, product_id):
                return

        event_type = _derive_event_type(request)
        entity_type, entity_id = _derive_entity(request, event_type)

        request_id = getattr(request.state, "request_id", None)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        metadata = {
            "ip": client_ip,
            "user_agent": user_agent,
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status": response.status_code,
        }
        metadata = _scrub_pii(metadata)
        diff = None

        from app.shared.models import AuditEvent  # local import

        try:
            async with AsyncSessionLocal() as session:
                row = AuditEvent(
                    user_id=user_id,
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    diff_jsonb=diff,
                    metadata_jsonb=metadata,
                )
                session.add(row)
                await session.commit()
        except Exception as exc:  # noqa: BLE001 — drop-on-failure
            logger.warning(
                "audit_events insert failed (event=%s, user=%s): %s",
                event_type,
                user_id,
                exc,
            )


__all__ = [
    "AuditMiddleware",
    "audit_event",
]
