# Wave 1 — Database Layer Task Spec (Razorpay Integration, V1.5)

**Feature slug:** `razorpay-integration`
**Wave:** 1 of 5 (DATA MODEL ONLY)
**Target specialist:** `meesell-database-builder` (sonnet)
**Session name (dispatch header):** `mesell-razorpay-integration-backend-session-1`
**Authored by:** `meesell-backend-coordinator`
**Date:** 2026-06-19
**Parent design (LOCKED):** `docs/plans/features/razorpay-integration/RAZORPAY_INTEGRATION_SPEC.md` rev v4 (APPROVED 2026-06-18) §3.1, §7, §7.4a, §14 Wave 1; `docs/PRICING_LOCKED.md` v2 §5, §5.1.

---

## 0. CRITICAL CORRECTION vs the design spec — read first

The RAZORPAY_INTEGRATION_SPEC (§7, §7.4, §14 Wave 1) repeatedly states the Alembic parent is **`f31c75438e61`**. **That is STALE.** Verified against the live `backend/alembic/versions/` tree on 2026-06-19:

```
935e55b4852c (baseline, 13 tables)
  → a1b2c3d4e5f6 (pg_trgm + category GIN)
    → f31c75438e61 (idx product_drafts saved_at)
      → b7c2e1a9d3f4 (pricing_calcs forward-estimator columns)   ← CURRENT HEAD
```

A newer migration `b7c2e1a9d3f4` (pricing_calcs forward-estimator columns, created 2026-06-18) landed AFTER the spec was written and its `down_revision = "f31c75438e61"`. Confirmed single head — no descendant of `b7c2e1a9d3f4` exists.

**THE MIGRATION PARENT (`down_revision`) MUST BE `b7c2e1a9d3f4`, NOT `f31c75438e61`.** Using `f31c75438e61` would create head divergence (two migrations both pointing at `f31c75438e61`) — a P0 blocker. Confirm the head yourself with `alembic heads` before generating; if a still-newer migration has landed by your dispatch time, use the THEN-current single head and note the change in your PR.

Second correction: the live `users.plan` column has **NO CHECK constraint today** — only the column comment `'free | pro'`. Plan values are enforced application-side. This Wave ADDS a brand-new CHECK constraint (it is not an "ALTER existing CHECK" — there is nothing to drop on upgrade; downgrade simply drops the new constraint).

---

## 1. Scope of Wave 1 (exactly this, nothing more)

Build the database layer for billing:

1. Three net-new ORM models + tables: `subscriptions`, `payments`, `webhook_events`.
2. `users` changes: add `trial_ends_at TIMESTAMPTZ NULL` (the ONLY new `users` column) + add a CHECK constraint widening the allowed `plan` vocabulary to the Pricing v2 set + update the column comment.
3. One Alembic migration (parent `b7c2e1a9d3f4`) with full `upgrade()` AND `downgrade()`.
4. Register the 3 new models in `app/shared/models/__init__.py` (the canonical import surface) and add their relationships to `User`.
5. Tests: model instantiation/CRUD + constraint enforcement + a migration up/down round-trip.

**Out of scope for Wave 1 (explicit — DO NOT build):**
- NO adapter methods (`adapters/razorpay.py` stays the V1 one-function file) — Wave 2.
- NO endpoints / routers / Pydantic schemas — Wave 3.
- NO webhook event-router logic, NO state-machine handlers, NO `capture_razorpay_webhook` change — Wave 2.
- NO `plan_guard` / entitlement resolution change, NO `MeResponse.plan` widening — Wave 3.
- NO reconciliation Celery task, NO trial-expiry sweep — Wave 4.
- NO seed data (no Razorpay plan-id constants, no price constants) — those are config/Wave 2-3.
- Do NOT touch `iam/service.py`, `iam/router.py`, `iam/schemas.py`, `core/plan_guard.py`, `core/auth.py`.

The schema you build is **LTD-ready and trial-ready from the start** (per spec F2 + Pricing v2) even though the LTD/trial *logic* lands in later waves. That means the columns/constraints below already accommodate the LTD path (`razorpay_order_id`, perpetual `current_period_end=NULL`, `ltd` tier value) and the trial (`users.trial_ends_at`).

---

## 2. Conventions to follow (verified against the live tree)

Match the existing `app/shared/models/*.py` pattern exactly (reference: `pricing_calc.py`, `user.py`, `audit_event.py`):

