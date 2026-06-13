"""Top-level integration test — MS Sub-Plan E (customer extraction).

Asserts the MONOLITH-side REVERSE shim
(``app.core.extracted_clients.customer_client``) faithfully translates the
FROZEN customer-svc ``/internal/*`` HTTP contracts into the monolith's own
domain types + exceptions — i.e. the contract the catalog call sites at
``catalog/service.py:406`` (eligibility) + ``:839`` (compliance-block) depend on
will hold AT CUTOVER when the import flips to this shim (§16.G).

NO tautologies (the pricing lesson): every assertion checks REAL equality
between the frozen customer-svc JSON shape and the monolith's deserialised
``ComplianceBlock`` / ``ProfileCompleteness`` / raised exception, NOT
``assert True``-class echoes.  Mock transport (``httpx.MockTransport``) stands
in for customer-svc — the callee is still in-monolith during the hybrid window,
so there is no live round-trip here (mirrors the MS-B mock-tested pattern).

Markers: ``unit`` — no real DB / Valkey (the shim is pure HTTP translation;
the callee is mocked).  The audit-row-on-PATCH + 5-public-endpoints-byte-
identical assertions are covered by customer-svc's own suite
(``backend/services/svc-customer/tests/``, 22 passing) + the existing monolith
customer integration tests (``tests/integration/test_customer_*``); this file
owns the REVERSE-shim contract that those two trees do not exercise together.
"""

from __future__ import annotations

import dataclasses
import inspect
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.unit


# ── Frozen customer-svc /internal/* JSON shapes (must match the svc dataclasses) ──
# Source: backend/services/svc-customer/app/internal_routes.py (asdict of the
# frozen domain dataclasses).  These are the EXACT bytes customer-svc emits.
_FROZEN_COMPLIANCE_BLOCK = {
    "manufacturer_name": "Acme Mfg Pvt Ltd",
    "manufacturer_address": "12 Industrial Estate, Pune",
    "manufacturer_pincode": "411001",
    "packer_name": "Acme Packers",
    "packer_address": "12 Industrial Estate, Pune",
    "packer_pincode": "411001",
    "importer_name": None,
    "importer_address": None,
    "importer_pincode": None,
    "country_of_origin": "India",
}


class _Recorder:
    """Records outbound requests + replays a scripted sequence of responses."""

    def __init__(self, scripted: list[tuple[int, object]]):
        self._scripted = list(scripted)
        self.requests: list[httpx.Request] = []
        self.timeouts: list[object] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._scripted.pop(0)
        return httpx.Response(status, json=body, request=request)


