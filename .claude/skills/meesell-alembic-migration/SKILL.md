---
name: meesell-alembic-migration
description: >-
  MeeSell's canonical conventions for SQLAlchemy 2.0 async ORM models and Alembic
  migrations. Use this skill WHENEVER you are creating or editing a database model,
  table, column, index, relationship, or writing/reviewing an Alembic migration in the
  MeeSell backend (backend/app/models/, backend/alembic/) — even if the user only says
  "add a table", "add a column", "change the schema", "create a migration", or names a
  data-model change without saying "Alembic". Apply it for UUID PKs, TIMESTAMPTZ, JSONB,
  indexing, and the nullable-identity auth constraints. Do NOT use it for API route
  shapes (defer to the fastapi-router skill).
---

# MeeSell Database & Migration Conventions

These are the locked conventions for every table and migration in MeeSell. They exist so
the schema is consistent, timezone-correct, multi-tenant-safe, and so migrations apply
cleanly on the self-hosted Postgres 16 (trimmed Supabase image) on K3s. They derive from
`CLAUDE.md` "Database" + Key Decisions #5/#14/#15, which win over any other guidance.

## The non-negotiables (and why each matters)

- **UUID primary keys via `gen_random_uuid()`.** Never auto-increment integers. UUIDs
  avoid cross-tenant ID guessing and let us generate IDs client-side or across services
  without a round-trip.

- **`TIMESTAMPTZ` for every timestamp.** Always timezone-aware. Indian sellers, GCP
  asia-south1, and any future region must agree on instants — a naive timestamp is a bug
  waiting to happen at IST/UTC boundaries.

- **`JSONB` for flexible structured data.** Use it for `ai_attributes`, `quality_checks`,
  and similar evolving shapes — but index the keys you actually query (GIN or expression
  index), never leave a hot JSONB filter unindexed.

- **Index every foreign key and every frequently-queried column.** Postgres does NOT
  auto-index FKs. An unindexed FK turns a tenant-scoped list query into a seq scan.

- **One migration per feature-group change, descriptive message.** Don't bundle unrelated
  schema changes; don't leave the message as "migration". The message is the changelog.

- **Async SQLAlchemy 2.0 only.** Models use the 2.0 declarative style with
  `Mapped[...]`/`mapped_column(...)`. Queries run through `AsyncSession`. No legacy
  `Query` API, no sync sessions.

- **No raw SQL in routes/services.** Go through the ORM or the service layer. Raw SQL
  scattered in handlers bypasses tenant scoping and is unreviewable.

## Auth identity constraints (Decision #5 + 2026-06-18 amendment)

The `iam.users` table is dual-identity (phone OR Google). When touching it, preserve:

- `phone` is **nullable-unique** (Google-only users have `phone = NULL`).
- `email` has a **nullable-UNIQUE** linking constraint.
- `google_sub` is a **nullable-UNIQUE** column; `auth_provider` is an audit column.
- A **table-level CHECK** guarantees `phone IS NOT NULL OR google_sub IS NOT NULL` — a row
  with neither identity is invalid. Never drop this CHECK in a migration.

## Standard model skeleton (SQLAlchemy 2.0 async)

```python
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Catalog(Base):
    __tablename__ = "catalogs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    ai_attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

Note: `index=True` on `user_id` (the FK) and `status` (queried in list filters). The
`created_at`/`updated_at` pair is `TIMESTAMPTZ` with server-side defaults.

## Migration authoring

- Autogenerate as a starting point, then **read the generated migration** — autogen
  misses server defaults, CHECK constraints, JSONB indexes, and enum changes.
- Provide a real `downgrade()` — a migration you can't reverse is a migration you can't
  safely deploy.
- For data backfills, do them in a separate, idempotent migration step, not mixed with
  DDL that locks the table.
- Descriptive message, e.g. `alembic revision -m "add google_sub + auth_provider to users"`.

```python
def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])
    op.create_check_constraint(
        "ck_users_identity",
        "users",
        "phone IS NOT NULL OR google_sub IS NOT NULL",
    )

def downgrade() -> None:
    op.drop_constraint("ck_users_identity", "users", type_="check")
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
```

## Quick checklist before you finish a model or migration

- [ ] PK is `UUID` with `gen_random_uuid()` server default
- [ ] All timestamps are `TIMESTAMPTZ` (timezone-aware)
- [ ] Every FK and hot filter column has an index
- [ ] Flexible data is `JSONB`, with an index on queried keys
- [ ] SQLAlchemy 2.0 `Mapped`/`mapped_column`, async-safe
- [ ] `iam.users` identity CHECK + nullable-unique constraints preserved
- [ ] Migration has a descriptive message and a working `downgrade()`
- [ ] Data backfills are separate + idempotent from DDL
- [ ] No raw SQL leaking into routes/services