- `from __future__ import annotations`; stdlib → SQLAlchemy → local import blocks.
- `Mapped[T]` / `mapped_column(...)` SQLAlchemy 2.0 typed style.
- PK: `id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))`.
- Timestamps: `from sqlalchemy.dialects.postgresql import TIMESTAMP` → `TIMESTAMP(timezone=True)`, server-default `text("NOW()")` where a default applies.
- JSONB: `from sqlalchemy.dialects.postgresql import JSONB`.
- FKs: `ForeignKey("users.id", ondelete="RESTRICT")` (billing survives user soft-delete — match the existing `ondelete='RESTRICT'` on `users` FKs from catalog/export).
- Indexes + table-level constraints via `__table_args__ = (Index(...), CheckConstraint(...), UniqueConstraint(...))`.
- `TYPE_CHECKING`-guarded forward references for relationships; string-based `relationship("User", back_populates=...)`.
- Each new model gets a module docstring naming the table + DDL source (`RAZORPAY_INTEGRATION_SPEC §7.x`).
- Register every new model in `app/shared/models/__init__.py` with a `# noqa: F401` re-export line, in dependency order (after `User`).

CHECK-constraint naming convention (from baseline): `ck_<table>_<column>` (e.g. `ck_templates_compliance_shape`, `ck_product_images_order_idx`). Index naming: `idx_<table>_<cols>` (e.g. `idx_pricing_calcs_product_id`) OR Alembic's `op.f('ix_<table>_<col>')` for single-column indexes created via `index=True`. Prefer explicit `Index(...)` in `__table_args__` for composite/partial indexes.

---

## 3. ORM file paths (DECISION — justified)

**Place the 3 new models in `app/shared/models/` as flat files, one per table**, matching every existing ORM model:

- `backend/app/shared/models/subscription.py` → class `Subscription`
- `backend/app/shared/models/payment.py` → class `Payment`
- `backend/app/shared/models/webhook_event.py` → class `WebhookEvent`

**Justification:** The codebase uses a FLAT `app/shared/models/` directory (verified: 14 model files, no per-domain sub-packages), and `app/shared/models/__init__.py` is the documented "canonical import surface" — modules import ORM classes from `app.shared.models`, never from another module's `repository.py`. Introducing a new `billing/` sub-package would break this single-surface convention and the import-linter rules (`BACKEND_ARCHITECTURE.md §16/§19`). The spec's agent-lineup row (§7 lineup) itself names `shared/models/subscription.py`, `shared/models/payment.py`, `shared/models/webhook_event.py` — this matches. Do NOT create a new package.

The `users.trial_ends_at` column is added to the existing `backend/app/shared/models/user.py`.

---

## 4. Table 1 — `subscriptions`

Source: RAZORPAY_INTEGRATION_SPEC §7.1 + §3.1 state table + Pricing v2 §5 tier set.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `user_id` | UUID | NOT NULL | — | FK `users(id)` ON DELETE RESTRICT |
| `razorpay_subscription_id` | VARCHAR(255) | NULL | — | UNIQUE; NULL for the LTD Orders path |
| `razorpay_order_id` | VARCHAR(255) | NULL | — | UNIQUE; set only for LTD |
| `tier` | VARCHAR(20) | NOT NULL | — | CHECK ∈ tier set (below) |
| `status` | VARCHAR(20) | NOT NULL | — | CHECK ∈ status set (below) |
| `current_period_end` | TIMESTAMPTZ | NULL | — | NULL = perpetual (LTD sentinel) |
| `cancel_scheduled_at` | TIMESTAMPTZ | NULL | — | set when cancel-at-cycle-end scheduled |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | also `onupdate=NOW()` at ORM level (`server_onupdate`/`onupdate=text("NOW()")`) |

**CHECK constraints:**
- `ck_subscriptions_tier`: `tier IN ('starter','pro','pro_annual','business','business_annual','ltd')`
  (NOTE: `free` is NOT a subscription tier — a free user has no `subscriptions` row. Do NOT include `free` here. This is the Pricing v2 set MINUS `free`.)
- `ck_subscriptions_status`: `status IN ('created','authenticated','active','past_due','halted','cancelled','completed','expired')` (the §3.1 derived-status set).

**UNIQUE constraints:**
- `razorpay_subscription_id` UNIQUE (column-level `unique=True`; NULLs allowed multiple times in Postgres — correct for LTD rows that have NULL here).
- `razorpay_order_id` UNIQUE (same NULL semantics).

**Indexes:**
- `idx_subscriptions_user_id_status` on `(user_id, status)` — the hot entitlement lookup.
- (the two UNIQUE constraints already create indexes on the razorpay ids — no separate index needed.)

