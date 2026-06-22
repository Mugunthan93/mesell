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

        # Wave-4 fan-out enqueue — ONLY on REVIEW_REQUIRED. PASS = no drift;
        # BLOCK = scrape anomaly (never spam sellers). Lazy import avoids a
        # tasks↔service import cycle (mirrors image/tasks lazy import).
        if verdict == "REVIEW_REQUIRED":
            from app.modules.monitor.tasks import fanout_category_change_task

            fanout_category_change_task.delay(cat_id_str, new_hash)

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


# ─────────────────────────────────────────────────────────────────────────────
# Wave-4 — fan-out + notify
# ─────────────────────────────────────────────────────────────────────────────


def _build_summary(category_name: str, n_catalogs: int, diff: dict[str, Any]) -> str:
    """Assemble the founder-locked seller-facing notification copy.

    English-only plain text (NEVER raw JSON). Only CHANGED dimensions
    contribute a fragment; fragments are joined with ``'; '`` and embedded in
    the headline. Currency is ``₹``; shipping deltas are integer rupees (W2
    casts shipping to int), transfer_price / platform_fee are floats.

    Returns the ``payload.summary`` string.
    """
    fragments: list[str] = []

    # ── compliance ──
    comp = diff.get("compliance_diff") or {}
    if comp.get("changed"):
        if comp.get("required_added"):
            fragments.append(
                f"added required field(s): {', '.join(comp['required_added'])}"
            )
        if comp.get("required_removed"):
            fragments.append(
                f"removed required field(s): {', '.join(comp['required_removed'])}"
            )
        opt_changed = sorted(
            set(comp.get("optional_added", [])) | set(comp.get("optional_removed", []))
        )
        if opt_changed:
            fragments.append(f"optional field(s) changed: {', '.join(opt_changed)}")

    # ── shipping ──
    ship = diff.get("shipping_diff") or {}
    if ship.get("changed"):
        ship_delta = ship.get("shipping_delta", 0)
        if ship_delta > 0:
            fragments.append(f"shipping cost rose ₹{abs(int(ship_delta))}")
        elif ship_delta < 0:
            fragments.append(f"shipping cost fell ₹{abs(int(ship_delta))}")
        if ship.get("gst_delta"):
            fragments.append(
                f"GST changed {ship['gst_percentage_old']}%→{ship['gst_percentage_new']}%"
            )

    # ── banned words ──
    banned = diff.get("banned_words_diff") or {}
    if banned.get("changed"):
        added: list[str] = []
        removed: list[str] = []
        for per_key in (banned.get("per_key") or {}).values():
            added.extend(per_key.get("added", []))
            removed.extend(per_key.get("removed", []))
        if added:
            fragments.append(f"new banned word(s): {', '.join(added)}")
        if removed:
            fragments.append(f"word(s) no longer banned: {', '.join(removed)}")

    # ── cost ──
    cost = diff.get("cost_fields_diff") or {}
    if cost.get("changed"):
        if cost.get("transfer_price_delta"):
            fragments.append(
                f"transfer price changed ₹{cost['transfer_price_old']}"
                f"→₹{cost['transfer_price_new']}"
            )
        if cost.get("platform_fee_delta"):
            fragments.append(
                f"platform fee changed ₹{cost['platform_fee_old']}"
                f"→₹{cost['platform_fee_new']}"
            )

    joined = "; ".join(fragments)
    return (
        f"Your category '{category_name}' changed: {joined}. "
        f"{n_catalogs} of your catalogs are affected — "
        f"review them before your next upload."
    )


def _changed_dimensions(diff: dict[str, Any]) -> list[str]:
    """Return the list of dimension names that changed (for the payload)."""
    changed: list[str] = []
    for dim, key in (
        ("compliance", "compliance_diff"),
        ("shipping", "shipping_diff"),
        ("banned_words", "banned_words_diff"),
        ("cost", "cost_fields_diff"),
    ):
        if (diff.get(key) or {}).get("changed"):
            changed.append(dim)
    return changed


