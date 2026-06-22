"""Identity-faithful REGRESSION guard — category-monitor onboarding edge.

Why this file exists (PR #472 merge-gate REJECT)
------------------------------------------------
Wave-3 wired the category change monitor into the three ``customer`` onboarding
recompute sites (``upsert_profile``, ``set_active_categories``,
``set_compliance_extension``).  The original implementation passed the LIVE
``existing`` ORM instance — read via ``find_by_user_id`` BEFORE the repository
write — into the false→true edge test, which then read
``existing.onboarding_complete`` AFTER the write.

That is broken under SQLAlchemy's identity map: ``find_by_user_id`` and the
repository write both ``scalar_one_or_none()`` on the SAME primary key in the
SAME session, so the identity map returns the SAME Python object.  The write
mutates ``existing.onboarding_complete`` to the NEW value (True) BEFORE the edge
test reads it, so ``crossed_edge = onboarding_complete and not
existing.onboarding_complete`` is ALWAYS False on the realistic
update→complete path — the monitor is NEVER enqueued in production.

The 8 fast unit tests in ``tests/test_monitor_triggers.py`` MASKED this: they
mocked ``find_by_user_id`` to return a DIFFERENT object than the repository
write returned, so the live-ORM read still saw the pre-write flag.  These
tests use a REAL async session + the REAL repository, so ``find_by_user_id``
and the write share ONE identity-mapped object — exactly the prod path.

The fix snapshots the prior flag as a plain ``bool`` at each call site BEFORE
the repository write and passes that bool (not the live ORM) into the edge
helper.  Against the OLD (live-ORM) code these tests FAIL (zero enqueues);
against the fixed (prior_complete bool) code they PASS.

NON-LIVE CONTRACT
-----------------
* The Celery task ``monitor.scrape_category`` / its ``.delay`` is MOCKED in
  every test — no live broker, no live Meesho.
* ``catalog_service.get_distinct_product_category_ids`` is mocked to a fixed
  leaf set so the test needs no seeded ``products`` rows.  Everything else —
  the seller-profile read (``find_by_user_id``) AND the repository write — runs
  against a REAL Postgres session via the real repository.  THAT is the
  identity-map path under test.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.modules.catalog.service as catalog_service
import app.modules.customer.service as customer_service
import app.modules.monitor.tasks as monitor_tasks
from app.modules.customer import repository as customer_repo
from app.modules.customer.schemas import PatchProfileRequest

pytestmark = pytest.mark.integration


# ── Harness (mirrors test_customer_cross_module_eligibility.py) ───────────────
async def _make_session_factory():
    """Per-test NullPool engine in the current event loop."""
    engine = create_async_engine(
        os.environ["DATABASE_URL"], poolclass=NullPool, echo=False
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _create_user_via_otp_verify(iam_client, phone: str, otp: str) -> str:
    """Drive a real OTP verify so the user_id is created via §7 iam."""
    from app.shared import valkey as _vk_mod

    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", payload, ex=300)

    resp = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _resolve_user_id(iam_client, access_token: str) -> UUID:
    resp = await iam_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200, resp.text
    return UUID(resp.json()["user_id"])


_BASE_PROFILE = dict(
    manufacturer_name="Edge Test Pvt",
    manufacturer_address="1 Edge Rd",
    manufacturer_pincode="560001",
    packer_name="Edge Test Pvt",
    packer_address="1 Edge Rd",
    packer_pincode="560001",
    country_of_origin="India",
)


def _patch_monitor_seam(monkeypatch):
    """Mock ONLY the leaf-resolver + Celery ``.delay``; leave the profile
    read + write REAL so the identity-map path is exercised.

    Returns ``(leaf_ids, delay_mock)``.
    """
    from unittest.mock import AsyncMock, MagicMock

    leaf_a, leaf_b = uuid4(), uuid4()
    monkeypatch.setattr(
        catalog_service,
        "get_distinct_product_category_ids",
        AsyncMock(return_value=[leaf_a, leaf_b]),
    )
    delay = MagicMock()
    monkeypatch.setattr(monitor_tasks.scrape_category_task, "delay", delay)
    return [leaf_a, leaf_b], delay


# ─────────────────────────────────────────────────────────────────────────────
# Site 1 — upsert_profile (base-field PATCH crosses the edge)
# ─────────────────────────────────────────────────────────────────────────────
async def test_upsert_profile_edge_enqueues_per_leaf_real_session(
    iam_client, use_live_valkey, monkeypatch
):
    """Seed onboarding_complete=False, then a base-PATCH flips it True via the
    REAL repository: the monitor must enqueue once per distinct product leaf.

    Against the live-ORM (pre-fix) code this asserts ZERO enqueues because the
    aliased ``existing`` already reads True after the write → RED.
    """
    leaf_ids, delay = _patch_monitor_seam(monkeypatch)
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000870", "676767"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        # Phase 1 — seed the row directly via the REPOSITORY (no service hook),
        # FORCING onboarding_complete=False so the next service PATCH genuinely
        # crosses the false→true edge.  Seeding via the service here would itself
        # complete onboarding (all base fields present) and fire the monitor,
        # polluting the count.
        async with Session() as session:
            await customer_repo.upsert(
                session, user_id, dict(_BASE_PROFILE), onboarding_complete=False
            )
            await session.commit()

        # Phase 2 — a fresh session.  ``find_by_user_id`` and the repo write
        # SHARE this session's identity map → the prod aliasing path.  Force the
        # recompute True so the flag flips false→true on this call.
        monkeypatch.setattr(
            customer_service, "_recompute_onboarding_complete", lambda *a, **k: True
        )
        async with Session() as session:
            await customer_service.upsert_profile(
                user_id,
                PatchProfileRequest(manufacturer_name="Edge Test Pvt Renamed"),
                session,
            )
            await session.commit()
    finally:
        await engine.dispose()

    assert delay.call_count == 2, (
        f"Expected one enqueue per distinct leaf (2); got {delay.call_count}. "
        "Zero means the identity-map aliasing suppressed the edge (pre-fix bug)."
    )
    enqueued = {c.args[0] for c in delay.call_args_list}
    assert enqueued == {str(leaf_ids[0]), str(leaf_ids[1])}


# ─────────────────────────────────────────────────────────────────────────────
# Site 2 — set_active_categories (declaring categories crosses the edge)
# ─────────────────────────────────────────────────────────────────────────────
async def test_set_active_categories_edge_enqueues_per_leaf_real_session(
    iam_client, use_live_valkey, monkeypatch
):
    """Seed onboarding_complete=False, then set_active_categories flips it True
    via the REAL repository → enqueue once per distinct leaf.
    """
    leaf_ids, delay = _patch_monitor_seam(monkeypatch)
    monkeypatch.setattr(
        customer_service, "_get_super_id_set", lambda db: _async_set({"13"})
    )
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000871", "787878"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        # Seed directly via the repository (onboarding False) — no service hook.
        async with Session() as session:
            await customer_repo.upsert(
                session, user_id, dict(_BASE_PROFILE), onboarding_complete=False
            )
            await session.commit()

        monkeypatch.setattr(
            customer_service, "_recompute_onboarding_complete", lambda *a, **k: True
        )
        async with Session() as session:
            await customer_service.set_active_categories(
                user_id, ["13"], session
            )
            await session.commit()
    finally:
        await engine.dispose()

    assert delay.call_count == 2, (
        f"Expected 2 enqueues (one per leaf); got {delay.call_count}. "
        "Zero means the identity-map aliasing suppressed the edge (pre-fix bug)."
    )
    enqueued = {c.args[0] for c in delay.call_args_list}
    assert enqueued == {str(leaf_ids[0]), str(leaf_ids[1])}


# ─────────────────────────────────────────────────────────────────────────────
# Site 3 — set_compliance_extension (final compliance step crosses the edge)
# ─────────────────────────────────────────────────────────────────────────────
async def test_set_compliance_extension_edge_enqueues_per_leaf_real_session(
    iam_client, use_live_valkey, monkeypatch
):
    """Grocery declared without FSSAI (onboarding False), then the FSSAI
    compliance PATCH flips it True via the REAL repository → enqueue per leaf.

    This drives the genuine production edge: a compulsory super (Grocery, 26)
    blocks onboarding until ``fssai_license_number`` is supplied.
    """
    leaf_ids, delay = _patch_monitor_seam(monkeypatch)
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000872", "898989"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        # Phase 1 — base profile + declare Grocery (26) WITHOUT FSSAI, seeded
        # directly via the repository (no service hook).  Grocery is a compulsory
        # super, so onboarding genuinely stays False until FSSAI is supplied.
        async with Session() as session:
            await customer_repo.upsert(
                session, user_id, dict(_BASE_PROFILE), onboarding_complete=False
            )
            await customer_repo.update_active_categories(
                session, user_id, ["26"], onboarding_complete=False
            )
            await session.commit()

        # Sanity — the row is genuinely incomplete before the compliance step.
        async with Session() as session:
            row = await customer_repo.find_by_user_id(session, user_id)
            assert row is not None and row.onboarding_complete is False

        # Phase 2 — supply FSSAI.  The REAL recompute flips the flag false→true
        # inside the same session that ``find_by_user_id`` read from.
        async with Session() as session:
            await customer_service.set_compliance_extension(
                user_id,
                "26",
                {"fssai_license_number": "10012345678901"},
                session,
            )
            await session.commit()
    finally:
        await engine.dispose()

    assert delay.call_count == 2, (
        f"Expected 2 enqueues (one per leaf); got {delay.call_count}. "
        "Zero means the identity-map aliasing suppressed the edge (pre-fix bug)."
    )
    enqueued = {c.args[0] for c in delay.call_args_list}
    assert enqueued == {str(leaf_ids[0]), str(leaf_ids[1])}


# ─────────────────────────────────────────────────────────────────────────────
# Host-survival — the enqueue raising must NOT break onboarding (real session)
# ─────────────────────────────────────────────────────────────────────────────
async def test_compliance_edge_host_survives_enqueue_raise_real_session(
    iam_client, use_live_valkey, monkeypatch
):
    """A broker outage (``.delay`` raises) must NOT break the compliance step;
    the profile still flips to onboarding_complete=True and is committed.
    """
    _leaf_ids, delay = _patch_monitor_seam(monkeypatch)
    delay.side_effect = RuntimeError("broker down")
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000873", "909090"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        async with Session() as session:
            await customer_repo.upsert(
                session, user_id, dict(_BASE_PROFILE), onboarding_complete=False
            )
            await customer_repo.update_active_categories(
                session, user_id, ["26"], onboarding_complete=False
            )
            await session.commit()

        async with Session() as session:
            result = await customer_service.set_compliance_extension(
                user_id,
                "26",
                {"fssai_license_number": "10012345678901"},
                session,
            )
            await session.commit()

        # Host flow survived the broker outage AND committed the completion.
        assert result is not None
        delay.assert_called()  # the enqueue WAS attempted (and swallowed)
        async with Session() as session:
            row = await customer_repo.find_by_user_id(session, user_id)
            assert row is not None and row.onboarding_complete is True
    finally:
        await engine.dispose()


async def _async_set(value):
    """Tiny awaitable returning ``value`` — for patching the async
    ``_get_super_id_set`` helper without unittest.mock."""
    return set(value)
