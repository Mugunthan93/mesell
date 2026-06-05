"""Declarative base re-export.

All ORM models import ``Base`` from here (or directly from ``app.database``).
Both paths are equivalent — ``Base`` is defined once in ``app.database`` and
re-exported here for convenience.
"""

from app.database import Base

__all__ = ["Base"]