async def fanout_category_change(
    category_id: UUID,
    content_hash: str,
    db: AsyncSession,
) -> dict[str, int]:
    """Fan a REVIEW_REQUIRED category change out to its subscribers (Wave 4).

    Idempotent end-to-end (Celery retries re-run the whole op safely):
      * the snapshot row is re-loaded + re-diffed (DECISION A — no W2 re-gate);
      * a superseded-snapshot guard STOPS if a fresher scrape replaced this one;
      * a defensive verdict re-check STOPS on BLOCK (never fan out a BLOCK);
      * per subscriber: products are FLAGGED (set-only, never toggled off) and
        ONE notification row is inserted ``ON CONFLICT DO NOTHING``.

    Args:
        category_id: ``categories.id`` whose change is being fanned out.
        content_hash: the ``category_snapshots.content_hash`` that triggered
            this fan-out — must match the latest snapshot (else superseded).
        db: async session; the whole fan-out runs in ONE transaction (the
            caller — the Celery wrapper or a test — owns commit/rollback).

    Returns:
        ``{notified_users, notifications_created, products_flagged,
        skipped_existing}`` (for the Celery result backend / assertions).
    """
    from scripts.diff_category_rules import diff_category_snapshot

    from app.modules.monitor import repository as monitor_repo

    cat_id_str = str(category_id)
    zero = {
        "notified_users": 0,
        "notifications_created": 0,
        "products_flagged": 0,
        "skipped_existing": 0,
    }

    # 1. Load latest snapshot + superseded guard.
    latest = await monitor_repo.get_latest_snapshot(db, category_id)
    if latest is None:
        logger.info(
            "monitor fan-out: category=%s has no snapshot — nothing to fan out",
            cat_id_str,
        )
        return zero
    if latest.content_hash != content_hash:
        logger.info(
            "monitor fan-out: category=%s content_hash=%s superseded by a fresher "
            "snapshot (latest=%s) — STOPPING (the fresher fan-out will run)",
            cat_id_str,
            content_hash,
            latest.content_hash,
        )
        return zero

    # 2. Re-diff against the prior snapshot (DECISION A).
    prior = await monitor_repo.get_prior_snapshot(db, category_id)
    prev_dims = prior.dimensions_jsonb if prior is not None else {}
    prev_hash = prior.content_hash if prior is not None else None
    diff = diff_category_snapshot(
        latest.dimensions_jsonb,
        prev_dims,
        prev_hash=prev_hash,
        new_hash=latest.content_hash,
    )

    # 3. Defensive verdict re-check — ONLY REVIEW_REQUIRED fans out.
    verdict = diff.get("verdict")
    if verdict != "REVIEW_REQUIRED":
        logger.warning(
            "monitor fan-out: category=%s re-diff verdict=%s (expected "
            "REVIEW_REQUIRED) — STOPPING, no fan-out",
            cat_id_str,
            verdict,
        )
        return zero

    # 4. WHO — distinct subscribers in this category.
    subscribers = await monitor_repo.get_distinct_subscribers(db, category_id)
    if not subscribers:
        logger.info(
            "monitor fan-out: category=%s has no subscribers — nothing to do",
            cat_id_str,
        )
        return zero

    category_name = await monitor_repo.get_category_name(db, category_id) or cat_id_str

    # 5. Flag mapping (built ONCE — same diff for every user).
    comp_changed = bool((diff.get("compliance_diff") or {}).get("changed"))
    ship_changed = bool((diff.get("shipping_diff") or {}).get("changed"))
    cost_changed = bool((diff.get("cost_fields_diff") or {}).get("changed"))
    banned_changed = bool((diff.get("banned_words_diff") or {}).get("changed"))
    # compliance → recheck; shipping/cost → reprice; banned → recheck+export
    # (banned words don't move cost — Director ruling); ANY change → export.
    flag_recheck = comp_changed or banned_changed
    flag_reprice = ship_changed or cost_changed
    flag_export = comp_changed or ship_changed or cost_changed or banned_changed
    changed_dims = _changed_dimensions(diff)

    # 6. Per-user fan-out — ONE transaction (the caller owns commit).
    notifications_created = 0
    skipped_existing = 0
    products_flagged = 0

    for user_id in subscribers:
        catalog_ids = await monitor_repo.get_user_catalog_ids(db, user_id, category_id)
        summary = _build_summary(category_name, len(catalog_ids), diff)
        payload = {
            "summary": summary,
            "diff_dimensions": changed_dims,
            "affected_catalog_ids": [str(cid) for cid in catalog_ids],
        }

        products_flagged += await monitor_repo.flag_user_products(
            db,
            user_id,
            category_id,
            recheck=flag_recheck,
            reprice=flag_reprice,
            export=flag_export,
        )

        inserted = await monitor_repo.insert_notification(
            db,
            user_id,
            category_id,
            content_hash,
            payload,
        )
        if inserted:
            notifications_created += 1
        else:
            skipped_existing += 1

    await db.commit()

    logger.info(
        "monitor fan-out: category=%s notified_users=%d created=%d "
        "skipped=%d products_flagged=%d",
        cat_id_str,
        len(subscribers),
        notifications_created,
        skipped_existing,
        products_flagged,
    )
    return {
        "notified_users": len(subscribers),
        "notifications_created": notifications_created,
        "products_flagged": products_flagged,
        "skipped_existing": skipped_existing,
    }


__all__ = [
    "run_dedupe_gate",
    "get_served_category_data",
    "fanout_category_change",
]
