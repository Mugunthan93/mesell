"""Unit tests for the category change monitor SERVING layer (Wave 3 Unit S).

What this covers
----------------
* ``monitor.service.get_served_category_data`` — the read-through serve
  (Valkey DB-3 cache → ``category_snapshots`` DB fallback). INTERNAL-ONLY
  in Wave 3 (no public route).
* ``core.cache.evict`` — the write-path sibling of ``get_or_set``.
* Evict-on-update — the gate's ``"scraped"`` success branch drops the stale
  serve cache after inserting a new snapshot row.

NON-LIVE CONTRACT (load-bearing)
--------------------------------
* The serve path NEVER scrapes Meesho — ``_fetch`` reads ONLY the mocked
  ``monitor.repository.get_latest_snapshot``. Case ``test_serve_path_no_live_meesho``
  greps the service module's serve method for any scrape symbol — MUST be zero.
* Valkey is ``fakeredis.aioredis.FakeRedis`` (DB-3 serve cache + DB-0 gate
  lock) — no live Valkey.
* DB reads are exercised through the mocked repository surface — no
  connection is opened to any database (least-privilege; the serve DB-read
  CONTRACT is asserted via the repository mock).

Revert-check structure
----------------------
* Strip the ``evict(...)`` line from the gate's scraped branch → the
  ``test_evict_on_update_clears_stale_serve_cache`` case goes RED (the second
  serve returns the STALE hash because the cache was never cleared).
* Strip the cache write in ``get_or_set`` (out of scope here) → the cache-HIT
  case would re-hit the DB.
"""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fakeredis import aioredis as fake_aioredis

import app.core.cache as core_cache
import app.modules.monitor.service as monitor_service
from app.modules.monitor.exceptions import CategorySnapshotNotFoundError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_CATEGORY_ID = uuid4()
_CAPTURED_AT = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
_OLD_HASH = "a" * 64
_NEW_HASH = "b" * 64
_DIMS = {
    "compliance_fields": {"required": ["size"], "optional": []},
    "shipping_slab": {"shipping_charges": 30, "gst_percentage": 5},
    "banned_words": {"branded": []},
    "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0, "sscat_id": "46677c24"},
}


def _snapshot_row(content_hash: str = _OLD_HASH):
    """A minimal stand-in for a CategorySnapshot ORM row."""
    return SimpleNamespace(
        captured_at=_CAPTURED_AT,
        content_hash=content_hash,
        dimensions_jsonb=_DIMS,
    )


@pytest.fixture
def serve_cache(monkeypatch):
    """In-memory FakeRedis standing in for the DB-3 serve cache.

    Patched onto ``app.core.cache.get_valkey_cache`` (the name bound INTO
    core.cache at import) so BOTH the ``core.cache.get_or_set`` read path and
    ``core.cache.evict`` resolve to the same in-memory client. Patching the
    source ``app.shared.valkey.get_valkey_cache`` would NOT affect the already
    bound reference in core.cache.
    """
    client = fake_aioredis.FakeRedis(decode_responses=True)

    async def _get_cache():
        return client

    monkeypatch.setattr("app.core.cache.get_valkey_cache", _get_cache)
    return client


# ---------------------------------------------------------------------------
# Case 1 — cache MISS reads DB, returns the dict, populates the cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_cache_miss_reads_db_and_populates(serve_cache, monkeypatch):
    """First call (cold cache) reads the DB and writes the value to cache."""
    get_latest = AsyncMock(return_value=_snapshot_row())
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_latest_snapshot", get_latest
    )
    db = SimpleNamespace()  # repo is mocked → session never used

    result = await monitor_service.get_served_category_data(_CATEGORY_ID, db)

    assert result == {
        "category_id": str(_CATEGORY_ID),
        "captured_at": _CAPTURED_AT.isoformat(),
        "content_hash": _OLD_HASH,
        "dimensions": _DIMS,
    }
    # DB was consulted exactly once on the miss.
    get_latest.assert_awaited_once()
    # The serve cache is now populated under the versioned key.
    full_key = core_cache._versioned_key(
        monitor_service._snapshot_cache_key(_CATEGORY_ID), None
    )
    assert await serve_cache.get(full_key) is not None


# ---------------------------------------------------------------------------
# Case 2 — cache HIT does NOT touch the DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_cache_hit_skips_db(serve_cache, monkeypatch):
    """A second call serves from cache; the DB read is NOT invoked again."""
    get_latest = AsyncMock(return_value=_snapshot_row())
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_latest_snapshot", get_latest
    )
    db = SimpleNamespace()

    first = await monitor_service.get_served_category_data(_CATEGORY_ID, db)
    second = await monitor_service.get_served_category_data(_CATEGORY_ID, db)

    assert first == second
    # DB read happened ONCE (on the miss); the hit served from cache.
    get_latest.assert_awaited_once()


