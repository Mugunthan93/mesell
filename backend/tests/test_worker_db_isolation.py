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
            patch("app.database.create_async_engine", return_value=mock_engine),
            patch("app.database.async_sessionmaker", return_value=mock_session_maker),
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
# 3. image_processor.run_pipeline uses make_worker_session, not the module-
#    level async_session_maker.
# ---------------------------------------------------------------------------

def test_run_pipeline_uses_make_worker_session_not_global_session_maker():
    """run_pipeline must reference make_worker_session, not async_session_maker."""
    import inspect
    import app.services.image_processor as ip_mod

    source = inspect.getsource(ip_mod.run_pipeline)
    assert "make_worker_session" in source, (
        "run_pipeline must use make_worker_session() for Celery-safe DB access"
    )
    assert "async_session_maker" not in source, (
        "run_pipeline must NOT use the module-level async_session_maker "
        "(that pool is unsafe across asyncio.run() calls)"
    )


# ---------------------------------------------------------------------------
# 4. generation_tasks helpers use make_worker_session
# ---------------------------------------------------------------------------

def test_generation_tasks_use_make_worker_session():
    """Both _run_generation and _regenerate_sku must import make_worker_session."""
    import inspect
    import app.workers.generation_tasks as gt_mod

    for fn_name in ("_run_generation", "_regenerate_sku"):
        source = inspect.getsource(getattr(gt_mod, fn_name))
        assert "make_worker_session" in source, (
            f"{fn_name} must use make_worker_session() for Celery-safe DB access"
        )
        assert "async_session_maker" not in source, (
            f"{fn_name} must NOT use the module-level async_session_maker"
        )


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
