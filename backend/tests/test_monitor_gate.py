"""Unit tests for the category change monitor dedupe gate (Wave 2 Unit C).

NON-LIVE CONTRACT (load-bearing)
--------------------------------
* ``scrape_category`` (Unit A — the live-Meesho path) is MOCKED in EVERY
  test. No test reaches ``*.meesho.com`` / ``async_playwright`` / ``webkit``.
  Grep this file's diff for any such path — it MUST be zero.
* Valkey is ``fakeredis.aioredis.FakeRedis`` — no live Valkey.
* The gate's DB reads go through ``monitor.repository`` functions, which are
  mocked here, AND ``make_worker_session`` is stubbed to a no-DB async
  context manager — so NO connection is opened to any database (least-
  privilege vs even the disposable ``meesell_test`` DB; the gate's DB-read
  CONTRACT is exercised through the mocked repository surface).

Revert-check structure (per spec)
---------------------------------
* Strip the ``finally``-clear in ``service.run_dedupe_gate`` → cases
  ``test_cold_success_clears_key`` + ``test_cold_failure_propagates_and_clears_key``
  go RED (key left behind).
* Strip the TTL guard → ``test_ttl_hit_no_scrape_no_key`` goes RED (it would
  proceed to claim + scrape).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fakeredis import aioredis as fake_aioredis

import app.modules.monitor.service as monitor_service

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_CATEGORY_ID = uuid4()
_SSCAT_ID = "46677c24"
_CATEGORY_NAME = "Kurtis"
_DB_URL = "postgresql+asyncpg://meesell:password@localhost:5432/meesell_test"

# A minimal four-dimension projection accepted by diff_category_snapshot.
_NEW_DIMS = {
    "compliance_fields": {"required": ["size"], "optional": []},
    "shipping_slab": {"shipping_charges": 30, "gst_percentage": 5},
    "banned_words": {"branded": []},
    "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0, "sscat_id": _SSCAT_ID},
}
_NEW_HASH = "a" * 64


@pytest.fixture
def fake_cache():
    """In-memory FakeRedis standing in for the DB-0 Valkey client."""
    return fake_aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def patched_gate(monkeypatch, fake_cache):
    """Patch the gate's external collaborators.

    Returns a ``SimpleNamespace`` of the mocks so each test can configure
    return values / raises and assert call counts:

        .scrape   — AsyncMock for scripts.scrape_category.scrape_category
        .diff     — MagicMock for scripts.diff_category_rules.diff_category_snapshot
        .repo     — SimpleNamespace of the three repository AsyncMocks
        .cache    — the FakeRedis instance (assert key presence/absence)
        .key      — the in-flight Valkey key for _CATEGORY_ID
    """
    import scripts.diff_category_rules as diff_mod
    import scripts.scrape_category as scrape_mod

    import app.modules.monitor.repository as monitor_repo
    import app.shared.database as shared_db
    import app.shared.valkey as shared_valkey

    # ── Valkey DB-0 (in-flight lock): hand the gate the FakeRedis client ──
    async def _get_fake_cache():
        return fake_cache

    monkeypatch.setattr(shared_valkey, "get_valkey_otp", _get_fake_cache)

    # ── Valkey DB-3 (serve read-through cache): the gate's evict-on-update
    #    (W3) calls core.cache.evict in the scraped branch, which reaches the
    #    DB-3 cache. Fake it so the gate stays NON-LIVE (distinct keyspace
    #    from the DB-0 lock above). Patch the name bound INTO core.cache.
    import app.core.cache as core_cache

    serve_fake = fake_aioredis.FakeRedis(decode_responses=True)

    async def _get_fake_serve_cache():
        return serve_fake

    monkeypatch.setattr(core_cache, "get_valkey_cache", _get_fake_serve_cache)

    # ── make_worker_session: no-DB async context manager ──
    @asynccontextmanager
    async def _fake_worker_session():
        yield SimpleNamespace()  # repo fns are mocked → session is never used

    monkeypatch.setattr(shared_db, "make_worker_session", _fake_worker_session)

    # ── repository reads (mocked — no DB connection) ──
    get_latest = AsyncMock(return_value=None)
    get_prior = AsyncMock(return_value=None)
    get_inputs = AsyncMock(return_value=(_SSCAT_ID, _CATEGORY_NAME))
    monkeypatch.setattr(monitor_repo, "get_latest_snapshot", get_latest)
    monkeypatch.setattr(monitor_repo, "get_prior_snapshot", get_prior)
    monkeypatch.setattr(monitor_repo, "get_category_scrape_inputs", get_inputs)

    # ── scrape (Unit A) — MOCKED. Default = a successful scrape result. ──
    scrape = AsyncMock(
        return_value={
            "dimensions": _NEW_DIMS,
            "content_hash": _NEW_HASH,
            "blob_path": "/tmp/blob.json",
            "meta_path": "/tmp/blob.meta.json",
            "db_inserted": True,
        }
    )
    monkeypatch.setattr(scrape_mod, "scrape_category", scrape)

    # ── diff (Unit B) — real engine by default; tests may override. ──
    # We wrap the real function so verdict logic is exercised end-to-end.
    real_diff = diff_mod.diff_category_snapshot

    return SimpleNamespace(
        scrape=scrape,
        diff=real_diff,
        diff_mod=diff_mod,
        repo=SimpleNamespace(
            get_latest=get_latest,
            get_prior=get_prior,
            get_inputs=get_inputs,
        ),
        cache=fake_cache,
        key=f"catmonitor:snapshot:{_CATEGORY_ID}",
    )


# ---------------------------------------------------------------------------
# Case 1 — TTL hit → no scrape, no key set, action=ttl_reuse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ttl_hit_no_scrape_no_key(patched_gate):
    """A fresh latest snapshot short-circuits BEFORE any claim or scrape."""
    fresh_captured = datetime.now(timezone.utc) - timedelta(hours=1)
    patched_gate.repo.get_latest.return_value = SimpleNamespace(
        captured_at=fresh_captured,
        content_hash=_NEW_HASH,
        dimensions_jsonb=_NEW_DIMS,
    )

    result = await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert result["action"] == "ttl_reuse"
    assert result["category_id"] == str(_CATEGORY_ID)
    # No scrape.
    patched_gate.scrape.assert_not_called()
    # No Valkey key was set (the claim path was never reached).
    assert await patched_gate.cache.get(patched_gate.key) is None


# ---------------------------------------------------------------------------
# Case 2 — in-flight key present → coalesced, scrape NOT called, key intact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_flight_coalesced_key_left_intact(patched_gate):
    """When the claim key already exists, NX fails → coalesce, leave key."""
    # latest snapshot is STALE (or absent) so the TTL guard passes through.
    patched_gate.repo.get_latest.return_value = None
    # Pre-seed the in-flight key as another worker would have (value distinct).
    await patched_gate.cache.set(patched_gate.key, "other-worker-ts")

    result = await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert result["action"] == "coalesced"
    assert result["category_id"] == str(_CATEGORY_ID)
    patched_gate.scrape.assert_not_called()
    # Pre-existing key is LEFT INTACT (belongs to the other worker).
    assert await patched_gate.cache.get(patched_gate.key) == "other-worker-ts"


# ---------------------------------------------------------------------------
# Case 3 — cold success → scrape called once w/ correct args; key cleared
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cold_success_clears_key(patched_gate):
    """Cold path: claim → scrape → diff → verdict; key ABSENT after."""
    patched_gate.repo.get_latest.return_value = None  # no fresh snapshot

    result = await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert result["action"] == "scraped"
    assert result["content_hash"] == _NEW_HASH
    assert "verdict" in result
    # scrape called EXACTLY once with the resolved Meesho inputs + db_url.
    patched_gate.scrape.assert_awaited_once_with(
        str(_CATEGORY_ID),
        _SSCAT_ID,
        category_name=_CATEGORY_NAME,
        db_url=_DB_URL,
    )
    # diff was invoked (prior snapshot was None → first-ever scrape).
    patched_gate.repo.get_prior.assert_awaited_once()
    # finally cleared the in-flight key.
    assert await patched_gate.cache.get(patched_gate.key) is None


@pytest.mark.asyncio
async def test_cold_success_sets_key_during_run(patched_gate):
    """The in-flight key is HELD while the scrape runs (then cleared)."""
    seen_during_run: dict[str, str | None] = {}

    async def _scrape_observing_key(*_args, **_kwargs):
        # The claim must be present at the moment scrape executes.
        seen_during_run["value"] = await patched_gate.cache.get(patched_gate.key)
        return {
            "dimensions": _NEW_DIMS,
            "content_hash": _NEW_HASH,
            "blob_path": "/tmp/b.json",
            "meta_path": "/tmp/b.meta.json",
            "db_inserted": True,
        }

    patched_gate.repo.get_latest.return_value = None
    patched_gate.scrape.side_effect = _scrape_observing_key

    await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert seen_during_run["value"] is not None  # key held during the scrape
    assert await patched_gate.cache.get(patched_gate.key) is None  # cleared after


# ---------------------------------------------------------------------------
# Case 4 — cold FAILURE → exception propagates AND key cleared [load-bearing]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cold_failure_propagates_and_clears_key(patched_gate):
    """A scrape failure propagates; the in-flight key is still released."""
    patched_gate.repo.get_latest.return_value = None
    patched_gate.scrape.side_effect = RuntimeError("akamai blocked")

    with pytest.raises(RuntimeError, match="akamai blocked"):
        await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    # finally released the key even though the body raised.
    assert await patched_gate.cache.get(patched_gate.key) is None


# ---------------------------------------------------------------------------
# Case 5 — category not found → CategoryNotFoundError + key cleared
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_not_found_raises_and_clears_key(patched_gate):
    """Unknown category id raises CategoryNotFoundError; key released."""
    from app.modules.monitor.exceptions import CategoryNotFoundError

    patched_gate.repo.get_latest.return_value = None
    patched_gate.repo.get_inputs.return_value = None  # no categories row

    with pytest.raises(CategoryNotFoundError):
        await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    patched_gate.scrape.assert_not_called()
    assert await patched_gate.cache.get(patched_gate.key) is None


# ---------------------------------------------------------------------------
# Case 6 — PASS / REVIEW_REQUIRED / BLOCK verdicts → correct return,
#          NO notification-table interaction (Wave 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verdict_pass_hash_equal(patched_gate):
    """Identical prior hash → diff short-circuits PASS (hash_equal)."""
    patched_gate.repo.get_latest.return_value = None
    patched_gate.repo.get_prior.return_value = SimpleNamespace(
        dimensions_jsonb=_NEW_DIMS,
        content_hash=_NEW_HASH,  # equal to new → PASS short-circuit
    )

    result = await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert result["action"] == "scraped"
    assert result["verdict"] == "PASS"
    assert result["block_reasons"] == []
    assert await patched_gate.cache.get(patched_gate.key) is None


@pytest.mark.asyncio
async def test_verdict_review_required(patched_gate):
    """A sub-threshold drift yields REVIEW_REQUIRED."""
    prior_dims = {
        "compliance_fields": {"required": ["size"], "optional": []},
        "shipping_slab": {"shipping_charges": 25, "gst_percentage": 5},  # ₹5 drift
        "banned_words": {"branded": []},
        "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0, "sscat_id": _SSCAT_ID},
    }
    patched_gate.repo.get_latest.return_value = None
    patched_gate.repo.get_prior.return_value = SimpleNamespace(
        dimensions_jsonb=prior_dims,
        content_hash="b" * 64,  # different → diff runs
    )

    result = await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert result["verdict"] == "REVIEW_REQUIRED"
    assert result["block_reasons"] == []
    assert await patched_gate.cache.get(patched_gate.key) is None


@pytest.mark.asyncio
async def test_verdict_block_stops_no_fanout(patched_gate, monkeypatch):
    """A BLOCK verdict returns block_reasons and STOPS (no Wave-4 fan-out).

    We force a BLOCK by patching the diff engine's BLOCK threshold so any
    shipping drift trips it — a partial projection would also BLOCK, but we
    exercise the threshold path to keep the new_dims well-formed.
    """
    monkeypatch.setattr(
        patched_gate.diff_mod, "BLOCK_THRESHOLD_SHIPPING_DELTA_INR", 0
    )
    prior_dims = {
        "compliance_fields": {"required": ["size"], "optional": []},
        "shipping_slab": {"shipping_charges": 1, "gst_percentage": 5},  # big drift
        "banned_words": {"branded": []},
        "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0, "sscat_id": _SSCAT_ID},
    }
    patched_gate.repo.get_latest.return_value = None
    patched_gate.repo.get_prior.return_value = SimpleNamespace(
        dimensions_jsonb=prior_dims,
        content_hash="c" * 64,
    )

    result = await monitor_service.run_dedupe_gate(_CATEGORY_ID, db_url=_DB_URL)

    assert result["action"] == "scraped"
    assert result["verdict"] == "BLOCK"
    assert result["block_reasons"]  # non-empty
    # No notification machinery exists in this module — the result is the
    # only side channel (Wave 4 owns fan-out). Key still released.
    assert await patched_gate.cache.get(patched_gate.key) is None
