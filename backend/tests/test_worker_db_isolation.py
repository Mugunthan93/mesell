"""Tests verifying that worker DB helpers are safe across asyncio.run() calls.

The prefork+asyncio.run() event-loop bug manifests when:
1.  A module-level asyncpg-backed engine holds pooled connections tied to
    loop-A.
2.  asyncio.run() closes loop-A after the first task.
3.  A second asyncio.run() creates loop-B and tries to re-use the connection
    from the pool — the connection's internal Future is still bound to the
    dead loop-A → RuntimeError.

make_worker_session() prevents this by creating a NullPool engine on every
call so no connection object survives past the context-manager exit.

These tests do NOT require a live database — they verify the structural
properties of the fix using mocks so they run in the standard test suite.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. make_worker_session source-level verification: NullPool is referenced
# ---------------------------------------------------------------------------

def test_make_worker_session_uses_nullpool():
    """make_worker_session source must reference NullPool (structural check)."""
    import inspect
    import app.shared.database as db_mod

    source = inspect.getsource(db_mod.make_worker_session)
    assert "NullPool" in source, (
        "make_worker_session must pass poolclass=NullPool to create_async_engine"
    )
    # Also verify that it does NOT simply delegate to async_session_maker
    # (which uses the pooled engine).
    assert "async_session_maker()" not in source, (
        "make_worker_session must not reuse the module-level async_session_maker"
    )


# ---------------------------------------------------------------------------
# 2. Two sequential asyncio.run() calls on make_worker_session don't share
#    connections — structural proof via dispose being called on every exit.
# ---------------------------------------------------------------------------

def test_make_worker_session_disposes_engine_after_each_call():
    """Engine.dispose() is awaited on every make_worker_session exit."""
    dispose_calls: list[int] = []

    async def _single_run(n: int) -> None:
        from app.shared.database import make_worker_session  # fresh import per call

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_maker = MagicMock(return_value=mock_session)

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock(side_effect=lambda: dispose_calls.append(n))

        with (
            patch("app.shared.database.create_async_engine", return_value=mock_engine),
            patch("app.shared.database.async_sessionmaker", return_value=mock_session_maker),
        ):
            async with make_worker_session():
                pass  # session body

    # Run twice in separate asyncio.run() calls — simulating two Celery task
    # executions in the same prefork worker process.
    asyncio.run(_single_run(1))
    asyncio.run(_single_run(2))

    assert dispose_calls == [1, 2], (
        f"Expected engine disposed twice (once per asyncio.run), got: {dispose_calls}"
    )


# ---------------------------------------------------------------------------
# 3. (RETIRED 2026-06-09 — V0-rot cleanup)
#    The original test #3 asserted that ``app.services.image_processor``'s
#    ``run_pipeline`` used ``make_worker_session``.  Both the V0 ``app.services``
#    package and its ``image_processor`` module were deleted in the pre-§22 §3
#    audit (V0-rot purge).  The V1 image pipeline lives at
#    ``app/modules/image/tasks.py`` and its worker-session posture is covered by
#    the §11 image module test suite.  This structural assertion no longer
#    applies and was removed to keep collection clean.
#
# 4. (RETIRED 2026-06-08 by §18 sub-session)
#    app/workers/generation_tasks.py was a V0 leftover deleted in session 2
#    final purge, accidentally restored, and re-deleted by §18 construction
#    when populating ``workers/celery_app.py``.  The §3.I canonical workers/
#    subtree contains exactly 2 files (``__init__.py`` + ``celery_app.py``);
#    no ``generation_tasks.py`` exists in V1.  The original test that
#    verified ``generation_tasks._run_generation`` / ``_regenerate_sku``
#    used ``make_worker_session`` is no longer applicable.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. FastAPI get_db still uses the pooled engine (unchanged)
# ---------------------------------------------------------------------------

def test_get_db_still_uses_pooled_engine():
    """The FastAPI get_db dependency must continue to use the pooled engine."""
    import inspect
    import app.shared.database as db_mod

    source = inspect.getsource(db_mod.get_db)
    assert "async_session_maker" in source, (
        "get_db (FastAPI dependency) must still use async_session_maker "
        "backed by the pooled engine"
    )
    assert "make_worker_session" not in source, (
        "get_db must NOT use make_worker_session — NullPool is wasteful for "
        "the long-lived FastAPI process"
    )


# ---------------------------------------------------------------------------
# 6. Simulate two sequential asyncio.run() calls with a fully mocked pipeline
#    to confirm no 'attached to a different loop' error surfaces.
# ---------------------------------------------------------------------------

def test_two_sequential_asyncio_run_calls_do_not_raise_loop_error():
    """Two back-to-back asyncio.run() calls with mocked DB must not raise loop errors."""
    import app.shared.database as db_mod

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_maker = MagicMock(return_value=mock_session)
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()

    iid = uuid.uuid4()

    with (
        patch.object(db_mod, "create_async_engine", return_value=mock_engine),
        patch.object(db_mod, "async_sessionmaker", return_value=mock_session_maker),
    ):
        async def _fake_pipeline() -> dict:
            async with db_mod.make_worker_session():
                await asyncio.sleep(0)
            return {"image_id": str(iid)}

        # Two calls — each creates and closes its own event loop.
        result1 = asyncio.run(_fake_pipeline())
        result2 = asyncio.run(_fake_pipeline())

    assert result1["image_id"] == str(iid)
    assert result2["image_id"] == str(iid)
