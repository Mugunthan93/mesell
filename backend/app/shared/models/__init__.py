"""ORM model registry — the 13 V1 tables.

Per BACKEND_ARCHITECTURE.md §5.E + §3.E, this package is the **single
canonical import surface** for any ORM model class in the codebase::

    from app.shared.models import (
        User, SellerProfile, Template, Category, FieldEnumValue, FieldAlias,
        Catalog, Product, ProductImage, PricingCalc, Export, AuditEvent,
        ProductDraft,
    )

Locked rules (§5.E)
-------------------
* NO module redefines a model.
* NO module imports from another module's ``repository.py`` to obtain a model
  class.  Repositories own queries; models live here.
* Even if a ``catalog/repository.py`` query incidentally returns a
  ``Category`` instance through a join, it returns the registry's
  ``Category`` class — the same class every other module sees.

Import order (locked verbatim)
------------------------------
Follows the FK dependency chain per MVP_ARCHITECTURE §2.6:

  1.  users               (no FK deps)
  2.  seller_profile      (→ users)
  3.  templates           (no FK deps)
  4.  categories          (→ templates)
  5.  field_enum_values   (→ categories)
  6.  field_aliases       (standalone)
  7.  catalogs            (→ users, categories)
  8.  products            (→ catalogs, categories, users)
  9.  product_images      (→ products)
  10. pricing_calcs       (→ products)
  11. exports             (→ products, users)
  12. audit_events        (→ users)
  13. product_drafts      (→ users, products)

All models use ``from __future__ import annotations`` + ``TYPE_CHECKING``-
guarded forward references so that sibling imports are deferred to
mapper-configuration time.  Importing this ``__init__.py`` in this order
makes SQLAlchemy's mapper registry see every class before any relationship
string is resolved, which is all that ``relationship("ClassName", ...)``
requires.

Base class
----------
``Base = DeclarativeBase`` lives in :mod:`app.shared.database` (per §5.B)
and is re-exported by :mod:`app.shared.models.base` for backward
compatibility with the model-side import convention.  Alembic's ``env.py``
imports ``Base`` from here.
"""

# Re-export Base so Alembic env.py + tests can import from a single location.
from app.shared.models.base import Base  # noqa: F401

# ── 1. Users (no FK deps) ───────────────────────────────────────────────────
from app.shared.models.user import User  # noqa: F401

# ── 2. Seller profile (→ users) ─────────────────────────────────────────────
from app.shared.models.seller_profile import SellerProfile  # noqa: F401

# ── 3. Templates (no FK deps) ───────────────────────────────────────────────
from app.shared.models.template import Template  # noqa: F401

# ── 4. Categories (→ templates) ─────────────────────────────────────────────
from app.shared.models.category import Category  # noqa: F401

# ── 5. Field enum values (→ categories) ─────────────────────────────────────
from app.shared.models.field_enum_value import FieldEnumValue  # noqa: F401

# ── 6. Field aliases (standalone) ───────────────────────────────────────────
from app.shared.models.field_alias import FieldAlias  # noqa: F401

# ── 7. Catalogs (→ users, categories) ───────────────────────────────────────
from app.shared.models.catalog import Catalog  # noqa: F401

# ── 8. Products (→ catalogs, categories, users) ─────────────────────────────
from app.shared.models.product import Product  # noqa: F401

# ── 9. Product images (→ products) ──────────────────────────────────────────
from app.shared.models.product_image import ProductImage  # noqa: F401

# ── 10. Pricing calcs (→ products) ──────────────────────────────────────────
from app.shared.models.pricing_calc import PricingCalc  # noqa: F401

# ── 11. Exports (→ products, users) ─────────────────────────────────────────
from app.shared.models.export import Export  # noqa: F401

# ── 12. Audit events (→ users) ──────────────────────────────────────────────
from app.shared.models.audit_event import AuditEvent  # noqa: F401

# ── 13. Product drafts (→ users, products) ──────────────────────────────────
from app.shared.models.product_draft import ProductDraft  # noqa: F401


__all__ = [
    "Base",
    # Identity
    "User",
    "SellerProfile",
    # Schema storage
    "Template",
    "Category",
    "FieldEnumValue",
    "FieldAlias",
    # Catalog wizard
    "Catalog",
    "Product",
    "ProductImage",
    # Pricing & exports
    "PricingCalc",
    "Export",
    # Audit & autosave
    "AuditEvent",
    "ProductDraft",
]
