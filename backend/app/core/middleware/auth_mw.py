"""Opportunistic JWT-decode middleware — position 3 in the §4.H middleware chain.

Per BACKEND_ARCHITECTURE.md §4.G (LOCKED 2026-06-05), this middleware decodes
the ``Authorization: Bearer <token>`` header (if present) and attaches the
resulting :class:`app.core.auth.CurrentUser` to ``request.state.user`` for log
correlation, tenancy-middleware copy-forward, and audit-log enrichment.

Fail-open posture
-----------------
**Missing, malformed, or expired tokens leave ``request.state.user = None``
and the request proceeds.**  This middleware does NOT raise 401.  Enforcement
lives in :func:`app.core.auth.get_current_user` (§4.B) — the dep is the
fail-closed layer; this middleware is the fail-open log-correlation layer.

Rationale: public routes — ``/health``, ``/api/v1/auth/otp/send``,
``/api/v1/auth/otp/verify``, ``/api/v1/auth/refresh`` (cookie-authenticated,
no Bearer header), the OpenAPI docs at ``/docs``, the Prometheus
``/metrics`` scrape — MUST traverse this middleware without a 401 short-circuit.
Each of those routes either declines to depend on ``get_current_user`` or
opt-in to a soft variant (none of which exists in V1 — public routes simply
do not call the dep).

State writes
------------
* Sets ``request.state.user`` to :class:`CurrentUser` on success.
* Sets ``request.state.user`` to ``None`` on every failure path.

No database lookup happens here — the dep at §4.B is responsible for proving
the decoded ``sub`` resolves to a live row.  Doing the DB lookup in middleware
would impose the cost on every public-route hit (``/health`` × thousands per
minute from the Prometheus scrape) for no security benefit; the dep does it
exactly once per authenticated route invocation.

Position in chain (§4.H)
------------------------
``CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw →
(route handler) → audit_mw``.  Auth runs before tenancy because tenancy needs
``request.state.user`` to exist (or be ``None``); auth runs after request-id
because every downstream layer including auth failures wants a correlation
ID.  This middleware is registered by ``services-builder`` in
``app/main.py`` per the §4.G owner row.
"""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.auth import CurrentUser
from app.shared.config import settings

logger = logging.getLogger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Opportunistically decode JWT and attach ``CurrentUser`` to request state.

    Per §4.G ``auth_mw.py`` contract row:

    * Reads ``Authorization: Bearer <token>`` header.
    * Writes ``request.state.user: CurrentUser | None``.
    * **Fail-open** — missing / malformed / expired tokens leave
      ``request.state.user = None``; the request proceeds normally.

    The corresponding fail-closed enforcement is :func:`app.core.auth.get_current_user`
    (§4.B), which routes opt into via ``Depends``.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Default the state to ``None`` so downstream middleware always see a
        # well-defined attribute (the tenancy middleware reads
        # ``request.state.user`` unconditionally per §4.G).
        request.state.user = None

        auth_header = request.headers.get("Authorization") or request.headers.get(
            "authorization"
        )
        if not auth_header:
            return await call_next(request)

        # Tolerate small casing / whitespace variations from misbehaved
        # clients but reject anything that is not the canonical
        # ``Bearer <token>`` two-part header.  Malformed → fail-open.
        parts = auth_header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return await call_next(request)

        token = parts[1].strip()
        if not token:
            return await call_next(request)

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.InvalidTokenError:
            # Covers ExpiredSignatureError, DecodeError, InvalidSignatureError,
            # ImmatureSignatureError, InvalidAudienceError, etc.  Per §4.G we
            # are deliberately silent here — the dep at §4.B is the layer that
            # surfaces the 401 / 403.
            return await call_next(request)

        # Build CurrentUser from the claim payload.  We do NOT hit the
        # database here — that's the dep's job (§4.B).  V1 narrows ``plan`` to
        # ``"free"``; the JWT claim itself is read but the literal type is
        # constrained here to honour the §4.B CurrentUser dataclass.
        try:
            user_id = UUID(payload["sub"])
        except (KeyError, ValueError, TypeError):
            # Decoded payload missing/invalid ``sub`` — treat as malformed
            # and leave state.user None.
            return await call_next(request)

        plan: Literal["free"] = "free"  # V1 narrow per §4.B
        request.state.user = CurrentUser(user_id=user_id, plan=plan)
        return await call_next(request)


__all__ = ["AuthContextMiddleware"]
