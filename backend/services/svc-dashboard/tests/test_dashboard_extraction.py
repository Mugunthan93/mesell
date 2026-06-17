"""Hybrid-mode integration test for the svc-dashboard extraction (Sub-Plan B,
Phase C).

LEAD-owned (meesell-backend-coordinator). Session
``mesell-microservices-dashboard-backend-session-1``. This is the integration
test that proves the extraction is CORRECT — not that the code merely imports.

Posture (spec_msB_backend §6 anti-tautology rule — the pricing lesson)
======================================================================
Every assertion is NON-TAUTOLOGICAL. ``assert True`` / "string-in-repr" echoes
are a reject-class offense. The five classes of proof here:

1. **§16.G in-process parity (UNCONDITIONAL).** Both ``service.py`` twins are
   parsed with ``ast``; the module docstring + EVERY import (top-level AND
   lazy/nested, via a recursive ``ast.NodeTransformer``) are stripped, and the
   REMAINING executable AST is compared node-for-node. This re-proves the
   §16.G ABSOLUTE CONTRACT ("zero non-import line changes") on EVERY CI run
   instead of trusting the one-time services-builder diff report. Dashboard
   has no lazy in-function imports today, but the recursive transformer is used
   anyway (recipe §2) so a future lazy import cannot create a false positive.

2. **Wire-shape JSON-schema parity (UNCONDITIONAL).** ``DashboardResponse``,
   ``ProductListItem`` and ``ProfileCompletenessSummary`` produce a byte-
   identical JSON Schema to the monolith ``modules/dashboard/schemas`` twins
   (``description`` prose stripped). ``model_json_schema()`` is the REAL wire
   contract; drift here is a runtime 4xx surprise for the frontend.

3. **Shim JWT-forward + real-deserialize (UNCONDITIONAL, httpx.MockTransport).**
   Both shims (``catalog_client.list_products``,
   ``customer_client.get_onboarding_completeness``) are driven through their
   real ``_transport`` path with a mocked ClusterIP. Proves: (a) the right
   verb/URL/query-params, (b) the JWT + X-Request-ID are forwarded, (c) the
   monolith's REAL JSON shape deserializes into the frozen domain object the
   pipeline reads, (d) the locked 5s/2s timeout, (e) exactly-one-retry only on
   503/504.

4. **Compose correctness (UNCONDITIONAL).** ``_compose_response`` (pure) is
   invoked with mocked domain objects and the field mapping is asserted —
   including the ``Product.id`` → ``ProductListItem.product_id`` rename, the
   5-field completeness 1:1 copy, total/page/limit passthrough, and the
   EMPTY-inventory case (zero products → 200-shape ``DashboardResponse`` with
   an empty list, NOT a 404).

5. **Flag guard (UNCONDITIONAL).** With
   ``FEATURE_TRACKING_DASHBOARD_ENABLED=false`` the route raises 404 BEFORE any
   service/shim call — proven by mocking the service to explode if reached.

No live infra is required for any of the five classes — they all run green on
the no-tunnel baseline (dashboard owns no schema, so there is no PG-gated
round-trip at all, unlike the SP01 export cross-schema audit test).
"""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

# ── Resolve both trees relative to this file (no hard-coded abs paths) ───────
_SVC_ROOT = Path(__file__).resolve().parents[1]  # backend/services/svc-dashboard
_BACKEND_ROOT = _SVC_ROOT.parents[1]  # backend/
_MONOLITH_DASHBOARD = _BACKEND_ROOT / "app" / "modules" / "dashboard"
_SVC_APP = _SVC_ROOT / "app"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — AST normalisation for the §16.G parity proof
# ─────────────────────────────────────────────────────────────────────────────
class _ImportStripper(ast.NodeTransformer):
    """Removes every ``import`` / ``from … import`` statement ANYWHERE in the
    tree — including lazy imports nested inside function bodies. Dashboard's
    ``service.py`` has none today, but the recursive form is used per recipe §2
    so that a future lazy import (the §16.G permitted diff) cannot silently
    fail this gate as a false positive."""

    def visit_Import(self, node: ast.Import):  # noqa: N802
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
        return None


