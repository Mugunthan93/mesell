"""Audit middleware — append-only ``audit_events`` write after 2xx commit.

Per BACKEND_ARCHITECTURE.md §4.G + MVP_ARCH §11.3 / §11.4 / §11.9 +
Philosophy M8 ("if it committed, it logged; if it didn't commit, it never
happened").

Position
--------
Chain position 7 — runs AFTER the route handler.  This is enforced by
registering ``AuditMiddleware`` FIRST in ``app/main.py`` (Starlette wraps
later additions further out, so the first-registered is the deepest, which
runs closest to the route).

Trigger
-------
Writes a row IFF:

1. ``response.status_code`` is 2xx (200–299), AND
2. ``request.state.user_id`` is not None (anonymous traffic is ignored
   here; ``auth.login`` is exempt — emitted explicitly by the auth route
   handler via the ``@audit_event`` decorator combined with a 2xx return).

PII scrubbing (§11.9)
---------------------
Before any row is committed, the request/response capture is filtered:

* ``phone`` (any case) → ``SHA-256(phone + AUDIT_PII_SALT)``.
* ``FSSAI_no``, ``fssai_no``, ``GST_no``, ``gst_no`` → removed from the
  captured payload entirely.

Coalescing (§11.4)
------------------
Autosave PATCH events (path matches the locked autosave regex) coalesce
into a single audit row per ``(user_id, product_id)`` per 5-minute window:

* On the first hit, write the row + ``SETEX 300`` a coalescing marker in
  Valkey DB 0 keyed ``audit:coalesce:{user_id}:{product_id}``.
* On subsequent hits inside the window, skip the write.

Non-autosave events (``product.export``, ``seller_profile.update``,
``auth.login``) are NEVER coalesced — each call writes one row.

Drop-on-failure (§1.E + MVP_ARCH §13 LangFuse rule)
---------------------------------------------------
Audit failure NEVER blocks the response.  Every Valkey or DB call is
wrapped; on exception the failure is logged with WARNING and the response
is returned to the client unchanged.

``@audit_event`` decorator
--------------------------
Route handlers tag their canonical event type via the decorator::

    @router.post("/products/{product_id}/export")
    @audit_event("product.export")
    async def export_product(...): ...

When the handler is undecorated, the middleware derives a catch-all
``"{method}.{path_template}"`` event_type.
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

# Locked autosave path regex.  Matches both the dev convention
# ``/api/v1/products/{id}/draft`` and the FE-prefer alternative
# ``/api/v1/products/{id}/autosave``.  Both forms route through the
# autosave coalescing window.
_AUTOSAVE_PATH = re.compile(
    r"^/api/v1/products/[0-9a-fA-F-]+/(draft|autosave)/?$"
)

# ── PII scrubbing constants ────────────────────────────────────────────────
_PII_HASH_KEYS = ("phone",)
_PII_STRIP_KEYS = ("fssai_no", "FSSAI_no", "gst_no", "GST_no")

# Coalesce window (seconds) per MVP_ARCH §11.4.
_COALESCE_WINDOW_SECONDS = 300


def audit_event(event_type: str) -> Callable:
    """Tag a route handler with its canonical audit event type.

    The middleware reads the tag at request time.  Bare handlers without a
    tag still get a catch-all event_type derived from method + path.
    """

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
    """Recursively scrub PII in a JSON-like dict.

    Returns ``None`` if ``payload`` is None.  Otherwise returns a NEW dict
    with ``phone`` values hashed and FSSAI/GST keys stripped — the input
    is not mutated.
    """
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
    """Return True if a previous autosave for this (user, product) is still in window.

    Sets the marker if absent (so this call counts as the window opener).
    Returns False on Valkey errors so the row is NOT lost — drop-on-failure
    applies to the WRITE path, not to the coalescing check.
    """
    key = f"audit:coalesce:{user_id}:{product_id}"
    try:
        client = await get_valkey_otp()
        # SET NX EX — succeeds (returns truthy) only if the key did NOT exist.
        acquired = await client.set(key, "1", nx=True, ex=_COALESCE_WINDOW_SECONDS)
        # acquired truthy = window OPENER → do NOT coalesce.
        # acquired falsy = window already open → COALESCE (skip write).
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
    # Trim for the 40-char column constraint.
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

        # Audit failure MUST NEVER fail the response.  Wrap everything.
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

        # Gate 2.5 — write-method only; GETs and HEADs never produce audit rows (§17.F)
        if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
            return

        path = request.url.path
        is_autosave = bool(_AUTOSAVE_PATH.match(path))

        # Gate 3: coalesce autosave hits within the 5-minute window.
        if is_autosave:
            product_id = _extract_product_id(path)
            if product_id is not None and await _autosave_should_coalesce(user_id, product_id):
                return

        # Build the row.
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

        # diff_jsonb is left None here — the diff capture lives in the
        # service layer where pre-write / post-write objects are available.
        # Middleware ships only the event-level fact.
        diff = None

        # Local import — keeps core/ free of top-level domain coupling per §4.I.
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