# ---------------------------------------------------------------------------
# Case 3 — no snapshot row → CategorySnapshotNotFoundError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_no_snapshot_raises(serve_cache, monkeypatch):
    """A category that has never been scraped raises the not-found error."""
    get_latest = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_latest_snapshot", get_latest
    )
    db = SimpleNamespace()

    with pytest.raises(CategorySnapshotNotFoundError) as exc_info:
        await monitor_service.get_served_category_data(_CATEGORY_ID, db)

    assert exc_info.value.category_id == str(_CATEGORY_ID)
    get_latest.assert_awaited_once()
    # Nothing was cached (the fetch raised before the cache SET).
    full_key = core_cache._versioned_key(
        monitor_service._snapshot_cache_key(_CATEGORY_ID), None
    )
    assert await serve_cache.get(full_key) is None


# ---------------------------------------------------------------------------
# Case 4 — evict-on-update: a fresh scrape clears the stale serve cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evict_on_update_clears_stale_serve_cache(serve_cache, monkeypatch):
    """serve (warm w/ OLD hash) → gate scrape inserts NEW row + evicts →
    next serve REBUILDS from DB and returns the NEW content_hash.

    Proves the stale serve cache was cleared by the gate's evict-on-update.
    """
    # The DB's "latest snapshot" the serve read sees. We flip this from the
    # OLD row to the NEW row at the moment the gate's scrape "inserts".
    db_state = {"latest": _snapshot_row(content_hash=_OLD_HASH)}

    async def _get_latest(_db, _cid):
        return db_state["latest"]

    monkeypatch.setattr(
        "app.modules.monitor.repository.get_latest_snapshot", _get_latest
    )

    db = SimpleNamespace()

    # 1. First serve → cache MISS → caches the OLD hash.
    first = await monitor_service.get_served_category_data(_CATEGORY_ID, db)
    assert first["content_hash"] == _OLD_HASH

    # 2. Run the gate's scrape branch. Wire its collaborators so we reach the
    #    scraped success branch (which calls evict) WITHOUT any live Meesho.
    #    DB-0 lock client = its own FakeRedis (distinct keyspace from serve).
    lock_cache = fake_aioredis.FakeRedis(decode_responses=True)

    async def _get_otp():
        return lock_cache

    monkeypatch.setattr("app.shared.valkey.get_valkey_otp", _get_otp)

    @asynccontextmanager
    async def _fake_worker_session():
        yield SimpleNamespace()

    monkeypatch.setattr(
        "app.shared.database.make_worker_session", _fake_worker_session
    )

    # gate's TTL guard reads get_latest_snapshot → return None so it proceeds
    # to claim + scrape (do NOT short-circuit on the OLD row's freshness).
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_latest_snapshot",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_prior_snapshot",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_category_scrape_inputs",
        AsyncMock(return_value=("46677c24", "Kurtis")),
    )

    # scrape "inserts" the NEW snapshot row → flip the DB state the serve sees.
    async def _scrape(*_args, **_kwargs):
        db_state["latest"] = _snapshot_row(content_hash=_NEW_HASH)
        return {
            "dimensions": _DIMS,
            "content_hash": _NEW_HASH,
            "blob_path": "/tmp/b.json",
            "meta_path": "/tmp/b.meta.json",
            "db_inserted": True,
        }

    monkeypatch.setattr("scripts.scrape_category.scrape_category", _scrape)

    gate_result = await monitor_service.run_dedupe_gate(
        _CATEGORY_ID,
        db_url="postgresql+asyncpg://meesell:password@localhost:5432/meesell_test",
    )
    assert gate_result["action"] == "scraped"
    assert gate_result["content_hash"] == _NEW_HASH

    # 3. After the gate evicted, restore the real get_latest so the next serve
    #    rebuilds from the (now NEW) db_state.
    monkeypatch.setattr(
        "app.modules.monitor.repository.get_latest_snapshot", _get_latest
    )

    second = await monitor_service.get_served_category_data(_CATEGORY_ID, db)
    # The stale cache was cleared → serve rebuilt from DB → NEW hash.
    assert second["content_hash"] == _NEW_HASH


# ---------------------------------------------------------------------------
# Case 5 — grep-proof: zero live Meesho in the serve path
# ---------------------------------------------------------------------------


def test_serve_path_no_live_meesho():
    """The serve method's source contains no scrape / Meesho symbols.

    The read path must never reach the live-Meesho scraper — scraping is the
    Wave-2 gate's job (gated + de-duped). This statically asserts the serve
    method body references only the DB repository read.
    """
    source = inspect.getsource(monitor_service.get_served_category_data)
    forbidden = (
        "scrape_category",
        "scripts.scrape_category",
        "meesho",
        "async_playwright",
        "webkit",
    )
    for token in forbidden:
        assert token not in source, f"serve path must not reference {token!r}"
    # Positive assertion: it DOES read the snapshot repository.
    assert "get_latest_snapshot" in source
