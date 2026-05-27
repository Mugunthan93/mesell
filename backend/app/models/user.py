"""User ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'free'"))
    plan_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    razorpay_sub_id: Mapped[str | None] = mapped_column(String(64))
    catalogs_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    catalogs_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )

    catalogs: Mapped[list["Catalog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    exports: Mapped[list["Export"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
