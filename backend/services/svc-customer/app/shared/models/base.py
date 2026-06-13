"""Declarative base re-export — canonical model-side import surface.

``Base`` is defined once in :mod:`app.shared.database` and re-exported here
so ORM model files follow ``from app.shared.models.base import Base``.
"""

from app.shared.database import Base

__all__ = ["Base"]
