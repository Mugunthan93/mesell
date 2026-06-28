"""``monitor`` router — ``GET /api/v1/notifications`` (Wave-4 Unit N).

This is the monitor module's first public HTTP surface.  The route is
flag-gated on ``FEATURE_CATEGORY_MONITOR_ENABLED`` (default ``False``) and
mounted in ``app/main.py`` only when the flag is on.  When the flag is off
the path is NOT registered → FastAPI returns the default 404 → the §17
mounted-endpoint count stays at 28 until the flag is flipped per-namespace
by the founder.

§17 NOTE (LOCKED — FOUNDER GATE)
---------------------------------
Mounting this router bumps §17 from 28 → 29.
``BACKEND_ARCHITECTURE.md §17`` is a LOCKED document — do NOT self-apply
the amendment.  The 28→29 bump is the founder's gate at the
``feature/category-monitor/integration → develop`` merge.  The PR body
carries the founder-gate flag; this file carries the code.

Tenancy
-------
Every query is scoped to the caller's ``user_id`` via
:func:`app.core.tenancy.scope_to_user` (called inside
:func:`monitor.service.list_notifications` — the route is thin).  A seller
NEVER sees another seller's notifications.

Out of scope (Director rulings)
--------------------------------
* ``get_served_category_data`` stays INTERNAL (Director Q2).
* Mark-read mutation (``PATCH /notifications/{id}``) DEFERRED to Wave 5.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID  # noqa: F401 — used by type hints

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.modules.monitor import service as monitor_service
from app.modules.monitor.schemas import NotificationItem, NotificationListResponse
from app.shared.config import settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List notifications for the authenticated seller",
)
async def list_notifications(
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    unread_only: Annotated[
        bool, Query(description="When true, only unread notifications are returned")
    ] = False,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """Return the authenticated seller's own notifications.

    Tenancy: the caller receives ONLY their own notifications — the service
    layer applies ``WHERE user_id = <caller.user_id>`` via
    ``core.tenancy.scope_to_user``.

    The ``unread_count`` field in the response always reflects the total
    unread count across ALL pages so the FE bell badge is accurate
    regardless of the requested page.

    Flag-gate: this endpoint is only mounted when
    ``FEATURE_CATEGORY_MONITOR_ENABLED`` is ``True`` (see main.py). When
    the flag is off the route is not registered and FastAPI returns 404.
    """
    if not settings.FEATURE_CATEGORY_MONITOR_ENABLED:
        # Belt-and-suspenders in-handler guard (main.py already skips the
        # include_router call when the flag is off, so this branch only fires
        # when the router is somehow mounted while the flag is False —
        # e.g. during a test that overrides the mount but not the flag).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category monitor is disabled in this environment",
        )

    items, total, unread_count = await monitor_service.list_notifications(
        user_id=user.user_id,
        page=page,
        limit=limit,
        unread_only=unread_only,
        db=db,
    )

    logger.info(
        "notifications list: user=%s page=%d limit=%d unread_only=%s "
        "total=%d unread_count=%d",
        user.user_id,
        page,
        limit,
        unread_only,
        total,
        unread_count,
    )

    return NotificationListResponse(
        data=[NotificationItem.model_validate(row) for row in items],
        total=total,
        page=page,
        unread_count=unread_count,
    )