def _executable_body_dump(source: str) -> str:
    """``ast.dump`` of a module with the leading docstring and ALL imports
    (top-level AND nested) removed.

    Isolates the EXECUTABLE pipeline logic. ``ast.dump`` is whitespace- and
    comment-insensitive and order-sensitive, so two modules produce an identical
    dump iff their non-import, non-docstring code is structurally identical.
    """
    tree = ast.parse(source)
    body = list(tree.body)
    # Drop the module docstring (first node, if it is a bare string Expr).
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    stripped = ast.Module(body=body, type_ignores=[])
    stripped = _ImportStripper().visit(stripped)
    ast.fix_missing_locations(stripped)
    return ast.dump(stripped, annotate_fields=True, include_attributes=False)


def _import_targets(source: str) -> list[str]:
    """Human-readable import targets of a module, for diagnostics."""
    tree = ast.parse(source)
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            out.extend(
                f"{mod}.{a.name} as {a.asname}" if a.asname else f"{mod}.{a.name}"
                for a in node.names
            )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 1. §16.G ABSOLUTE CONTRACT — executable body of service.py twins is identical
# ─────────────────────────────────────────────────────────────────────────────
def test_service_py_executable_body_byte_for_byte_identical():
    """The extracted ``service.py`` pipeline is structurally identical to the
    monolith twin once docstring + imports are stripped (§16.G).

    Any executable-line drift in either tree fails here — the CI-enforced
    re-proof of the services-builder one-time diff report.
    """
    monolith = (_MONOLITH_DASHBOARD / "service.py").read_text()
    extracted = (_SVC_APP / "service.py").read_text()

    mono_body = _executable_body_dump(monolith)
    svc_body = _executable_body_dump(extracted)

    assert svc_body == mono_body, (
        "§16.G VIOLATION: the extracted service.py executable body diverged "
        "from the monolith twin. The ONLY permitted diff is import lines + the "
        "module docstring. Re-run the AST classifier to locate the drift."
    )


def test_service_py_imports_rewritten_only_as_specified():
    """The §16.G permitted diff: the 2 cross-module imports were rewritten to
    ``extracted_clients`` re-exporting the SAME ``<callee>_service`` symbol, and
    the domain-type imports were repointed at the shim modules. Symbol names are
    preserved so the call sites in ``list_products_for_dashboard`` are unchanged
    (proven structurally by test #1 above)."""
    extracted = (_SVC_APP / "service.py").read_text()
    joined = "\n".join(_import_targets(extracted))

    # The 2 cross-module shims re-export the monolith symbol names verbatim.
    assert "app.core.extracted_clients.catalog_client as catalog_service" in joined
    assert "app.core.extracted_clients.customer_client as customer_service" in joined
    # The domain types now resolve from the shim modules (frozen mirrors).
    assert "app.core.extracted_clients.catalog_client.PaginatedProductsInternal" in joined
    assert "app.core.extracted_clients.catalog_client.Pagination" in joined
    assert "app.core.extracted_clients.customer_client.ProfileCompleteness" in joined
    # The monolith module-path imports must be GONE (proves the rewrite landed).
    assert "app.modules.catalog" not in joined
    assert "app.modules.customer" not in joined
    assert "app.modules.dashboard" not in joined


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wire-shape parity — the response schemas match the monolith field-for-field
# ─────────────────────────────────────────────────────────────────────────────
def _strip_descriptions(obj):
    """Recursively drop ``description`` keys from a JSON-schema dict — prose-only
    documentation that is not part of the serialisation contract."""
    if isinstance(obj, dict):
        return {k: _strip_descriptions(v) for k, v in obj.items() if k != "description"}
    if isinstance(obj, list):
        return [_strip_descriptions(v) for v in obj]
    return obj


