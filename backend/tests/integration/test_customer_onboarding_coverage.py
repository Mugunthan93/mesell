"""OB Wave A — Customer onboarding coverage gaps (§1.B partial/gap rows).

After reviewing test_customer_routes.py, the following OB-BE cases already
exist there:
  OB-BE-27  get-profile 404 first seller         → test_get_profile_when_no_row_returns_404
  OB-BE-30  active-categories unknown super 422  → test_unknown_super_id_returns_422
  OB-BE-32  compliance not-declared 404          → test_compliance_for_super_id_not_in_active_returns_404
  OB-BE-33  compliance missing-fields 422        → test_grocery_compliance_without_fssai_returns_422
  OB-BE-34  required-fields drives wizard        → test_required_fields_for_new_seller_returns_200_all_incomplete
                                                   + test_required_fields_after_full_patch_shows_blocking_fields_completed

This file adds the ONE true gap not yet on disk:

  OB-BE-31  active-categories replace semantics — PATCH a new set replaces the
            old set entirely; the old super_id is gone.

DPDP consent (OB-BE-38) is not modelled in the V1 customer schema —
no ``consent`` column or ``consent_at`` column exists in ``seller_profiles``.
This is filed as a SPEC gap in deferred_coverage.md; no test is written.

All tests use the ``customer_client`` fixture from ``test_customer_routes.py``
via pytest_plugins discovery.  The fixture file is loaded automatically from
the same package directory.
"""

from __future__ import annotations

import pytest
import app.modules.customer.service as _customer_service

# Import the ``customer_client`` fixture from the existing test module.
# The fixture is defined in test_customer_routes.py (not a conftest) so we
# pull it in via pytest_plugins.  pytest discovers ``test_customer_routes``
# as a top-level module under ``testpaths = tests``, which makes the names
# importable as ``test_customer_routes``.
pytest_plugins = ["test_customer_routes"]

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# ── Profile payload re-used across tests ──────────────────────────────────────
_VALID_PROFILE_PAYLOAD = {
    "manufacturer_name": "Onboard Wave Pvt Ltd",
    "manufacturer_address": "99 Wave Rd, Chennai",
    "manufacturer_pincode": "600001",
    "packer_name": "Onboard Wave Pvt Ltd",
    "packer_address": "99 Wave Rd, Chennai",
    "packer_pincode": "600001",
    "country_of_origin": "India",
}


async def _mock_super_ids(db):  # noqa: ARG001
    """Return a fixed super_id set so tests do not need a seeded categories table."""
    return {"26", "19", "13", "16", "80", "55"}


# ─────────────────────────────────────────────────────────────────────────────
# OB-BE-31  active-categories replace semantics
# ─────────────────────────────────────────────────────────────────────────────
async def test_active_categories_replace_semantics(customer_client, monkeypatch):
    """OB-BE-31: PATCH /seller-profile/active-categories replaces the entire set.

    Arrange: profile + active=['26', '19']; then PATCH again with ['13'] only.
    Act: second PATCH with ['13'].
    Assert: active_super_categories == ['13'] — '26' and '19' are GONE.

    This guards the §8.B.3 invariant: the endpoint REPLACES, not appends.
    """
    monkeypatch.setattr(_customer_service, "_get_super_id_set", _mock_super_ids)

    # Step 1: seed profile
    resp = await customer_client.patch(
        "/api/v1/seller-profile", json=_VALID_PROFILE_PAYLOAD
    )
    assert resp.status_code == 200, resp.text

    # Step 2: set initial active categories ['26', '19']
    resp = await customer_client.patch(
        "/api/v1/seller-profile/active-categories",
        json={"active_super_categories": ["26", "19"]},
    )
    assert resp.status_code == 200, (
        f"Initial active-categories PATCH failed: {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert set(body["active_super_categories"]) == {"26", "19"}, (
        f"Expected {{'26','19'}}, got {body['active_super_categories']!r}"
    )

    # Step 3: REPLACE with ['13'] only
    resp2 = await customer_client.patch(
        "/api/v1/seller-profile/active-categories",
        json={"active_super_categories": ["13"]},
    )
    assert resp2.status_code == 200, (
        f"Replace PATCH failed: {resp2.status_code}: {resp2.text}"
    )
    body2 = resp2.json()

    # Assert: the result is EXACTLY ['13'] — '26' and '19' must be gone
    assert body2["active_super_categories"] == ["13"], (
        f"Replace semantics failed: expected ['13'] only; "
        f"got {body2['active_super_categories']!r}. "
        f"'26' or '19' still present — the endpoint is additive, not a full-replace."
    )
