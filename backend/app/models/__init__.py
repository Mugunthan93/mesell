"""SQLAlchemy ORM models — all 13 V1 tables.

Import order follows the FK dependency chain (MVP_ARCHITECTURE §2.6):
  1. users
  2. seller_profile (→ users)
  3. templates
  4. categories (→ templates)
  5. field_enum_values (→ categories)
  6. field_aliases (standalone)
  7. catalogs (→ users, categories)
  8. products (→ catalogs, categories, users)
  9. product_images (→ products)
  10. pricing_calcs (→ products)
  11. exports (→ products, users)
  12. audit_events (→ users)
  13. product_drafts (→ users, products)

All models use ``from __future__ import annotations`` + TYPE_CHECKING guards
for forward references so that circular imports are resolved at class-body
evaluation time without actually importing the sibling modules.  Importing
this ``__init__.py`` in the correct order causes SQLAlchemy's mapper registry
to see all classes before any relationship is resolved, which is all that is
required for ``relationship()`` string references to work.

``Base`` (the ``DeclarativeBase`` subclass) lives in ``app.database`` and is
re-exported via ``app.models.base``.  Alembic's ``env.py`` imports ``Base``
from here to discover all table metadata for ``--autogenerate``.
"""

# Re-export Base so Alembic env.py can import it from a single location.
from app.models.base import Base  # noqa: F401

# ── 1. Users (no FK deps) ────────────────────────────────────────────────────
from app.models.user import User  # noqa: F401

# ── 2. Seller profile (→ users) ──────────────────────────────────────────────
from app.models.seller_profile import SellerProfile  # noqa: F401

# ── 3. Templates (no FK deps) ────────────────────────────────────────────────
from app.models.template import Template  # noqa: F401

# ── 4. Categories (→ templates) ──────────────────────────────────────────────
from app.models.category import Category  # noqa: F401

# ── 5. Field enum values (→ categories) ──────────────────────────────────────
from app.models.field_enum_value import FieldEnumValue  # noqa: F401

# ── 6. Field aliases (standalone) ────────────────────────────────────────────
from app.models.field_alias import FieldAlias  # noqa: F401

# ── 7. Catalogs (→ users, categories) ────────────────────────────────────────
from app.models.catalog import Catalog  # noqa: F401

# ── 8. Products (→ catalogs, categories, users) ──────────────────────────────
from app.models.product import Product  # noqa: F401

# ── 9. Product images (→ products) ───────────────────────────────────────────
from app.models.product_image import ProductImage  # noqa: F401

# ── 10. Pricing calcs (→ products) ───────────────────────────────────────────
from app.models.pricing_calc import PricingCalc  # noqa: F401

# ── 11. Exports (→ products, users) ──────────────────────────────────────────
from app.models.export import Export  # noqa: F401

# ── 12. Audit events (→ users) ───────────────────────────────────────────────
from app.models.audit_event import AuditEvent  # noqa: F401

# ── 13. Product drafts (→ users, products) ───────────────────────────────────
from app.models.product_draft import ProductDraft  # noqa: F401


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
