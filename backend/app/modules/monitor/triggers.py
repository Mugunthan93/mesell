"""``monitor`` PUBLIC trigger seam — fire-and-forget category-scrape enqueue.

Owned by ``meesell-services-builder``. Part of the category change monitor
feature (``feature/category-monitor``), Wave 3 (trigger wiring).

Why this file is PUBLIC (alongside ``service.py``)
--------------------------------------------------
Wave 3 wires the LIVE V1 seller flows (catalog-add in ``catalog.service``
and onboarding-complete in ``customer.service``) into the monitor's dedupe
gate.  Those host modules must NOT reach into ``monitor.repository`` (PRIVATE
per §16) nor import the Celery task module directly at module-load time.
:func:`enqueue_category_scrape` is the single, narrow, public entry point
they call.

The non-negotiable invariant: a Celery enqueue failure (broker outage,
serialisation error, import error) MUST NEVER propagate into the host seller
flow.  Catalog-add and onboarding-complete are revenue paths — they have to
succeed even when Valkey (the broker, DB 1) is down.  This seam is therefore:

  * **synchronous** — never awaited, never blocks the event loop / request;
  * **fire-and-forget** — it does not wait for the task result;
  * **failure-isolated** — every exception is swallowed + logged at WARNING,
    so the caller's transaction commits regardless.

The actual dedupe (TTL reuse + in-flight coalesce) happens inside the task
(:func:`monitor.service.run_dedupe_gate`), so this seam can enqueue freely —
duplicates are suppressed downstream, never here.
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)

__all__ = [
    "enqueue_category_scrape",
]


def enqueue_category_scrape(category_id: str | UUID) -> None:
    """Fire-and-forget enqueue of ``monitor.scrape_category`` for one category.

    Synchronous (never awaited). NEVER raises into the caller — a broker
    outage or any other enqueue failure is swallowed + logged at WARNING so
    the host seller flow (catalog-add / onboarding-complete) always survives.

    Args:
        category_id: the LEAF ``categories.id`` to scrape. Coerced to ``str``
            for the Celery JSON serialiser (which strips the UUID type).
    """
    try:
        # Lazy import — keep the host modules' import-time graph light and
        # avoid pulling the Celery task module at their module load.
        from app.modules.monitor.tasks import scrape_category_task

        scrape_category_task.delay(str(category_id))
    except Exception as exc:  # noqa: BLE001 — host seller flow MUST survive a broker outage
        logger.warning(
            "monitor trigger enqueue failed for category=%s: %r", category_id, exc
        )
