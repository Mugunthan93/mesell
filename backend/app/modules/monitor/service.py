"""``monitor`` service — the category change monitor dedupe gate (Wave 2 Unit C).

This module owns the async orchestration behind the ``monitor.scrape_category``
Celery task. The Celery wrapper (``tasks.py``) is thin; all logic lives here so
it is unit-testable without a Celery worker.

The gate (three guards, in order)
---------------------------------
(a) **TTL freshness guard.** Read the latest ``category_snapshots.captured_at``
    for the id. If ``now(UTC) - captured_at < CATEGORY_SNAPSHOT_TTL_SECONDS``
    the snapshot is still fresh — reuse it, scrape NOTHING, return
    ``{"action": "ttl_reuse", ...}``. No Valkey key is touched.

(b/c) **Atomic in-flight claim.** ``SET catmonitor:snapshot:<id> <ts> NX EX
    CATEGORY_INFLIGHT_TTL_SECONDS``. The ``NX`` makes the claim atomic:

      - NX fails → another worker is already scraping this category right
        now. Return ``{"action": "coalesced", ...}``, scrape NOTHING, and
        do NOT delete the existing key (it belongs to the other worker).
      - NX succeeds → we own the claim. Proceed inside a ``try/finally`` so
        the key is ALWAYS released — on success AND on any raised exception.
        The exception is NEVER swallowed; it propagates after the
        ``finally`` clears the key.

    Inside the claim:
      1. resolve scrape inputs (``meesho_leaf_id`` → ``sscat_id``,
         ``leaf_name`` → ``category_name``); no row → ``CategoryNotFoundError``.
      2. ``scrape_category(...)`` — writes the new snapshot row (it owns its
         own engine via ``db_url``). LIVE-Meesho path → MOCKED in every test.
      3. load the PRIOR snapshot (second-latest row) for ``prev_dims`` /
         ``prev_hash``.
      4. ``diff_category_snapshot(...)`` → verdict dict.
      5. return ``{"action": "scraped", "verdict", ...}``. Log INFO on
         PASS / REVIEW_REQUIRED, WARNING on BLOCK.

Wave boundary (HARD)
--------------------
On BLOCK the gate logs a WARNING and STOPS. It does NOT fan out, does NOT
write any notification row, does NOT read ``category_subscription``, and does
NOT touch catalog flags — those are Wave 4. The verdict is stored only in the
Celery result dict + the log.

DB sessions
-----------
The gate's own reads use :func:`app.shared.database.make_worker_session`
(NullPool — safe across the ``asyncio.run`` event-loop boundary). The live
scrape manages its OWN engine internally via the ``db_url`` argument.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.modules.monitor.exceptions import CategoryNotFoundError
from app.shared.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Valkey in-flight claim key namespace (DB 0 — OTP/session/locks per §1.B).
_INFLIGHT_KEY_PREFIX = "catmonitor:snapshot:"

# Wave-3 SERVE read-through cache (Valkey DB 3 via core/cache — distinct from
# the DB-0 in-flight LOCK above; do NOT conflate the two keyspaces).
_SERVE_TTL_SECONDS = 86400  # 1-day cache TTL (locked design)
_SERVE_KEY_PREFIX = "monitor:snapshot:"


def _inflight_key(category_id: UUID) -> str:
    """Build the atomic-claim Valkey key for a category id (DB 0 lock)."""
    return f"{_INFLIGHT_KEY_PREFIX}{category_id}"


def _snapshot_cache_key(category_id: UUID) -> str:
    """Build the DB-3 read-through serve cache key for a category id."""
    return f"{_SERVE_KEY_PREFIX}{category_id}"


async def run_dedupe_gate(category_id: UUID, *, db_url: str) -> dict[str, Any]:
    """Run the dedupe gate → scrape → diff → store-verdict for one category.

    Args:
        category_id: ``categories.id`` UUID of the category to (maybe) scrape.
        db_url:      SQLAlchemy async DB URL passed through to
                     :func:`scripts.scrape_category.scrape_category` for its
                     OWN engine (snapshot-row insert). The gate's own reads
                     use ``make_worker_session`` against ``settings.DATABASE_URL``.

    Returns:
        One of three result shapes, all carrying ``action`` + ``category_id``::

            {"action": "ttl_reuse",  "category_id": ..., "captured_at": ...}
            {"action": "coalesced",  "category_id": ...}
            {"action": "scraped",    "category_id": ..., "content_hash": ...,
             "verdict": ..., "block_reasons": [...]}

    Raises:
        CategoryNotFoundError: ``category_id`` has no ``categories`` row. The
            in-flight Valkey claim is cleared before this propagates.
        Exception: any error raised by the live scrape / diff propagates
            unswallowed; the in-flight claim is cleared first (``finally``).
    """
    # Lazy imports — keep module import light + dodge heavy worker deps at boot.
    from scripts.diff_category_rules import diff_category_snapshot
    from scripts.scrape_category import scrape_category

    from app.core.cache import evict
    from app.modules.monitor import repository as monitor_repo
    from app.shared.database import make_worker_session
    from app.shared.valkey import get_valkey_otp

    cat_id_str = str(category_id)

    # ── Guard (a): TTL freshness — reuse a fresh snapshot, scrape nothing ──
    async with make_worker_session() as session:
        latest = await monitor_repo.get_latest_snapshot(session, category_id)

    if latest is not None:
        captured_at = latest.captured_at
        # captured_at is TIMESTAMPTZ → tz-aware; guard against a naive value
        # defensively so the subtraction never raises.
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - captured_at
        ttl = timedelta(seconds=settings.CATEGORY_SNAPSHOT_TTL_SECONDS)
        if age < ttl:
            logger.info(
                "monitor gate: category=%s snapshot fresh (age=%ss < ttl=%ss) "
                "— reusing, no scrape",
                cat_id_str,
                int(age.total_seconds()),
                settings.CATEGORY_SNAPSHOT_TTL_SECONDS,
            )
            return {
                "action": "ttl_reuse",
                "category_id": cat_id_str,
                "captured_at": captured_at.isoformat(),
            }

    # ── Guard (b/c): atomic in-flight claim (SET NX EX) ──
    cache = await get_valkey_otp()
    key = _inflight_key(category_id)
    claim_ts = datetime.now(timezone.utc).isoformat()
    claimed = await cache.set(
        key,
        claim_ts,
        nx=True,
        ex=settings.CATEGORY_INFLIGHT_TTL_SECONDS,
    )
    if not claimed:
        # Another worker holds the claim — coalesce. Do NOT delete its key.
        logger.info(
            "monitor gate: category=%s already in-flight (claim held) — coalescing",
            cat_id_str,
        )
        return {
            "action": "coalesced",
            "category_id": cat_id_str,
        }

    # We own the claim. ALWAYS release it (success or exception).
    try:
        # 1. Resolve Meesho scrape inputs for this category.
        async with make_worker_session() as session:
            inputs = await monitor_repo.get_category_scrape_inputs(session, category_id)
        if inputs is None:
            raise CategoryNotFoundError(cat_id_str)
        sscat_id, category_name = inputs

        # 2. Live scrape — writes the new snapshot row (owns its own engine).
        #    LIVE-Meesho path; MOCKED in every test.
        logger.info(
            "monitor gate: category=%s claim acquired — scraping "
            "(sscat_id=%s name=%r)",
            cat_id_str,
            sscat_id,
            category_name,
        )
        scrape_result = await scrape_category(
            cat_id_str,
            sscat_id,
            category_name=category_name,
            db_url=db_url,
        )
        new_dims = scrape_result["dimensions"]
        new_hash = scrape_result["content_hash"]

        # 3. Load the PRIOR snapshot (second-latest row) to diff against.
        async with make_worker_session() as session:
            prior = await monitor_repo.get_prior_snapshot(session, category_id)
        prev_dims = prior.dimensions_jsonb if prior is not None else {}
        prev_hash = prior.content_hash if prior is not None else None

        # 4. Diff → verdict (pure stdlib; no DB / network).
        verdict_result = diff_category_snapshot(
            new_dims,
            prev_dims,
            prev_hash=prev_hash,
            new_hash=new_hash,
        )
        verdict = verdict_result["verdict"]
        block_reasons = verdict_result.get("block_reasons", [])

        # 5. Store the verdict (Celery result dict + log). NO fan-out (Wave 4).
        if verdict == "BLOCK":
            logger.warning(
                "monitor gate: category=%s verdict=BLOCK content_hash=%s "
                "block_reasons=%s — STOPPING (no fan-out; Wave 4 owns promotion)",
                cat_id_str,
                new_hash,
                block_reasons,
            )
        else:
            logger.info(
                "monitor gate: category=%s verdict=%s content_hash=%s",
                cat_id_str,
                verdict,
                new_hash,
            )

        # Evict-on-update: a new snapshot row was just inserted, so the
        # read-through serve cache (DB 3) is now stale — drop it so the next
        # get_served_category_data rebuilds from the fresh DB row.
        await evict(_snapshot_cache_key(category_id))

        return {
            "action": "scraped",
            "category_id": cat_id_str,
            "content_hash": new_hash,
            "verdict": verdict,
            "block_reasons": block_reasons,
        }
    finally:
        # Release the in-flight claim on EVERY exit path (success + exception).
        # Never swallow the exception — let it propagate after the delete.
        try:
            await cache.delete(key)
        except Exception as exc:  # noqa: BLE001 — best-effort lock release
            logger.warning(
                "monitor gate: failed to release in-flight claim for "
                "category=%s (key will expire via EX): %r",
                cat_id_str,
                exc,
            )


async def get_served_category_data(category_id: UUID, db: AsyncSession) -> dict[str, Any]:
    """Serve the latest captured snapshot for a category (cache → DB).

    Wave-3 INTERNAL-ONLY serving read (no public route yet — the customer-
    facing endpoint lands in Wave 4 with the FE contract). Read-through:
    the value is served from the Valkey DB-3 cache when warm, else rebuilt
    from the latest ``category_snapshots`` row and cached for
    ``_SERVE_TTL_SECONDS`` (1 day).

    The DB fallback reads ONLY ``category_snapshots`` (no live Meesho scrape
    ever sits in the read path — scraping is the Wave-2 gate's job, gated +
    de-duped). A fresh scrape evicts this cache via :func:`evict` in
    :func:`run_dedupe_gate`, so a warm value is never older than the most
    recent capture.

    Args:
        category_id: ``categories.id`` UUID to serve.
        db: Async session for the DB fallback read.

    Returns:
        ``{"category_id", "captured_at", "content_hash", "dimensions"}`` —
        all JSON-serialisable (``captured_at`` is ISO-8601 text).

    Raises:
        CategorySnapshotNotFoundError: the category has no snapshot row.
    """
    # Lazy imports — keep module import light (core/cache pulls in valkey).
    from app.core.cache import get_or_set
    from app.modules.monitor import repository as monitor_repo
    from app.modules.monitor.exceptions import CategorySnapshotNotFoundError

    async def _fetch() -> dict[str, Any]:
        row = await monitor_repo.get_latest_snapshot(db, category_id)
        if row is None:
            raise CategorySnapshotNotFoundError(str(category_id))
        return {
            "category_id": str(category_id),
            "captured_at": row.captured_at.isoformat(),
            "content_hash": row.content_hash,
            "dimensions": row.dimensions_jsonb,
        }

    return await get_or_set(
        _snapshot_cache_key(category_id),
        _fetch,
        ttl=_SERVE_TTL_SECONDS,
    )


__all__ = [
    "run_dedupe_gate",
    "get_served_category_data",
]
