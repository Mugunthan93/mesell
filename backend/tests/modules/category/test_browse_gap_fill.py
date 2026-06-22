"""CAT-BE-11 / CAT-BE-12 / CAT-BE-13 / CAT-BE-14
Gap-fill for ``GET /categories/browse``.

What this file adds (does NOT duplicate test_trigram_*.py):
- CAT-BE-11  super_id filter narrows results to that super
- CAT-BE-12  limit>100 → 422 (FastAPI validates) with NON-EMPTY detail
- CAT-BE-13  q with no match → 200, empty list, total=0
- CAT-BE-14  no q → browse-all happy → 200, non-empty first page

Tests use the live DB (``db`` fixture) so the seeded category tree is present.
They skip gracefully when the seed is absent (CI schema-only).
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app


pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class _StubUser:
    user_id: object
    plan: str = "free"


def _stub_user_dep():
    return _StubUser(user_id=uuid.uuid4())


@asynccontextmanager
async def _make_client():
    app.dependency_overrides[get_current_user] = _stub_user_dep
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-12  limit > 100 → 422 (FastAPI query-param validation)
# ─────────────────────────────────────────────────────────────────────────────

async def test_browse_invalid_pagination_422(use_live_valkey):
    """CAT-BE-12: limit=101 exceeds the declared max(100) → 422 with non-empty detail."""
    async with _make_client() as ac:
        resp = await ac.get(
            "/api/v1/categories/browse",
            params={"limit": 101},
        )

    assert resp.status_code == 422, (
        f"Expected 422 for limit=101, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail") or body.get("validation_message_id")
    assert detail, (
        f"422 body must carry a non-empty detail; got {body}"
    )


async def test_browse_invalid_offset_422(use_live_valkey):
    """CAT-BE-12b: offset=-1 → 422 (FastAPI ge=0 constraint)."""
    async with _make_client() as ac:
        resp = await ac.get(
            "/api/v1/categories/browse",
            params={"offset": -1},
        )

    assert resp.status_code == 422, (
        f"Expected 422 for offset=-1, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail") or body.get("validation_message_id")
    assert detail, f"422 body must carry a non-empty detail; got {body}"


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-13  q with no trigram match → 200, empty results, total=0
# ─────────────────────────────────────────────────────────────────────────────

async def test_browse_no_match_returns_empty_list(db, use_live_valkey):
    """CAT-BE-13: a gibberish q that can't match any category → 200, [] results."""
    # Check seed presence — skip if schema-only CI.
    from sqlalchemy import text as _text
    async with db:
        row = await db.execute(_text("SELECT COUNT(*) FROM categories"))
        count = row.scalar_one()
    if count == 0:
        pytest.skip("categories not seeded — CI schema-only; skip CAT-BE-13")

    async with _make_client() as ac:
        resp = await ac.get(
            "/api/v1/categories/browse",
            params={"q": "xyzzyqqqzxzxzqqqzzq999zzz_nomatch"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    results = body.get("results") or body.get("categories") or body.get("items") or []
    total = body.get("total", -1)
    assert results == [], (
        f"Expected empty results for no-match q, got {results}"
    )
    assert total == 0, (
        f"Expected total=0 for no-match q, got total={total}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-14  no q → browse-all happy → 200, non-empty results
# ─────────────────────────────────────────────────────────────────────────────

async def test_browse_no_q_returns_first_page(db, use_live_valkey):
    """CAT-BE-14: GET /categories/browse without q → 200, first-page categories."""
    # Check seed presence.
    from sqlalchemy import text as _text
    async with db:
        row = await db.execute(_text("SELECT COUNT(*) FROM categories"))
        count = row.scalar_one()
    if count == 0:
        pytest.skip("categories not seeded — CI schema-only; skip CAT-BE-14")

    async with _make_client() as ac:
        resp = await ac.get(
            "/api/v1/categories/browse",
            params={"limit": 10},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    results = body.get("results") or body.get("categories") or body.get("items") or []
    assert len(results) > 0, (
        f"Expected at least one category when no q; got empty results: {body}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-11  super_id filter narrows results
# ─────────────────────────────────────────────────────────────────────────────

async def test_browse_super_id_filter_narrows_results(db, use_live_valkey):
    """CAT-BE-11: super_id filter returns only leaves from that super-category."""
    from sqlalchemy import text as _text

    # Discover a real super_id with >0 leaves.
    # (All entries in categories table are leaf categories — no is_leaf column.)
    async with db:
        row = await db.execute(
            _text(
                "SELECT super_id FROM categories "
                "GROUP BY super_id "
                "ORDER BY COUNT(*) DESC LIMIT 1"
            )
        )
        result = row.fetchone()

    if result is None:
        pytest.skip("categories not seeded — CI schema-only; skip CAT-BE-11")

    real_super_id = result[0]

    async with _make_client() as ac:
        resp = await ac.get(
            "/api/v1/categories/browse",
            params={"super_id": real_super_id, "limit": 5},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    results = body.get("results") or body.get("categories") or body.get("items") or []

    # All returned items must belong to the requested super.
    for item in results:
        item_super = item.get("super_id")
        assert str(item_super) == str(real_super_id), (
            f"super_id filter broken: expected {real_super_id!r}, got {item_super!r}"
            f" in item {item}"
        )