**Partial unique index — "≤1 active sub per user" guard (spec §7.1):**
- `uq_subscriptions_one_active_per_user`: `UNIQUE (user_id) WHERE status = 'active'`.
  Implement via `Index("uq_subscriptions_one_active_per_user", "user_id", unique=True, postgresql_where=text("status = 'active'"))`.
  RATIONALE: prevents a user holding two simultaneous active subscriptions (e.g. a stray race between LTD + recurring). This is a DB-level invariant the later waves rely on. If the builder judges this too strict for the LTD-plus-recurring edge (a user who bought LTD then also subscribes), FLAG IT in the PR rather than silently dropping it — but default to including it; the spec's §7.1 inline comment explicitly calls for it.

**Relationship:** `subscription.user` ↔ add `subscriptions: Mapped[list[Subscription]]` to `User` (back_populates, no cascade — billing must survive; RESTRICT on FK already protects). `subscription.payments` ↔ `Payment.subscription` (one-to-many, see Table 2).

---

## 5. Table 2 — `payments`

Source: RAZORPAY_INTEGRATION_SPEC §7.2. **Unit decision: paise (integer), per founder ruling F9.** Name the column `amount_paise` (NOT the spec's ambiguous `amount_inr` — F9 locked paise; an explicit `_paise` suffix prevents the rupees/paise confusion the spec §7.2 itself flagged as a "decide unit" TODO). Add a column comment stating "amount in paise (Razorpay-native), e.g. 49900 = ₹499.00".

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `subscription_id` | UUID | NULL | — | FK `subscriptions(id)` ON DELETE RESTRICT; NULL for an LTD order-only payment with no sub row, or until linked |
| `user_id` | UUID | NOT NULL | — | FK `users(id)` ON DELETE RESTRICT |
| `razorpay_payment_id` | VARCHAR(255) | NULL | — | UNIQUE; NULL allowed (e.g. a failed-payment record before an id is assigned) |
| `amount_paise` | INTEGER | NOT NULL | — | paise (F9) |
| `currency` | VARCHAR(3) | NOT NULL | `'INR'` | server-default `'INR'` |
| `status` | VARCHAR(20) | NOT NULL | — | CHECK ∈ {captured, failed, refunded} |
| `event_type` | VARCHAR(40) | NULL | — | source webhook event, e.g. `subscription.charged`, `payment.captured`, `refund.processed` |
| `occurred_at` | TIMESTAMPTZ | NULL | — | event timestamp from the payload |
| `raw_jsonb` | JSONB | NULL | — | the charge/refund payload slice |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | row insert time (distinct from `occurred_at`) |

**CHECK:** `ck_payments_status`: `status IN ('captured','failed','refunded')`.
**UNIQUE:** `razorpay_payment_id` UNIQUE (NULLs allowed).
**Indexes:**
- `idx_payments_user_id` on `(user_id)`.
- `idx_payments_subscription_id` on `(subscription_id)`.
(The UNIQUE on `razorpay_payment_id` covers payment-id lookups.)

**Relationships:** `payment.user` ↔ `User.payments`; `payment.subscription` ↔ `Subscription.payments`.

---

## 6. Table 3 — `webhook_events`

Source: RAZORPAY_INTEGRATION_SPEC §7.3 (idempotency + audit + replay store). **This is the table that resolves the V1 capture-only conflict — DO NOT relax `audit_events.user_id` instead.**

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `event_id` | VARCHAR(255) | NOT NULL | — | **PK** — the Razorpay event id; this is the `ON CONFLICT (event_id) DO NOTHING` dedupe key |
| `event_type` | VARCHAR(60) | NOT NULL | — | e.g. `subscription.charged` |
| `payload_jsonb` | JSONB | NOT NULL | — | FULL raw payload (the column V1 lacked) — enables replay (§4.4) |
| `signature_valid` | BOOLEAN | NOT NULL | — | recorded for ops triage |
| `received_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | |
| `processed_at` | TIMESTAMPTZ | NULL | — | NULL until handler succeeds |
| `processing_error` | TEXT | NULL | — | last handler error for ops triage |

**PK is `event_id` (natural key)** — NOT a synthetic UUID. This is deliberate: the dedupe gate is `INSERT ... ON CONFLICT (event_id) DO NOTHING`, which needs `event_id` to be the conflict target (a PK or UNIQUE constraint). Use a string PK here (the one model in this wave that does NOT use a UUID PK). Note this exception clearly in the model docstring.

**Indexes:**
- `idx_webhook_events_type_received` on `(event_type, received_at)`.
- `idx_webhook_events_unprocessed` partial: `Index("idx_webhook_events_unprocessed", "processed_at", postgresql_where=text("processed_at IS NULL"))` — finds stuck/unprocessed events.

**No FK** — `webhook_events` has no `user_id` (a webhook transport record has no inherent user; the business effect lands in `audit_events` in later waves). No relationships.

---

## 7. `users` changes

Source: RAZORPAY_INTEGRATION_SPEC §7.4a + §13 F1 + Pricing v2 §5/§5.1.

1. **Add column** `trial_ends_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, comment="14-day Pro trial expiry (Pricing v2 §5.1); Pro entitlement while now() < trial_ends_at; user stays plan='free'. NULL = no trial.")`. This is the ONLY new `users` column. NO `razorpay_sub_id`, NO `plan_expires_at` (the spec pre-flight verified these do not exist and must NOT be added — the subscription is its own FK'd entity).

2. **Add CHECK constraint** on `users.plan` (none exists today):
   `ck_users_plan`: `plan IN ('free','starter','pro','pro_annual','business','business_annual','ltd')`.
   (This is the FULL Pricing v2 set INCLUDING `free` — `users.plan` carries `free`; only `subscriptions.tier` excludes `free`.)

3. **Update the column comment** on `users.plan` from `'free | pro'` to `'free | starter | pro | pro_annual | business | business_annual | ltd'`. (Comment change in both the ORM model and the migration via `op.alter_column(..., comment=..., existing_type=...)`.)

In `user.py`: widen the `plan` mapped_column `comment=`, add the `trial_ends_at` mapped_column, add the `subscriptions` and `payments` relationships, and add a `__table_args__ = (CheckConstraint("plan IN (...)", name="ck_users_plan"),)`. (User currently has no `__table_args__` — add one.)

---

## 8. Alembic migration plan

- **File:** `backend/alembic/versions/<rev>_add_billing_tables_and_trial.py` (let `alembic revision -m "..."` generate the slug; do NOT hand-pick the revision hash).
- **`down_revision = "b7c2e1a9d3f4"`** (the VERIFIED current head — see §0; re-confirm with `alembic heads` at build time).
- **Message:** `add billing tables subscriptions payments webhook_events + widen users.plan check + add users.trial_ends_at`.
- **Hand-write the migration** (do not rely solely on autogenerate — autogenerate misses CHECK constraints, partial indexes, and column comments; verify against autogenerate diff but author the ops explicitly, following the `b7c2e1a9d3f4` hand-written style).

**`upgrade()` order of operations:**
1. `op.create_table("subscriptions", ...)` with all columns + the two CHECKs + the two UNIQUE column constraints + PK.
2. Create `subscriptions` indexes: `idx_subscriptions_user_id_status` + the partial unique `uq_subscriptions_one_active_per_user`.
3. `op.create_table("payments", ...)` (after subscriptions — it FKs to it) with CHECK + UNIQUE.
4. Create `payments` indexes.
5. `op.create_table("webhook_events", ...)` (string PK on `event_id`) + its two indexes (incl. the partial).
6. `op.add_column("users", sa.Column("trial_ends_at", postgresql.TIMESTAMP(timezone=True), nullable=True, comment="..."))`.
7. `op.create_check_constraint("ck_users_plan", "users", "plan IN ('free','starter','pro','pro_annual','business','business_annual','ltd')")`.
8. `op.alter_column("users", "plan", existing_type=sa.String(20), comment="free | starter | pro | pro_annual | business | business_annual | ltd", existing_comment="free | pro")`.

**`downgrade()` — exact reverse order:**
1. `op.alter_column("users", "plan", ...)` revert comment to `'free | pro'`.
2. `op.drop_constraint("ck_users_plan", "users", type_="check")`.
3. `op.drop_column("users", "trial_ends_at")`.
4. `op.drop_table("webhook_events")` (drops its indexes with it).
5. `op.drop_table("payments")`.
6. `op.drop_table("subscriptions")` (drop AFTER payments — payments FKs to it).

**Test both directions locally** against a `*_test` DB: `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head` again (round-trip). Paste the command output in the PR "Test evidence" section. Confirm `alembic heads` shows a SINGLE head after upgrade (no divergence).

**Cross-lead note:** if `meesell-data-engineer` has any migration in flight this sprint, the parent revision must be coordinated (a memo per repo management master plan §7.5). The lead will check this before dispatch; the builder should `git fetch` + re-run `alembic heads` immediately before generating to catch a race.

---

## 9. Test requirements

Add tests following the existing `tests/test_database.py` conventions (the `db` rolled-back-AsyncSession fixture + `dev_engine`; `pytestmark = pytest.mark.integration`; conftest's `*_test`-DB guard). Place model/CRUD tests in `tests/test_database.py` (extend it) OR a focused new `tests/test_billing_models.py` — builder's choice, but they MUST run under the same conftest fixtures.

Required coverage:
1. **CRUD instantiation** — insert + read-back one row per new table (`Subscription`, `Payment`, `WebhookEvent`) with valid values; assert server-defaults populate (`id`, `created_at`/`received_at`, `currency='INR'`).
2. **FK enforcement** — inserting a `payments` row with a non-existent `user_id` raises `IntegrityError`; same for `subscriptions.user_id`; `payments.subscription_id` accepts NULL.
3. **CHECK enforcement** — `subscriptions.tier='free'` raises (free is not a sub tier); `subscriptions.status='bogus'` raises; `payments.status='bogus'` raises; `users.plan='bogus'` raises; `users.plan='starter'` succeeds.
4. **UNIQUE enforcement** — duplicate `razorpay_subscription_id` raises; two rows with NULL `razorpay_subscription_id` both succeed (NULL-multiplicity sanity for the LTD path); duplicate `webhook_events.event_id` raises (the dedupe-key sanity).
5. **Partial unique (one-active-per-user)** — two `status='active'` subs for the same user raises; one `active` + one `cancelled` for the same user succeeds.
6. **JSONB round-trip** — `webhook_events.payload_jsonb` and `payments.raw_jsonb` write+read a nested dict unchanged (match the existing §B JSONB round-trip pattern).
7. **`users.trial_ends_at`** — set a timestamp, read it back; NULL default verified.
8. **Migration up/down round-trip** — a test (or documented manual evidence in the PR) proving `upgrade → downgrade → upgrade` leaves a single head and the 3 tables + column present/absent correctly. If automated, follow any existing migration-test harness; if none exists, manual CLI evidence pasted in the PR is acceptable for this wave (note which you did).

---

## 10. Branch + PR

- **Branch to cut:** `feature/razorpay-integration/backend` (off `develop` per the spec §Branch setup; first backend slice of the feature).
- **PR target:** `feature/razorpay-integration/backend` → **`feature/razorpay-integration`** (the lead merge gate, squash-merge — NOT directly to `develop`; the founder owns the integration→develop gate per D1). If `feature/razorpay-integration` does not yet exist, the lead creates the integration branch off `develop` first; flag if absent.
- **PR template:** fill `.github/PULL_REQUEST_TEMPLATE/backend.md` COMPLETELY — no `<>` placeholders. Required: Alembic revision + down-revision documented; upgrade+downgrade tested (paste output); modules/files touched listed; CHECK/constraint changes in the commit body; no new cross-module call (this wave adds none — `iam`/`shared` only); Test evidence pasted; "Session" block = `mesell-razorpay-integration-backend-session-1`.
- **First commit footer** carries the session name.
- **On PR open:** YOU (the specialist) set the `feature_board_backend.md` row for `razorpay-integration` to `IN REVIEW` and clear `Current session` (per D2). The lead will then run the merge-gate review (HYBRID step 3).
- **OpenAPI:** no regeneration needed this wave (no endpoint shape change — Wave 1 is schema-only).

---

## 11. Acceptance criteria (the lead's merge-gate checklist for this PR)

- [ ] 3 new ORM models exist at the §3 paths, match the `Mapped[T]` convention, registered in `app/shared/models/__init__.py`.
- [ ] `users.trial_ends_at` added; `users.plan` CHECK added; `users.plan` comment widened; NO other `users` columns added.
- [ ] All columns/types/nullability/defaults match §4/§5/§6/§7 (paise unit on `payments.amount_paise`; string PK on `webhook_events.event_id`; perpetual-NULL `current_period_end`; UNIQUE razorpay ids).
- [ ] All CHECK constraints present with the exact value sets (`subscriptions.tier` EXCLUDES `free`; `users.plan` INCLUDES `free`).
- [ ] Partial unique "one active sub per user" present (or explicitly flagged with rationale if dropped).
- [ ] Migration parent = the verified current head (`b7c2e1a9d3f4` unless a newer head landed); both `upgrade()` and `downgrade()` implemented and tested; single head after upgrade.
- [ ] Tests cover §9 items 1–8; CI gates 1 (unit), 2 (smoke), 3 (lint) green; gate 4 (integration) result pasted.
- [ ] PR template fully filled; session block correct; board row `IN REVIEW`.
- [ ] Zero out-of-scope changes (no adapter, routes, schemas, plan_guard, service, reconciliation, seeds).
```
