"""SKU (product variant) ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SKU(Base):
    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    weight_grams: Mapped[int | None] = mapped_column(Integer)
    material: Mapped[str | None] = mapped_column(String(100))
    sizes: Mapped[str | None] = mapped_column(String(255))
    colors: Mapped[str | None] = mapped_column(String(255))

    ai_title: Mapped[str | None] = mapped_column(Text)
    ai_description: Mapped[str | None] = mapped_column(Text)
    ai_keywords: Mapped[str | None] = mapped_column(Text)
    ai_category: Mapped[str | None] = mapped_column(String(100))
    ai_attributes: Mapped[dict | None] = mapped_column(JSONB)

    margin_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    return_provision: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    quality_checks: Mapped[dict | None] = mapped_column(JSONB)
    quality_score: Mapped[int | None] = mapped_column(Integer)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    catalog: Mapped["Catalog"] = relationship(back_populates="skus")
    images: Mapped[list["Image"]] = relationship(
        back_populates="sku", cascade="all, delete-orphan"
    )
