"""Image ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    processed_url: Mapped[str | None] = mapped_column(Text)
    bg_removed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    resized: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    file_size_kb: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str | None] = mapped_column(String(10))
    has_watermark: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_compliant: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    compliance_note: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    sku: Mapped["SKU"] = relationship(back_populates="images")
