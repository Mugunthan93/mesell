"""Integration tests for the category change monitor FAN-OUT worker (Wave 4 Unit F).

What this covers
----------------
* ``monitor.service.fanout_category_change`` — the async orchestrator behind
  the ``monitor.fanout_category_change`` Celery task. It re-diffs the latest
  vs prior ``category_snapshots`` rows, fans the change out to every
  subscriber (``category_subscription`` VIEW), idempotently FLAGS the affected
  products and inserts ONE notification row per user
  (``ON CONFLICT DO NOTHING``).

NON-LIVE CONTRACT (load-bearing)
--------------------------------
* ZERO live Meesho. The orchestrator NEVER scrapes — it reads the already-
  captured snapshot rows that the test seeds directly. ``scrape_category`` /
  ``.delay`` are never reached on this path.
* The gate-enqueue case (verdict → ``.delay`` called/not-called) lives in
  ``test_monitor_gate.py`` (mock-based) — see ``patched_gate.fanout_delay``
  assertions there (the 3 verdict cases). This file owns the DB-real
  orchestrator behaviour.
* Disposable ``meesell_test`` DB only (conftest refuses any non-``*_test`` DB).
  NEVER the live ``meesell`` DB (3772 categories).

Revert-check structure
----------------------
* Drop the ``ON CONFLICT DO NOTHING`` in ``repository.insert_notification`` →
  the idempotency case (``test_fanout_is_idempotent``) goes RED with a unique
  violation on the 2nd run.
* Flip the verdict guard to allow BLOCK → ``test_block_verdict_no_fanout``
  goes RED (it would create rows).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.modules.monitor import service as monitor_service
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.category_snapshot import CategorySnapshot
from app.shared.models.notification import Notification
from app.shared.models.product import Product as ProductORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ─────────────────────────────────────────────────────────────────────────────
# Diff dimension projections (well-formed 4-dimension shapes)
# ─────────────────────────────────────────────────────────────────────────────
# Prior snapshot: baseline.
_PRIOR_DIMS = {
    "compliance_fields": {"required": ["size"], "optional": []},
    "shipping_slab": {"shipping_charges": 30, "gst_percentage": 5},
    "banned_words": {"branded": []},
    "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0},
}
# New snapshot with a REVIEW_REQUIRED-grade drift: a required field added
# (compliance change) + ₹6 shipping rise (shipping change). Sub-threshold so
# it is REVIEW_REQUIRED, not BLOCK.
_NEW_DIMS = {
    "compliance_fields": {"required": ["size", "country_of_origin"], "optional": []},
    "shipping_slab": {"shipping_charges": 36, "gst_percentage": 5},
    "banned_words": {"branded": []},
    "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0},
}
_PRIOR_HASH = "a" * 64
_NEW_HASH = "b" * 64


# ─────────────────────────────────────────────────────────────────────────────
# Seed helpers (full FK chain: template→category→user→catalog→product)
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_template(db, *, schema_hash: str) -> TemplateORM:
    template = TemplateORM(
        schema_hash=schema_hash,
        schema_jsonb={
            "fields": [],
            "compulsory_count": 0,
            "optional_count": 0,
            "total_count": 0,
            "wizard_step_count": 0,
            "main_sheet_label": "Test",
        },
        compliance_shape="standard",
        parsed_from_xlsx_at=datetime.now(timezone.utc),
        parser_version="fo1.0",
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def _seed_category(db, *, schema_hash, leaf_id, leaf_name) -> CategoryORM:
    template = await _seed_template(db, schema_hash=schema_hash)
    category = CategoryORM(
        super_id="99",
        super_name="Fan-out Test Super",
        path=f"Fan-out Test Super > {leaf_name}",
        meesho_leaf_id=leaf_id,
        leaf_name=leaf_name,
        template_id=template.id,
        commission_pct=Decimal("10.00"),
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def _seed_user(db, *, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_catalog(db, *, user_id, category_id, name) -> CatalogORM:
    catalog = CatalogORM(
        user_id=user_id, name=name, status="draft", category_id=category_id
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(db, *, user_id, catalog_id, category_id, name) -> ProductORM:
    product = ProductORM(
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name=name,
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
        deleted_at=None,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _seed_snapshot(db, *, category_id, content_hash, dims, age_seconds) -> None:
    snap = CategorySnapshot(
        category_id=category_id,
        captured_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        content_hash=content_hash,
        dimensions_jsonb=dims,
        blob_uri=None,
    )
    db.add(snap)
    await db.flush()


async def _seed_two_snapshots(db, *, category_id, new_dims=None, new_hash=None) -> None:
    """Seed prior (older) + new (latest) snapshot rows for a category."""
    await _seed_snapshot(
        db,
        category_id=category_id,
        content_hash=_PRIOR_HASH,
        dims=_PRIOR_DIMS,
        age_seconds=600,
    )
    await _seed_snapshot(
        db,
        category_id=category_id,
        content_hash=new_hash or _NEW_HASH,
        dims=new_dims or _NEW_DIMS,
        age_seconds=10,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 1 — REVIEW_REQUIRED fans out: notifications + flags + copy
# ─────────────────────────────────────────────────────────────────────────────
class TestFanoutHappyPath:
    async def test_review_required_fans_out(self, db_session, use_live_valkey):
        """One category, two subscribers → both get a notification + flags;
        copy headline + a known fragment assembled correctly."""
        category = await _seed_category(
            db_session, schema_hash="fo-0001", leaf_id="FO-LEAF-1", leaf_name="Kurtis"
        )
        user_a = await _seed_user(db_session, phone="+915557010001")
        user_b = await _seed_user(db_session, phone="+915557010002")
        cat_a = await _seed_catalog(
            db_session, user_id=user_a.id, category_id=category.id, name="A Cat"
        )
        cat_b = await _seed_catalog(
            db_session, user_id=user_b.id, category_id=category.id, name="B Cat"
        )
        await _seed_product(
            db_session, user_id=user_a.id, catalog_id=cat_a.id,
            category_id=category.id, name="A P1",
        )
        await _seed_product(
            db_session, user_id=user_b.id, catalog_id=cat_b.id,
            category_id=category.id, name="B P1",
        )
        await _seed_two_snapshots(db_session, category_id=category.id)
        await db_session.commit()

        result = await monitor_service.fanout_category_change(
            category.id, _NEW_HASH, db_session
        )

        assert result["notified_users"] == 2
        assert result["notifications_created"] == 2
        assert result["skipped_existing"] == 0
        assert result["products_flagged"] == 2

        # Notifications exist for both users.
        notifs = (
            await db_session.execute(
                select(Notification).where(Notification.category_id == category.id)
            )
        ).scalars().all()
        assert len(notifs) == 2
        assert {n.user_id for n in notifs} == {user_a.id, user_b.id}

        # Copy: headline + the compliance + shipping fragments.
        summary = notifs[0].payload_jsonb["summary"]
        assert summary.startswith("Your category 'Kurtis' changed:")
        assert "added required field(s): country_of_origin" in summary
        assert "shipping cost rose ₹6" in summary
        assert "review them before your next upload." in summary
        assert "1 of your catalogs are affected" in summary

        # Payload structure: only the two changed dimensions.
        assert set(notifs[0].payload_jsonb["diff_dimensions"]) == {
            "compliance",
            "shipping",
        }
        assert len(notifs[0].payload_jsonb["affected_catalog_ids"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Case 2 — Idempotency: run twice → no double notify, flags stay true
# ─────────────────────────────────────────────────────────────────────────────
class TestFanoutIdempotency:
    async def test_fanout_is_idempotent(self, db_session, use_live_valkey):
        category = await _seed_category(
            db_session, schema_hash="fo-0002", leaf_id="FO-LEAF-2", leaf_name="Sarees"
        )
        user = await _seed_user(db_session, phone="+915557020001")
        cat = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id, name="Cat"
        )
        await _seed_product(
            db_session, user_id=user.id, catalog_id=cat.id,
            category_id=category.id, name="P1",
        )
        await _seed_two_snapshots(db_session, category_id=category.id)
        await db_session.commit()

        first = await monitor_service.fanout_category_change(
            category.id, _NEW_HASH, db_session
        )
        assert first["notifications_created"] == 1
        assert first["skipped_existing"] == 0

        # 2nd run on the same (category, content_hash) → no double notify.
        second = await monitor_service.fanout_category_change(
            category.id, _NEW_HASH, db_session
        )
        assert second["notified_users"] == 1
        assert second["notifications_created"] == 0
        assert second["skipped_existing"] == 1  # ON CONFLICT DO NOTHING

        # Exactly ONE notification row (not 2).
        count = (
            await db_session.execute(
                select(Notification).where(Notification.user_id == user.id)
            )
        ).scalars().all()
        assert len(count) == 1

        # Flags stay true (set-only — no error on re-flag).
        prod = (
            await db_session.execute(
                select(ProductORM).where(ProductORM.user_id == user.id)
            )
        ).scalar_one()
        assert prod.needs_recheck is True
        assert prod.needs_reprice is True
        assert prod.needs_export is True


# ─────────────────────────────────────────────────────────────────────────────
# Case 3 — BLOCK verdict → NO fan-out;  also PASS → NO fan-out
# ─────────────────────────────────────────────────────────────────────────────
class TestFanoutVerdictGuards:
    async def test_block_verdict_no_fanout(self, db_session, use_live_valkey):
        """A partial/truncated new projection re-diffs to BLOCK → STOP."""
        category = await _seed_category(
            db_session, schema_hash="fo-0003", leaf_id="FO-LEAF-3", leaf_name="Tops"
        )
        user = await _seed_user(db_session, phone="+915557030001")
        cat = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id, name="Cat"
        )
        await _seed_product(
            db_session, user_id=user.id, catalog_id=cat.id,
            category_id=category.id, name="P1",
        )
        # New dims are PARTIAL (missing dimension keys) → diff engine BLOCKs.
        partial_dims = {"compliance_fields": {"required": ["size"], "optional": []}}
        await _seed_two_snapshots(
            db_session, category_id=category.id,
            new_dims=partial_dims, new_hash=_NEW_HASH,
        )
        await db_session.commit()

        result = await monitor_service.fanout_category_change(
            category.id, _NEW_HASH, db_session
        )
        assert result == {
            "notified_users": 0,
            "notifications_created": 0,
            "products_flagged": 0,
            "skipped_existing": 0,
        }
        notifs = (
            await db_session.execute(
                select(Notification).where(Notification.category_id == category.id)
            )
        ).scalars().all()
        assert notifs == []
        prod = (
            await db_session.execute(
                select(ProductORM).where(ProductORM.user_id == user.id)
            )
        ).scalar_one()
        assert prod.needs_recheck is False
        assert prod.needs_export is False

    async def test_pass_verdict_no_fanout(self, db_session, use_live_valkey):
        """Latest hash == prior hash → diff short-circuits PASS → STOP."""
        category = await _seed_category(
            db_session, schema_hash="fo-0004", leaf_id="FO-LEAF-4", leaf_name="Jeans"
        )
        user = await _seed_user(db_session, phone="+915557040001")
        cat = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id, name="Cat"
        )
        await _seed_product(
            db_session, user_id=user.id, catalog_id=cat.id,
            category_id=category.id, name="P1",
        )
        # Both snapshots share the SAME hash + dims → PASS (no drift).
        await _seed_snapshot(
            db_session, category_id=category.id,
            content_hash=_NEW_HASH, dims=_PRIOR_DIMS, age_seconds=600,
        )
        await _seed_snapshot(
            db_session, category_id=category.id,
            content_hash=_NEW_HASH, dims=_PRIOR_DIMS, age_seconds=10,
        )
        await db_session.commit()

        result = await monitor_service.fanout_category_change(
            category.id, _NEW_HASH, db_session
        )
        assert result["notifications_created"] == 0
        notifs = (
            await db_session.execute(
                select(Notification).where(Notification.category_id == category.id)
            )
        ).scalars().all()
        assert notifs == []


# ─────────────────────────────────────────────────────────────────────────────
# Case 4 — Superseded guard: arg content_hash != latest snapshot hash → STOP
# ─────────────────────────────────────────────────────────────────────────────
class TestFanoutSupersededGuard:
    async def test_superseded_hash_stops(self, db_session, use_live_valkey):
        category = await _seed_category(
            db_session, schema_hash="fo-0005", leaf_id="FO-LEAF-5", leaf_name="Shirts"
        )
        user = await _seed_user(db_session, phone="+915557050001")
        cat = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id, name="Cat"
        )
        await _seed_product(
            db_session, user_id=user.id, catalog_id=cat.id,
            category_id=category.id, name="P1",
        )
        await _seed_two_snapshots(db_session, category_id=category.id)
        await db_session.commit()

        # The fan-out is invoked with a STALE hash (a fresher scrape replaced it).
        result = await monitor_service.fanout_category_change(
            category.id, "deadbeef" * 8, db_session
        )
        assert result == {
            "notified_users": 0,
            "notifications_created": 0,
            "products_flagged": 0,
            "skipped_existing": 0,
        }
        notifs = (
            await db_session.execute(
                select(Notification).where(Notification.category_id == category.id)
            )
        ).scalars().all()
        assert notifs == []


# ─────────────────────────────────────────────────────────────────────────────
# Case 6 — Flag mapping: compliance/shipping/banned/cost → correct flags
# ─────────────────────────────────────────────────────────────────────────────
class TestFanoutFlagMapping:
    async def _run_with_new_dims(self, db_session, *, schema_hash, leaf_id, new_dims):
        category = await _seed_category(
            db_session, schema_hash=schema_hash, leaf_id=leaf_id, leaf_name="Cat"
        )
        user = await _seed_user(db_session, phone=f"+91555706{leaf_id[-4:].zfill(4)}")
        cat = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id, name="Cat"
        )
        await _seed_product(
            db_session, user_id=user.id, catalog_id=cat.id,
            category_id=category.id, name="P1",
        )
        await _seed_two_snapshots(
            db_session, category_id=category.id, new_dims=new_dims, new_hash=_NEW_HASH
        )
        await db_session.commit()
        await monitor_service.fanout_category_change(category.id, _NEW_HASH, db_session)
        prod = (
            await db_session.execute(
                select(ProductORM).where(ProductORM.user_id == user.id)
            )
        ).scalar_one()
        await db_session.refresh(prod)
        return prod

    async def test_compliance_only_recheck_and_export(self, db_session, use_live_valkey):
        new_dims = {
            "compliance_fields": {"required": ["size", "hsn"], "optional": []},
            "shipping_slab": {"shipping_charges": 30, "gst_percentage": 5},
            "banned_words": {"branded": []},
            "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0},
        }
        prod = await self._run_with_new_dims(
            db_session, schema_hash="fo-0061", leaf_id="FO-LEAF-61", new_dims=new_dims
        )
        assert prod.needs_recheck is True
        assert prod.needs_reprice is False  # compliance does NOT move cost
        assert prod.needs_export is True

    async def test_shipping_only_reprice_and_export(self, db_session, use_live_valkey):
        new_dims = {
            "compliance_fields": {"required": ["size"], "optional": []},
            "shipping_slab": {"shipping_charges": 50, "gst_percentage": 5},  # +₹20
            "banned_words": {"branded": []},
            "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0},
        }
        prod = await self._run_with_new_dims(
            db_session, schema_hash="fo-0062", leaf_id="FO-LEAF-62", new_dims=new_dims
        )
        assert prod.needs_recheck is False
        assert prod.needs_reprice is True
        assert prod.needs_export is True

    async def test_cost_only_reprice_and_export(self, db_session, use_live_valkey):
        new_dims = {
            "compliance_fields": {"required": ["size"], "optional": []},
            "shipping_slab": {"shipping_charges": 30, "gst_percentage": 5},
            "banned_words": {"branded": []},
            "cost_fields": {"transfer_price": 120.0, "platform_fee": 5.0},  # +₹20
        }
        prod = await self._run_with_new_dims(
            db_session, schema_hash="fo-0063", leaf_id="FO-LEAF-63", new_dims=new_dims
        )
        assert prod.needs_recheck is False
        assert prod.needs_reprice is True
        assert prod.needs_export is True

    async def test_banned_only_recheck_and_export_not_reprice(
        self, db_session, use_live_valkey
    ):
        new_dims = {
            "compliance_fields": {"required": ["size"], "optional": []},
            "shipping_slab": {"shipping_charges": 30, "gst_percentage": 5},
            "banned_words": {"branded": ["nike"]},  # new banned word
            "cost_fields": {"transfer_price": 100.0, "platform_fee": 5.0},
        }
        prod = await self._run_with_new_dims(
            db_session, schema_hash="fo-0064", leaf_id="FO-LEAF-64", new_dims=new_dims
        )
        # Director ruling: banned → recheck + export, NOT reprice.
        assert prod.needs_recheck is True
        assert prod.needs_reprice is False
        assert prod.needs_export is True


# ─────────────────────────────────────────────────────────────────────────────
# Case 7 — Tenancy: only users IN the category are flagged/notified
# ─────────────────────────────────────────────────────────────────────────────
class TestFanoutTenancy:
    async def test_uninvolved_user_untouched(self, db_session, use_live_valkey):
        """User B has products in a DIFFERENT category → never flagged/notified
        when category X fans out."""
        cat_x = await _seed_category(
            db_session, schema_hash="fo-0071", leaf_id="FO-LEAF-71", leaf_name="X"
        )
        cat_y = await _seed_category(
            db_session, schema_hash="fo-0072", leaf_id="FO-LEAF-72", leaf_name="Y"
        )
        user_a = await _seed_user(db_session, phone="+915557070001")
        user_b = await _seed_user(db_session, phone="+915557070002")

        cat_a = await _seed_catalog(
            db_session, user_id=user_a.id, category_id=cat_x.id, name="A in X"
        )
        prod_a = await _seed_product(
            db_session, user_id=user_a.id, catalog_id=cat_a.id,
            category_id=cat_x.id, name="A P1",
        )
        # User B is ONLY in category Y.
        cat_b = await _seed_catalog(
            db_session, user_id=user_b.id, category_id=cat_y.id, name="B in Y"
        )
        prod_b = await _seed_product(
            db_session, user_id=user_b.id, catalog_id=cat_b.id,
            category_id=cat_y.id, name="B P1",
        )
        await _seed_two_snapshots(db_session, category_id=cat_x.id)
        await db_session.commit()

        result = await monitor_service.fanout_category_change(
            cat_x.id, _NEW_HASH, db_session
        )
        assert result["notified_users"] == 1  # only user A

        # User A's product in X is flagged.
        await db_session.refresh(prod_a)
        assert prod_a.needs_export is True
        # User B's product in Y is UNTOUCHED.
        await db_session.refresh(prod_b)
        assert prod_b.needs_recheck is False
        assert prod_b.needs_reprice is False
        assert prod_b.needs_export is False
        # No notification for user B.
        b_notifs = (
            await db_session.execute(
                select(Notification).where(Notification.user_id == user_b.id)
            )
        ).scalars().all()
        assert b_notifs == []


# ─────────────────────────────────────────────────────────────────────────────
# Subscription-VIEW sanity — confirms the audience source the orchestrator reads
# ─────────────────────────────────────────────────────────────────────────────
async def test_subscription_view_distinct_audience(db_session, use_live_valkey):
    """A catalog-level + product-level subscription dedup to ONE user row."""
    category = await _seed_category(
        db_session, schema_hash="fo-0081", leaf_id="FO-LEAF-81", leaf_name="Z"
    )
    user = await _seed_user(db_session, phone="+915557080001")
    cat = await _seed_catalog(
        db_session, user_id=user.id, category_id=category.id, name="Cat"
    )
    await _seed_product(
        db_session, user_id=user.id, catalog_id=cat.id,
        category_id=category.id, name="P1",
    )
    await db_session.commit()

    rows = (
        await db_session.execute(
            text(
                "SELECT DISTINCT user_id FROM category_subscription "
                "WHERE category_id = :cid"
            ),
            {"cid": str(category.id)},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0][0] == user.id
