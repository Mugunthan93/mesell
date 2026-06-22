"""Tests for scrape_category.py — Unit A of the category change monitor.

NON-LIVE CONTRACT:
    NO test opens a live ctx.request to *.meesho.com.
    ctx.request is mocked entirely via the _ctx parameter injection point.
    The disposable test DB (TEST_DATABASE_URL env var, must end in _test)
    is used for the DB-insert test — NEVER the live meesell dev DB.

Test cases:
    1. test_projection_extraction — mock ctx returns fixture; assert all four
       dimensions present + correctly populated.
    2. test_content_hash_deterministic — same input → same hash on two runs.
    3. test_content_hash_stable_across_runs — two calls with identical dimensions
       yield byte-identical hashes (hash is deterministic).
    4. test_blob_and_meta_written — blob + .meta.json exist in the tmp snapshot dir.
    5. test_hard_stop_403_no_row — mock ctx returns HTTP 403; assert AkamaiBlockedError
       raised + NO row written to a tmp dir (no snapshot file produced).
    6. test_hard_stop_429_no_row — same as above for HTTP 429.
    7. test_db_insert_on_test_db — (skipped when TEST_DATABASE_URL not set or not
       ending in _test) inserts a row and reads it back.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.scrape_category import (  # type: ignore[import]
    AkamaiBlockedError,
    compute_content_hash,
    scrape_category,
)

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------
# Fixtures live at tests/fixtures/category_monitor/ (one level above tests/scripts/)
_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "category_monitor"
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_CATEGORY_ATTRS = _BACKEND_DIR / "app" / "data" / "category_attributes.json"
_BANNED_WORDS = _BACKEND_DIR / "app" / "data" / "banned_words.json"

# Stable test IDs
_SSCAT_ID = "46677c24"
_CATEGORY_NAME = "Kurtis"


# ---------------------------------------------------------------------------
# Mock ctx.request helper
# ---------------------------------------------------------------------------


def _make_mock_ctx(response_json: dict[str, Any], status: int = 200) -> MagicMock:
    """Build a MagicMock that mimics playwright's BrowserContext.request.post.

    Returns a mock ctx where ctx.request.post(...) returns a mock APIResponse
    with the given status and JSON body.  All calls are async.
    """
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=response_json)

    mock_request = MagicMock()
    mock_request.post = AsyncMock(return_value=mock_response)

    mock_ctx = MagicMock()
    mock_ctx.request = mock_request

    return mock_ctx


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test DB helper
# ---------------------------------------------------------------------------


def _get_test_db_url() -> str | None:
    """Return TEST_DATABASE_URL only if it points at a *_test database."""
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        return None
    db_name = url.rsplit("/", 1)[-1].split("?")[0]
    if not db_name.endswith("_test"):
        return None
    return url


# ---------------------------------------------------------------------------
# DB-insert fixture: seeds the FK chain templates -> categories
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_category_id() -> str:
    """Insert one Template + one Category row into the disposable test DB.

    Seeds the minimum FK chain required by category_snapshots.category_id:
        templates  (no FK parent)
        categories (template_id -> templates.id, NOT NULL)

    Yields the seeded category UUID as a string.  After the test the rows
    are removed (DELETE by primary key) so the fixture is idempotent across
    repeated runs.

    Skipped when TEST_DATABASE_URL is not set or does not end in ``_test``.
    """
    db_url = _get_test_db_url()
    if db_url is None:
        pytest.skip(
            "TEST_DATABASE_URL not set or does not end in _test — skipping live DB test"
        )

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlalchemy import text

    engine = create_async_engine(db_url, poolclass=NullPool)

    template_id = uuid.uuid4()
    category_id = uuid.uuid4()
    schema_hash = uuid.uuid4().hex  # unique random hash for deduplication uniqueness

    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(
                    text(
                        "INSERT INTO templates "
                        "(id, schema_hash, schema_jsonb, compliance_shape, "
                        "parsed_from_xlsx_at, parser_version) "
                        "VALUES (:id, :schema_hash, CAST(:schema_jsonb AS jsonb), "
                        "'standard', NOW(), '0.2')"
                    ),
                    {
                        "id": template_id,
                        "schema_hash": schema_hash,
                        "schema_jsonb": '{"fields":[],"compulsory_count":0,"optional_count":0,'
                                        '"total_count":0,"wizard_step_count":1,"main_sheet_label":"Test"}',
                    },
                )
                await session.execute(
                    text(
                        "INSERT INTO categories "
                        "(id, meesho_leaf_id, super_id, super_name, path, leaf_name, "
                        "template_id, created_at) "
                        "VALUES (:id, :meesho_leaf_id, '11', 'Women Fashion', "
                        "'Women Fashion > Kurtis', 'Kurtis', :template_id, NOW())"
                    ),
                    {
                        "id": category_id,
                        "meesho_leaf_id": f"test_{category_id.hex[:8]}",
                        "template_id": template_id,
                    },
                )

        yield str(category_id)

    finally:
        # Clean up seeded rows (CASCADE deletes any snapshot rows too)
        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(
                    text("DELETE FROM categories WHERE id = :id"),
                    {"id": category_id},
                )
                await session.execute(
                    text("DELETE FROM templates WHERE id = :id"),
                    {"id": template_id},
                )
        await engine.dispose()


# ---------------------------------------------------------------------------
# Test 1: projection extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_projection_extraction(tmp_path: Path) -> None:
    """Mock ctx returns the recorded raw fixture; assert all four dimensions present."""
    raw = _load_fixture("cat_46677c24_raw.json")
    mock_ctx = _make_mock_ctx(raw)

    result = await scrape_category(
        category_id=str(uuid.uuid4()),
        sscat_id=_SSCAT_ID,
        category_name=_CATEGORY_NAME,
        db_url=None,
        snapshot_dir=tmp_path,
        _ctx=mock_ctx,
    )

    dims = result["dimensions"]

    # All four dimensions must be present
    assert "compliance_fields" in dims, "compliance_fields dimension missing"
    assert "shipping_slab" in dims, "shipping_slab dimension missing"
    assert "banned_words" in dims, "banned_words dimension missing"
    assert "cost_fields" in dims, "cost_fields dimension missing"

    # compliance_fields from corpus (Kurtis category)
    assert "required" in dims["compliance_fields"], "compliance_fields.required missing"

    # shipping_slab from live fixture
    assert "shipping_charges" in dims["shipping_slab"]
    assert "gst_percentage" in dims["shipping_slab"]
    assert dims["shipping_slab"]["shipping_charges"] == raw["shipping_charges"]
    assert dims["shipping_slab"]["gst_percentage"] == raw["gst_percentage"]

    # cost_fields from live fixture
    assert "transfer_price" in dims["cost_fields"]
    assert dims["cost_fields"]["transfer_price"] == float(raw["transfer_price"])
    assert dims["cost_fields"]["sscat_id"] == _SSCAT_ID

    # banned_words from corpus (non-empty)
    assert isinstance(dims["banned_words"], dict)
    assert len(dims["banned_words"]) > 0, "banned_words should not be empty"

    # content_hash must be a 64-char hex string
    assert len(result["content_hash"]) == 64
    assert all(c in "0123456789abcdef" for c in result["content_hash"])


# ---------------------------------------------------------------------------
# Test 2: content_hash deterministic — same input same hash
# ---------------------------------------------------------------------------


def test_content_hash_deterministic() -> None:
    """Same dimensions dict → byte-identical hash on every call."""
    dims: dict[str, Any] = {
        "compliance_fields": {"required": ["fabric", "fit"], "optional": ["wash_care"]},
        "shipping_slab": {"shipping_charges": 55, "gst_percentage": 5},
        "banned_words": {"branded": ["nike"], "trademark": ["patented"]},
        "cost_fields": {"transfer_price": 68.0, "platform_fee": 0.0, "sscat_id": "46677c24"},
    }

    h1 = compute_content_hash(dims)
    h2 = compute_content_hash(dims)

    assert h1 == h2, "content_hash must be deterministic for identical inputs"
    assert len(h1) == 64, "SHA-256 hex must be 64 chars"


# ---------------------------------------------------------------------------
# Test 3: content_hash stable — identical-value dict with different key order
# Same canonical JSON (sort_keys=True) must produce the same hash
# ---------------------------------------------------------------------------


def test_content_hash_stable_key_order() -> None:
    """Key order in the input dict must NOT affect the hash (sort_keys=True)."""
    dims_a: dict[str, Any] = {
        "compliance_fields": {"required": ["fabric"], "optional": []},
        "shipping_slab": {"shipping_charges": 55, "gst_percentage": 5},
        "banned_words": {"branded": ["nike"]},
        "cost_fields": {"transfer_price": 68.0, "platform_fee": 0.0, "sscat_id": "46677c24"},
    }
    # Build the same dict in reversed key order
    dims_b: dict[str, Any] = {
        "cost_fields": {"sscat_id": "46677c24", "platform_fee": 0.0, "transfer_price": 68.0},
        "banned_words": {"branded": ["nike"]},
        "shipping_slab": {"gst_percentage": 5, "shipping_charges": 55},
        "compliance_fields": {"optional": [], "required": ["fabric"]},
    }

    assert compute_content_hash(dims_a) == compute_content_hash(dims_b), (
        "content_hash must be stable regardless of key ordering in the input dict"
    )


# ---------------------------------------------------------------------------
# Test 4: blob + meta written
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blob_and_meta_written(tmp_path: Path) -> None:
    """After scrape_category(), blob file + .meta.json sidecar must exist."""
    raw = _load_fixture("cat_46677c24_raw.json")
    mock_ctx = _make_mock_ctx(raw)

    result = await scrape_category(
        category_id=str(uuid.uuid4()),
        sscat_id=_SSCAT_ID,
        category_name=_CATEGORY_NAME,
        db_url=None,
        snapshot_dir=tmp_path,
        _ctx=mock_ctx,
    )

    blob_path = result["blob_path"]
    meta_path = result["meta_path"]

    assert blob_path.exists(), f"Blob file not written: {blob_path}"
    assert meta_path.exists(), f"Meta sidecar not written: {meta_path}"

    # Blob must be valid JSON with all four dimension keys
    blob_data = json.loads(blob_path.read_text(encoding="utf-8"))
    for key in ("compliance_fields", "shipping_slab", "banned_words", "cost_fields"):
        assert key in blob_data, f"Blob JSON missing key: {key}"

    # Meta sidecar must contain category_id, captured_at, content_hash
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "captured_at" in meta_data
    assert meta_data["content_hash"] == result["content_hash"]


# ---------------------------------------------------------------------------
# Test 5: hard stop on HTTP 403 — no row, no blob
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_stop_403_no_row(tmp_path: Path) -> None:
    """Mock ctx returns HTTP 403 → AkamaiBlockedError raised; no blob written."""
    category_id = str(uuid.uuid4())

    mock_response = MagicMock()
    mock_response.status = 403

    mock_request = MagicMock()
    mock_request.post = AsyncMock(return_value=mock_response)

    mock_ctx = MagicMock()
    mock_ctx.request = mock_request

    with pytest.raises(AkamaiBlockedError):
        await scrape_category(
            category_id=category_id,
            sscat_id=_SSCAT_ID,
            category_name=_CATEGORY_NAME,
            db_url=None,
            snapshot_dir=tmp_path,
            _ctx=mock_ctx,
        )

    # No blob should have been written (exception raised before write)
    blob_path = tmp_path / f"cat_{category_id}.json"
    assert not blob_path.exists(), "Blob MUST NOT be written on a hard stop"


# ---------------------------------------------------------------------------
# Test 6: hard stop on HTTP 429 — no row, no blob
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_stop_429_no_row(tmp_path: Path) -> None:
    """Mock ctx returns HTTP 429 → AkamaiBlockedError raised; no blob written."""
    category_id = str(uuid.uuid4())

    mock_response = MagicMock()
    mock_response.status = 429

    mock_request = MagicMock()
    mock_request.post = AsyncMock(return_value=mock_response)

    mock_ctx = MagicMock()
    mock_ctx.request = mock_request

    with pytest.raises(AkamaiBlockedError):
        await scrape_category(
            category_id=category_id,
            sscat_id=_SSCAT_ID,
            category_name=_CATEGORY_NAME,
            db_url=None,
            snapshot_dir=tmp_path,
            _ctx=mock_ctx,
        )

    blob_path = tmp_path / f"cat_{category_id}.json"
    assert not blob_path.exists(), "Blob MUST NOT be written on a rate-limit hard stop"


# ---------------------------------------------------------------------------
# Test 7: DB insert (skipped when TEST_DATABASE_URL not available)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_insert_on_test_db(tmp_path: Path, seeded_category_id: str) -> None:
    """Insert a category_snapshots row into the test DB and read it back.

    Uses a real seeded category_id (from the seeded_category_id fixture) so
    the FK constraint on category_snapshots.category_id is satisfied.  The
    seeded rows (template + category) are cleaned up by the fixture teardown.
    """
    db_url = _get_test_db_url()
    assert db_url is not None  # seeded_category_id fixture already skips if None

    raw = _load_fixture("cat_46677c24_raw.json")
    mock_ctx = _make_mock_ctx(raw)

    result = await scrape_category(
        category_id=seeded_category_id,
        sscat_id=_SSCAT_ID,
        category_name=_CATEGORY_NAME,
        db_url=db_url,
        snapshot_dir=tmp_path,
        _ctx=mock_ctx,
    )

    assert result["db_inserted"] is True, "DB insert must succeed on a valid test DB"

    # Read back the row to verify
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlalchemy import text

    engine = create_async_engine(db_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine) as session:
            # Verify row exists with correct hash
            row_result = await session.execute(
                text(
                    "SELECT content_hash FROM category_snapshots WHERE category_id = :cid "
                    "ORDER BY captured_at DESC LIMIT 1"
                ),
                {"cid": seeded_category_id},
            )
            row = row_result.fetchone()
            assert row is not None, "Row must be present after insert"
            assert row[0] == result["content_hash"], "Stored hash must match computed hash"
    finally:
        await engine.dispose()
