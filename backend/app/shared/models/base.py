"""Declarative base re-export — canonical model-side import surface.

Per BACKEND_ARCHITECTURE.md §5.E, ``Base`` is defined once in
:mod:`app.shared.database` and re-exported here so that ORM model files can
follow the convention::

    from app.shared.models.base import Base

without dragging in the engine / session machinery declared alongside.

Alembic's ``env.py`` imports ``Base`` from here (or directly from
``app.shared.database`` — both paths resolve to the same class object) to
discover all table metadata for ``--autogenerate``.
"""

from app.shared.database import Base

__all__ = ["Base"]
