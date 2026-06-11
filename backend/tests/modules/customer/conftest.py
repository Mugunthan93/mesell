"""Customer-module test fixtures.

Provides the ``db`` fixture used by the §8.J unit tests.  The customer
unit tests intentionally run against the **ephemeral test DB** (port
5432, the ``db_session`` fixture in the top-level conftest), NOT the
live dev tunnel at port 5433 used by the iam unit tests.  Rationale:

  * The customer suite does NOT consume seeded categories — it
    bypasses the ``categories.super_id`` set validation via the
    repository helpers, which are written to work against an empty
    ``categories`` table.
  * The dev tunnel is operator-dependent (requires an SSH session).
    Tying the customer suite to it would block CI runs whenever the
    tunnel drops.

The fixture is named ``db`` so the per-test signatures match the §8.J
prose verbatim.  It is a thin alias over the upstream ``db_session``
fixture from ``tests/conftest.py``.
"""

from __future__ import annotations

import pytest_asyncio


@pytest_asyncio.fixture(loop_scope="function")
async def db(db_session):
    """Alias for the ephemeral test DB session.

    Backs onto the top-level ``db_session`` fixture which:

      1. Creates a fresh engine against ``DATABASE_URL`` (defaults to
         the local Postgres on port 5432 per conftest).
      2. ``Base.metadata.drop_all`` + ``create_all`` for a clean slate.
      3. Yields an ``AsyncSession`` bound to that engine.

    Tests treat this as the canonical "DB session" handle; they do
    NOT commit (the session goes away at teardown).  Service-layer
    calls under test use ``await session.flush()`` semantics implicitly
    via the repository implementations.
    """
    yield db_session
