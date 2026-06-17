"""Unit tests for the 4 extracted_clients HTTP shims (spec §3.A acceptance).

Transport is mocked via ``httpx.MockTransport``: a factory replaces
``_transport.httpx.AsyncClient`` so every shim call routes through a handler
that records the inbound request(s) and returns a scripted response sequence.

Assertions cover the locked transport contract:
* (a) JWT (``Authorization: Bearer``) + ``X-Request-ID`` forwarded;
* (b) timeout config 5 s read / 2 s connect;
* (c) EXACTLY ONE retry on 503/504, NO retry on 500/4xx;
* (d) the response deserializes into the REAL callee shape
  (ComplianceBlock fields, ExportSnapshotInternal nesting, ImagesListResponse).
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.core.extracted_clients import (
    _transport,
    catalog_client,
    category_client,
    customer_client,
    image_client,
)

pytestmark = pytest.mark.asyncio


# ── Mock-transport harness ──────────────────────────────────────────────────
class _Recorder:
    """Captures requests + the timeout the shim constructed the client with."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []
        self.timeouts: list[httpx.Timeout] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        # Pop the next scripted response (status, json).
        status, body = self._responses.pop(0)
        return httpx.Response(status_code=status, json=body)


def _install_mock(monkeypatch, recorder: _Recorder) -> None:
    """Patch ``_transport.httpx.AsyncClient`` to inject the MockTransport."""
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        recorder.timeouts.append(kwargs.get("timeout"))
        kwargs["transport"] = httpx.MockTransport(recorder.handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", factory)


# ─────────────────────────────────────────────────────────────────────────────
# (a) JWT + X-Request-ID forwarding  +  (b) timeout config
# ─────────────────────────────────────────────────────────────────────────────
async def test_jwt_and_request_id_forwarded_and_timeout_config(monkeypatch):
    rec = _Recorder([(200, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="tok-abc-123", request_id="rid-xyz-789")

    await catalog_client.assert_product_ownership(uuid4(), uuid4(), db=object())

    assert len(rec.requests) == 1
    req = rec.requests[0]
    # (a) JWT + X-Request-ID forwarded.
    assert req.headers.get("Authorization") == "Bearer tok-abc-123"
    assert req.headers.get("X-Request-ID") == "rid-xyz-789"
    # base URL points at the monolith ClusterIP (R4 hybrid).
    assert str(req.url).startswith("http://monolith-svc:8001/internal/products/")
    assert "/ownership-check" in str(req.url)
    # (b) timeout config 5 s read / 2 s connect.
    to = rec.timeouts[0]
    assert to.read == 5.0
    assert to.connect == 2.0


# ─────────────────────────────────────────────────────────────────────────────
# (c) retry policy — EXACTLY ONE retry on 503/504, NONE on 500/4xx
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("transient", [503, 504])
async def test_retry_once_on_transient_then_succeeds(monkeypatch, transient):
    # First response transient, second 200 → exactly 2 requests total (1 retry).
    rec = _Recorder([(transient, {}), (200, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    await catalog_client.assert_product_ownership(uuid4(), uuid4())

    assert len(rec.requests) == 2  # original + EXACTLY ONE retry


@pytest.mark.parametrize("transient", [503, 504])
async def test_retry_exhausts_after_one_attempt(monkeypatch, transient):
    # Both transient → 2 requests then raise (no infinite retry).
    rec = _Recorder([(transient, {}), (transient, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(httpx.HTTPStatusError):
        await catalog_client.assert_product_ownership(uuid4(), uuid4())
    assert len(rec.requests) == 2  # original + ONE retry, then surfaced


async def test_no_retry_on_500(monkeypatch):
    rec = _Recorder([(500, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(httpx.HTTPStatusError):
        await catalog_client.get_product_for_export(uuid4(), uuid4())
    assert len(rec.requests) == 1  # NO retry on 500


async def test_no_retry_on_4xx_maps_to_typed_404(monkeypatch):
    rec = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(catalog_client.ProductNotFoundError):
        await catalog_client.assert_product_ownership(uuid4(), uuid4())
    assert len(rec.requests) == 1  # NO retry on 4xx


async def test_worker_context_forwards_request_id_only(monkeypatch):
    """Worker path: no JWT context, but X-Request-ID still forwarded."""
    rec = _Recorder([(200, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_worker_context(request_id="worker-rid-1")

    await catalog_client.assert_product_ownership(uuid4(), uuid4())

    req = rec.requests[0]
    assert "Authorization" not in req.headers
    assert req.headers.get("X-Request-ID") == "worker-rid-1"


# ─────────────────────────────────────────────────────────────────────────────
# (d) real-shape deserialization
# ─────────────────────────────────────────────────────────────────────────────
async def test_get_compliance_block_deserializes_into_ComplianceBlock(monkeypatch):
    body = {
        "manufacturer_name": "Acme Mfg",
        "manufacturer_address": "1 Mill Rd",
        "manufacturer_pincode": "560001",
        "packer_name": "Acme Pack",
        "packer_address": "2 Dock St",
        "packer_pincode": "560002",
        "importer_name": None,
        "importer_address": None,
        "importer_pincode": None,
        "country_of_origin": "India",
    }
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    block = await customer_client.get_compliance_block(uuid4(), object())

    from app.domain import ComplianceBlock

    assert isinstance(block, ComplianceBlock)
    assert block.manufacturer_name == "Acme Mfg"
    assert block.manufacturer_pincode == "560001"
    assert block.importer_name is None
    assert block.country_of_origin == "India"
    # path target = the frozen /internal contract path.
    assert "/internal/seller-profile/" in str(rec.requests[0].url)
    assert str(rec.requests[0].url).endswith("/compliance-block")


async def test_compliance_block_404_maps_to_profile_not_found(monkeypatch):
    rec = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(customer_client.ProfileNotFoundError):
        await customer_client.get_compliance_block(uuid4(), object())


async def test_get_product_for_export_deserializes_snapshot(monkeypatch):
    pid, cid = uuid4(), uuid4()
    body = {
        "product_id": str(pid),
        "category_id": str(cid),
        "fields": {"color": "red"},
        "ai_suggestions": {"size": {"value": "M"}},
        "image_refs": ["meesell-images/u/p/1.jpg", "meesell-images/u/p/2.jpg"],
        "validation_summary": {
            "status": "ready",
            "product_id": str(pid),
            "compulsory_filled": 3,
            "compulsory_total": 3,
            "optional_filled": 1,
            "optional_total": 2,
            "has_validation_errors": False,
        },
    }
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    snap = await catalog_client.get_product_for_export(pid, uuid4())

    assert snap.product_id == pid
    assert snap.category_id == cid
    assert snap.fields == {"color": "red"}
    assert snap.image_refs == ("meesell-images/u/p/1.jpg", "meesell-images/u/p/2.jpg")
    # The export pipeline reads exactly this attribute path.
    assert snap.validation_summary.status == "ready"
    assert "/export-snapshot" in str(rec.requests[0].url.path)
    assert str(rec.requests[0].url.path).endswith("/export-snapshot")


async def test_fetch_schema_returns_dict_envelope(monkeypatch):
    body = {
        "fields": [{"canonical_name": "color", "meesho_column_header": "Color"}],
        "compliance_shape": "standard",
        "main_sheet_label": "Sheet1",
        "total_count": 1,
    }
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    schema = await category_client.fetch_schema(uuid4(), db=object())

    assert schema["compliance_shape"] == "standard"
    assert schema["fields"][0]["canonical_name"] == "color"
    assert "/internal/categories/" in str(rec.requests[0].url)
    assert str(rec.requests[0].url).endswith("/schema")


async def test_get_field_enum_404_maps_to_field_enum_not_found(monkeypatch):
    rec = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(category_client.FieldEnumNotFoundError):
        await category_client.get_field_enum(uuid4(), "color", object())
    # field-enum path carries the field name segment.
    assert "/field-enum/color" in str(rec.requests[0].url)


async def test_list_images_deserializes_into_ImagesListResponse(monkeypatch):
    img_id = uuid4()
    body = {
        "images": [
            {
                "image_id": str(img_id),
                "idx": 1,
                "status": "ready",
                "signed_url": "https://signed.example/1.jpg",
                "precheck_jsonb": {"jpeg_valid": True},
            }
        ]
    }
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    pid = uuid4()
    resp = await image_client.list_images(user_id=uuid4(), product_id=pid, db=object())

    assert isinstance(resp, image_client.ImagesListResponse)
    assert len(resp.images) == 1
    # The export front-image gate reads exactly img.idx + img.status.
    assert resp.images[0].idx == 1
    assert resp.images[0].status == "ready"
    assert resp.images[0].image_id == img_id
    assert str(rec.requests[0].url).startswith(
        f"http://monolith-svc:8001/internal/products/{pid}/images"
    )