@pytest.mark.parametrize(
    "model_name",
    ["DashboardResponse", "ProductListItem", "ProfileCompletenessSummary"],
)
def test_wire_shape_matches_monolith_field_for_field(model_name):
    """Each svc-dashboard wire model produces a byte-identical JSON Schema to the
    monolith ``modules/dashboard/schemas`` twin (``description`` excluded). Drift
    here = a runtime 4xx surprise for the frontend, so it is a hard gate.

    The monolith schemas module is loaded in isolation via ``importlib`` from
    file path and registered in ``sys.modules`` BEFORE ``exec_module`` so
    Pydantic can resolve the ``from __future__ import annotations`` ForwardRefs
    (``UUID`` / ``datetime`` / ``Literal``) against the module's own namespace.
    """
    import importlib.util
    import sys

    # svc-dashboard model (already on sys.path via PYTHONPATH).
    from app import schemas as svc_schemas

    mod_name = "_monolith_dashboard_schemas"
    mono_path = _MONOLITH_DASHBOARD / "schemas.py"
    spec = importlib.util.spec_from_file_location(mod_name, mono_path)
    assert spec is not None and spec.loader is not None
    mono_mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mono_mod
    try:
        spec.loader.exec_module(mono_mod)
        svc_model = getattr(svc_schemas, model_name)
        mono_model = getattr(mono_mod, model_name)
        # Force ForwardRef resolution against the registered module namespace.
        mono_model.model_rebuild(_types_namespace=vars(mono_mod))
    finally:
        sys.modules.pop(mod_name, None)

    svc_schema = _strip_descriptions(svc_model.model_json_schema())
    mono_schema = _strip_descriptions(mono_model.model_json_schema())

    assert svc_schema == mono_schema, (
        f"Wire-shape DRIFT in {model_name} (prose descriptions excluded):\n"
        f"  svc-dashboard: {svc_schema}\n"
        f"  monolith:      {mono_schema}\n"
        "A frontend consuming the monolith contract would break on svc-dashboard."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. HTTP-shim mode — drive both shims through the real _transport call path.
# ─────────────────────────────────────────────────────────────────────────────
class _Recorder:
    """Captures requests + the client construction timeout, replays a queued
    list of ``(status, body)`` responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []
        self.timeouts: list[httpx.Timeout] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._responses.pop(0)
        return httpx.Response(status_code=status, json=body)


def _install_mock(monkeypatch, recorder: _Recorder) -> None:
    """Patch ``_transport.httpx.AsyncClient`` so every constructed client routes
    through a ``MockTransport`` and records the timeout it was built with."""
    from app.core.extracted_clients import _transport

    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        recorder.timeouts.append(kwargs.get("timeout"))
        kwargs["transport"] = httpx.MockTransport(recorder.handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", factory)


def _product_json(pid, cid):
    """A realistic monolith ``/internal/products`` item shape (catalog.domain
    .Product, catalog/domain.py:35)."""
    return {
        "id": str(pid),
        "user_id": str(uuid4()),
        "catalog_id": str(uuid4()),
        "category_id": str(cid),
        "name": "Cotton Kurta",
        "status": "ready",
        "fields": {"color": "red", "size": "M"},
        "ai_suggestions": {"material": {"value": "cotton"}},
        "created_at": "2026-06-10T09:00:00+00:00",
        "updated_at": "2026-06-11T09:00:00+00:00",
        "deleted_at": None,
    }


@pytest.mark.asyncio
async def test_catalog_shim_forwards_jwt_and_deserialises_paginated_products(monkeypatch):
    """``catalog_service.list_products`` issues
    ``GET /internal/products?page=&limit=`` with the forwarded JWT +
    X-Request-ID, honours the locked 5s/2s timeout, and deserialises the
    monolith JSON into a frozen ``PaginatedProductsInternal`` whose ``Product``
    items carry the exact attributes ``_compose_response`` reads.

    The call goes through ``catalog_service`` — the SAME symbol the pipeline
    imports — so this exercises the real shim wiring, not a stand-in.
    """
    from app.service import catalog_service  # the re-exported shim surface
    from app.core.extracted_clients import _transport
    from app.core.extracted_clients.catalog_client import (
        PaginatedProductsInternal,
        Pagination,
        Product,
    )

    pid, cid = uuid4(), uuid4()
    body = {
        "items": [_product_json(pid, cid)],
        "total": 1,
        "page": 2,
        "limit": 20,
    }
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="real-jwt-tok", request_id="req-corr-99")

    result = await catalog_service.list_products(
        user_id=uuid4(),
        pagination=Pagination(page=2, limit=20),
        db=object(),
    )

    # (a) verb / URL / query-params.
    assert len(rec.requests) == 1
    req = rec.requests[0]
    assert req.method == "GET"
    assert str(req.url).startswith("http://monolith-svc:8001/internal/products")
    assert req.url.params.get("page") == "2"
    assert req.url.params.get("limit") == "20"
    # (b) JWT + X-Request-ID forwarded. user_id is NOT in the URL (tenant from JWT).
    assert req.headers.get("Authorization") == "Bearer real-jwt-tok"
    assert req.headers.get("X-Request-ID") == "req-corr-99"
    assert "user_id" not in str(req.url)
    # (c) locked transport timeout: 5s read / 2s connect.
    assert rec.timeouts[0].read == 5.0
    assert rec.timeouts[0].connect == 2.0
    # (d) deserialised into the REAL frozen shape the pipeline reads.
    assert isinstance(result, PaginatedProductsInternal)
    assert result.total == 1
    assert result.page == 2
    assert result.limit == 20
    assert len(result.items) == 1
    item = result.items[0]
    assert isinstance(item, Product)
    assert item.id == pid
    assert item.category_id == cid
    assert item.name == "Cotton Kurta"
    assert item.status == "ready"
    assert item.created_at == datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc)
    assert item.updated_at == datetime(2026, 6, 11, 9, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_customer_shim_forwards_jwt_and_deserialises_completeness(monkeypatch):
    """``customer_service.get_onboarding_completeness`` issues
    ``GET /internal/seller-profile/{user_id}/onboarding-completeness`` with the
    forwarded JWT + X-Request-ID and deserialises the 5-field
    ``ProfileCompleteness`` (the exact fields ``_compose_response`` copies)."""
    from app.service import customer_service
    from app.core.extracted_clients import _transport
    from app.core.extracted_clients.customer_client import ProfileCompleteness

    uid = uuid4()
    body = {
        "base_complete_count": 8,
        "base_total_count": 10,
        "extension_complete_count": 2,
        "extension_total_count": 5,
        "onboarding_complete": False,
    }
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="jwt-cust", request_id="rid-cust")

    result = await customer_service.get_onboarding_completeness(user_id=uid, db=object())

    assert len(rec.requests) == 1
    req = rec.requests[0]
    assert req.method == "GET"
    # user_id IS in the URL path for this shim (callee re-verifies vs JWT sub).
    assert str(req.url) == (
        f"http://monolith-svc:8001/internal/seller-profile/{uid}/onboarding-completeness"
    )
    assert req.headers.get("Authorization") == "Bearer jwt-cust"
    assert req.headers.get("X-Request-ID") == "rid-cust"
    assert rec.timeouts[0].read == 5.0
    assert rec.timeouts[0].connect == 2.0
    # 5-field deserialisation into the frozen mirror.
    assert isinstance(result, ProfileCompleteness)
    assert result.base_complete_count == 8
    assert result.base_total_count == 10
    assert result.extension_complete_count == 2
    assert result.extension_total_count == 5
    assert result.onboarding_complete is False


@pytest.mark.asyncio
async def test_transport_retries_once_on_503_then_succeeds(monkeypatch):
    """The locked transport contract: a 503 triggers EXACTLY ONE retry; the
    second (200) response is returned. Two requests are issued, not three."""
    from app.service import customer_service
    from app.core.extracted_clients import _transport

    body = {
        "base_complete_count": 0,
        "base_total_count": 10,
        "extension_complete_count": 0,
        "extension_total_count": 0,
        "onboarding_complete": False,
    }
    rec = _Recorder([(503, {}), (200, body)])  # 503 once, then 200
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    result = await customer_service.get_onboarding_completeness(user_id=uuid4(), db=object())

    # Exactly one retry → two total attempts.
    assert len(rec.requests) == 2
    assert result.base_total_count == 10


@pytest.mark.asyncio
async def test_transport_does_not_retry_on_500(monkeypatch):
    """A 500 is deterministic — NO retry. Exactly one request, and the
    non-2xx surfaces as ``httpx.HTTPStatusError`` (the customer shim only
    translates 404 → typed; 500 bubbles)."""
    from app.service import catalog_service
    from app.core.extracted_clients import _transport
    from app.core.extracted_clients.catalog_client import Pagination

    rec = _Recorder([(500, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(httpx.HTTPStatusError):
        await catalog_service.list_products(
            user_id=uuid4(), pagination=Pagination(page=1, limit=20), db=object()
        )
    assert len(rec.requests) == 1


@pytest.mark.asyncio
async def test_customer_shim_404_maps_to_typed_exception(monkeypatch):
    """A 404 from the customer endpoint maps to the typed
    ``ProfileNotFoundError`` — NOT a raw httpx error. (Live contract returns
    200 for first-time sellers; this proves the parity error surface.)"""
    from app.service import customer_service
    from app.core.extracted_clients import _transport, customer_client

    rec = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(customer_client.ProfileNotFoundError):
        await customer_service.get_onboarding_completeness(user_id=uuid4(), db=object())
    assert len(rec.requests) == 1  # no retry on a 4xx


# ─────────────────────────────────────────────────────────────────────────────
# 4. Compose correctness — _compose_response is pure; assert field mapping.
# ─────────────────────────────────────────────────────────────────────────────
def _mk_completeness(**over):
    from app.core.extracted_clients.customer_client import ProfileCompleteness

    base = dict(
        base_complete_count=8,
        base_total_count=10,
        extension_complete_count=2,
        extension_total_count=5,
        onboarding_complete=False,
    )
    base.update(over)
    return ProfileCompleteness(**base)


def _mk_product(pid, cid, **over):
    from app.core.extracted_clients.catalog_client import Product

    base = dict(
        id=pid,
        user_id=uuid4(),
        catalog_id=uuid4(),
        category_id=cid,
        name="Cotton Kurta",
        status="ready",
        fields={},
        ai_suggestions={},
        created_at=datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 11, 9, 0, tzinfo=timezone.utc),
        deleted_at=None,
    )
    base.update(over)
    return Product(**base)


def test_compose_maps_fields_and_renames_id_to_product_id():
    """``_compose_response`` (pure) maps ``Product.id`` → ``ProductListItem
    .product_id`` (the boundary rename), copies the other 5 product fields 1:1,
    copies the 5 completeness fields 1:1, and passes total/page/limit through."""
    # _compose_response is module-private (not in __all__); access via the module.
    import app.service as svc
    from app.core.extracted_clients.catalog_client import PaginatedProductsInternal

    pid, cid = uuid4(), uuid4()
    product = _mk_product(pid, cid, name="Silk Saree", status="draft")
    paginated = PaginatedProductsInternal(items=(product,), total=37, page=2, limit=20)
    completeness = _mk_completeness(
        base_complete_count=9,
        extension_complete_count=3,
        extension_total_count=6,
        onboarding_complete=True,
    )

    resp = svc._compose_response(paginated=paginated, completeness=completeness)

    # total/page/limit passthrough.
    assert resp.total == 37
    assert resp.page == 2
    assert resp.limit == 20
    # one product row, with the id→product_id rename + 1:1 copies.
    assert len(resp.products) == 1
    row = resp.products[0]
    assert row.product_id == pid  # the rename: Product.id → ProductListItem.product_id
    assert row.category_id == cid
    assert row.name == "Silk Saree"
    assert row.status == "draft"
    assert row.created_at == product.created_at
    assert row.updated_at == product.updated_at
    # 5-field completeness 1:1.
    s = resp.onboarding_completeness
    assert s.base_complete_count == 9
    assert s.base_total_count == 10
    assert s.extension_complete_count == 3
    assert s.extension_total_count == 6
    assert s.onboarding_complete is True


def test_compose_empty_inventory_is_200_shape_not_404():
    """Zero products composes a valid 200-shape ``DashboardResponse`` with an
    EMPTY products list and ``total=0`` — empty inventory is a valid first-time
    seller state, NOT a 404 (spec §6 + router.py:107 contract)."""
    import app.service as svc
    from app.core.extracted_clients.catalog_client import PaginatedProductsInternal

    paginated = PaginatedProductsInternal(items=(), total=0, page=1, limit=20)
    completeness = _mk_completeness(
        base_complete_count=0,
        extension_complete_count=0,
        extension_total_count=0,
        onboarding_complete=False,
    )

    resp = svc._compose_response(paginated=paginated, completeness=completeness)

    assert resp.products == []  # empty list, not an error
    assert resp.total == 0
    assert resp.page == 1
    assert resp.limit == 20
    # the completeness header strip still renders for a brand-new seller.
    assert resp.onboarding_completeness.base_total_count == 10
    assert resp.onboarding_completeness.onboarding_complete is False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Flag guard — FEATURE_TRACKING_DASHBOARD_ENABLED=false → 404 BEFORE any call.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_flag_disabled_raises_404_before_any_service_call(monkeypatch):
    """With ``FEATURE_TRACKING_DASHBOARD_ENABLED=false`` the route raises 404
    (D3 kill-switch) BEFORE invoking the service — proven by patching the
    service to explode if it is ever reached. The rate_limit decorator is a
    pure tag attach (it returns the handler unchanged), so the handler coroutine
    is directly awaitable here."""
    from fastapi import HTTPException

    import app.router as router_mod
    from app.shared.config import settings

    monkeypatch.setattr(settings, "FEATURE_TRACKING_DASHBOARD_ENABLED", False)

    async def _explode(**_kwargs):  # pragma: no cover — must NOT be reached
        raise AssertionError(
            "service.list_products_for_dashboard was called despite the flag "
            "being disabled — the 404 guard did not short-circuit first."
        )

    monkeypatch.setattr(router_mod.dashboard_service, "list_products_for_dashboard", _explode)

    class _FakeUser:
        user_id = uuid4()
        plan = "free"

    with pytest.raises(HTTPException) as ei:
        await router_mod.list_products(user=_FakeUser(), db=object(), page=1, limit=20)

    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_flag_enabled_reaches_service(monkeypatch):
    """Counter-proof to the flag-guard test: with the flag ENABLED the handler
    builds the ``DashboardQuery`` and delegates to the service (so the 404 above
    is genuinely the flag, not an unconditional 404)."""
    import app.router as router_mod
    from app.shared.config import settings

    monkeypatch.setattr(settings, "FEATURE_TRACKING_DASHBOARD_ENABLED", True)

    seen = {}

    async def _capture(*, user_id, query, db):
        seen["user_id"] = user_id
        seen["page"] = query.page
        seen["limit"] = query.limit
        return "SENTINEL_RESPONSE"

    monkeypatch.setattr(router_mod.dashboard_service, "list_products_for_dashboard", _capture)

    uid = uuid4()

    class _FakeUser:
        user_id = uid
        plan = "free"

    result = await router_mod.list_products(user=_FakeUser(), db=object(), page=3, limit=50)

    assert result == "SENTINEL_RESPONSE"
    assert seen["user_id"] == uid
    assert seen["page"] == 3
    assert seen["limit"] == 50