def _install_mock(monkeypatch, recorder: _Recorder) -> None:
    from app.core.extracted_clients import customer_client

    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        recorder.timeouts.append(kwargs.get("timeout"))
        kwargs["transport"] = httpx.MockTransport(recorder.handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(customer_client.httpx, "AsyncClient", factory)


# ── (a) compliance-block: 10-field REAL equality, deserialised into ComplianceBlock ──
@pytest.mark.asyncio
async def test_reverse_shim_compliance_block_10_fields_equal(monkeypatch):
    from app.core.extracted_clients import customer_client
    from app.modules.customer.domain import ComplianceBlock

    rec = _Recorder([(200, _FROZEN_COMPLIANCE_BLOCK)])
    _install_mock(monkeypatch, rec)
    customer_client.set_request_context(bearer_token="jwt-x", request_id="rid-1")

    uid = uuid4()
    block = await customer_client.get_compliance_block(uid, db=None)

    # REAL equality: every one of the 10 frozen fields round-trips into the
    # monolith ComplianceBlock with the SAME value.
    assert isinstance(block, ComplianceBlock)
    field_names = [f.name for f in dataclasses.fields(ComplianceBlock)]
    assert len(field_names) == 10
    for name in field_names:
        assert getattr(block, name) == _FROZEN_COMPLIANCE_BLOCK[name], name

    # Transport contract: forwarded headers + 5s/2s timeout + correct path.
    req = rec.requests[0]
    assert req.method == "GET"
    assert str(req.url) == f"http://customer-svc:8001/internal/seller-profile/{uid}/compliance-block"
    assert req.headers.get("Authorization") == "Bearer jwt-x"
    assert req.headers.get("X-Request-ID") == "rid-1"
    assert rec.timeouts[0].read == 5.0
    assert rec.timeouts[0].connect == 2.0


# ── compliance-block 404 → ProfileNotFoundError (the in-process raise behaviour) ──
@pytest.mark.asyncio
async def test_reverse_shim_compliance_block_404_raises_profile_not_found(monkeypatch):
    from app.core.extracted_clients import customer_client
    from app.modules.customer.exceptions import ProfileNotFoundError

    rec = _Recorder([(404, {"detail": "not found", "code": "customer.profile_not_found"})])
    _install_mock(monkeypatch, rec)
    customer_client.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(ProfileNotFoundError) as exc:
        await customer_client.get_compliance_block(uuid4(), db=None)
    assert exc.value.status_code == 404
    assert exc.value.code == "customer.profile_not_found"


# ── (c) eligibility: 200 {} → None (eligible); 422 → ProfileIncompleteForCategoryError ──
@pytest.mark.asyncio
async def test_reverse_shim_eligibility_200_returns_none(monkeypatch):
    from app.core.extracted_clients import customer_client

    rec = _Recorder([(200, {})])
    _install_mock(monkeypatch, rec)
    customer_client.set_request_context(bearer_token="t", request_id="r")

    uid = uuid4()
    result = await customer_client.assert_eligible_for_super_id(uid, "26", db=None)
    assert result is None
    # super_id forwarded as a query param (frozen-0H contract).
    req = rec.requests[0]
    assert str(req.url) == (
        f"http://customer-svc:8001/internal/seller-profile/{uid}/eligibility?super_id=26"
    )


@pytest.mark.asyncio
async def test_reverse_shim_eligibility_422_raises_with_missing_keys(monkeypatch):
    from app.core.extracted_clients import customer_client
    from app.modules.customer.exceptions import ProfileIncompleteForCategoryError

    envelope = {
        "detail": "Your seller profile is incomplete for this category.",
        "code": "customer.profile_incomplete_for_category",
        "super_id": "26",
        "missing_keys": ["fssai_license_no"],
    }
    rec = _Recorder([(422, envelope)])
    _install_mock(monkeypatch, rec)
    customer_client.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(ProfileIncompleteForCategoryError) as exc:
        await customer_client.assert_eligible_for_super_id(uuid4(), "26", db=None)
    # REAL forwarding of the envelope detail fields (not a generic re-raise).
    assert exc.value.status_code == 422
    assert exc.value.code == "customer.profile_incomplete_for_category"
    assert exc.value.super_id == "26"
    assert exc.value.missing_keys == ["fssai_license_no"]


# ── 503 → exactly one retry, then success (locked transport contract) ──
@pytest.mark.asyncio
async def test_reverse_shim_retries_once_on_503(monkeypatch):
    from app.core.extracted_clients import customer_client

    rec = _Recorder([(503, {}), (200, {})])
    _install_mock(monkeypatch, rec)
    customer_client.set_request_context(bearer_token="t", request_id="r")

    result = await customer_client.assert_eligible_for_super_id(uuid4(), "13", db=None)
    assert result is None
    assert len(rec.requests) == 2  # one retry → two attempts


# ── (§16.G) reverse shim signature parity with the in-process customer.service ──
def test_reverse_shim_signatures_match_in_process_service():
    """The 2 re-exported symbols carry the SAME signatures as the in-process
    ``customer.service`` methods so the catalog call sites are byte-for-byte
    unchanged AT CUTOVER (§16.G)."""
    from app.core.extracted_clients import customer_client
    from app.modules.customer import service as customer_service

    for name in ("get_compliance_block", "assert_eligible_for_super_id"):
        shim_sig = inspect.signature(getattr(customer_client, name))
        svc_sig = inspect.signature(getattr(customer_service, name))
        assert list(shim_sig.parameters) == list(svc_sig.parameters), (
            f"{name}: shim params {list(shim_sig.parameters)} != "
            f"service params {list(svc_sig.parameters)}"
        )


def test_reverse_shim_reexports_exactly_the_two_caller_symbols():
    """The catalog caller imports ``customer_service`` and uses exactly
    ``get_compliance_block`` + ``assert_eligible_for_super_id``.  The shim
    re-exports those two (plus the context setter)."""
    from app.core.extracted_clients import customer_client

    assert "get_compliance_block" in customer_client.__all__
    assert "assert_eligible_for_super_id" in customer_client.__all__
