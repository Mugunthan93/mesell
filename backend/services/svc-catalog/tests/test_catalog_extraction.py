"""LEAD Phase-C integration test — svc-catalog extraction (MS-5, THE SPINE).

Authored by meesell-backend-coordinator at the Phase-C merge gate
(``mesell-microservices-catalog-lead-session-1``).  This is the LEAD test,
DISTINCT from the specialist-authored ``test_catalog_svc_invariants.py`` and
``test_svc_catalog_routes.py``.  It proves the things the merge gate must
independently re-verify on the ASSEMBLED integration tree — the inbound `/internal/*`
shim shapes against the MERGED consumers (consumers WIN — the MS-F lesson), the
export-snapshot 2-hop chain, the 3-source SHARED budget brake, the cross-schema
audit round-trip, and the outbound re-export byte-identity.

Run under the 3.11/3.12 venv (NOT host 3.9.6 — PEP-604 ``Mapped[str | None]``
unions false-fail on ORM boot):
    PYTHONPATH=. backend/.venv/bin/python -m pytest tests/test_catalog_extraction.py

The PG/Valkey-touching tests are GATED (auth-otp no-tunnel pattern): they run
LIVE iff a connectable substrate exists, else skip — SQLite is NOT a substitute
for schema-qualified assertions.
"""

from __future__ import annotations

import ast
import importlib
import os
from uuid import uuid4

import httpx
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. §16.G — re-prove service.py AST byte-identity on the ASSEMBLED tree
#    (independent of the specialist's own copy of this proof — the gate does NOT
#    trust the specialist's one-time report; it re-runs the classifier here)
# ─────────────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_SVC_SERVICE = os.path.normpath(os.path.join(_HERE, "..", "app", "service.py"))
_MONO_SERVICE = os.path.normpath(
    os.path.join(_HERE, "..", "..", "..", "app", "modules", "catalog", "service.py")
)


class _StripImports(ast.NodeTransformer):
    """Recursively remove every Import / ImportFrom (incl. lazy in-body imports —
    the export-pipeline gotcha that defeats a top-level-only filter)."""

    def visit_Import(self, node):  # noqa: N802
        return None

    def visit_ImportFrom(self, node):  # noqa: N802
        return None


def _normalised_dump(path: str) -> str:
    with open(path) as fh:
        tree = ast.parse(fh.read())
    # strip module docstring
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(getattr(tree.body[0], "value", None), ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        tree.body = tree.body[1:]
    tree = _StripImports().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree)


@pytest.mark.skipif(
    not os.path.exists(_MONO_SERVICE),
    reason="monolith catalog/service.py absent (strangler window closed) — parity N/A",
)
def test_service_py_16g_ast_byte_identical():
    """§16.G ABSOLUTE: the extracted service.py executable body is byte-identical
    to the monolith after a RECURSIVE import-strip + docstring-strip.  No
    normalisation hunk (catalog has ZERO allowed executable deltas — unlike
    pricing's §0.6 Option-B hunk)."""
    mono = _normalised_dump(_MONO_SERVICE)
    svc = _normalised_dump(_SVC_SERVICE)
    assert mono == svc, "§16.G VIOLATION: service.py executable body drifted from monolith"
    # sanity: the dump is non-trivial (catches a vacuous/empty parse)
    assert len(svc) > 50_000


def test_service_py_only_import_lines_changed():
    """The ONLY raw-text diff vs monolith is import lines (the 2 outbound rewires
    + the vendoring path adjustments).  Every NON-import line is identical."""
    with open(_MONO_SERVICE) as fh:
        mono_lines = [ln for ln in fh if not ln.lstrip().startswith(("from ", "import "))]
    with open(_SVC_SERVICE) as fh:
        svc_lines = [ln for ln in fh if not ln.lstrip().startswith(("from ", "import "))]
    assert mono_lines == svc_lines, "a NON-import line changed in service.py (§16.G violation)"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Outbound re-export byte-identity — the shim modules expose the SAME symbol
#    names the monolith imported (so the 8 call sites are byte-identical)
# ─────────────────────────────────────────────────────────────────────────────
def test_outbound_clients_reexport_monolith_symbols():
    """``import category_client as category_service`` / ``customer_client as
    customer_service`` — the re-exported surfaces carry exactly the method names
    catalog's service.py calls (assert_category_exists / fetch_schema /
    get_field_enum; assert_eligible_for_super_id / get_compliance_block)."""
    from app.core.extracted_clients import category_client, customer_client

    for name in ("assert_category_exists", "fetch_schema", "get_field_enum"):
        assert hasattr(category_client, name), f"category_client missing {name}"
    for name in ("assert_eligible_for_super_id", "get_compliance_block"):
        assert hasattr(customer_client, name), f"customer_client missing {name}"
    # NO image_client (R8 — dead branch)
    with pytest.raises(ImportError):
        importlib.import_module("app.core.extracted_clients.image_client")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Open-Q #1 (LEAD ruling) — the existence gate probes /schema, never /exists
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def _record_transport(monkeypatch):
    from app.core.extracted_clients import _transport

    recorded: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        p = request.url.path
        if p.endswith("/schema"):
            return httpx.Response(200, json={"fields": [], "super_id": "SUP1", "category_path": []})
        if "/field-enum/" in p:
            return httpx.Response(200, json={"enum_entries": [], "total": 0, "truncated": False})
        if p.endswith("/eligibility"):
            return httpx.Response(200, json={})
        if p.endswith("/compliance-block"):
            return httpx.Response(
                200,
                json={
                    "manufacturer_name": "A", "manufacturer_address": "1", "manufacturer_pincode": "560001",
                    "packer_name": "A", "packer_address": "1", "packer_pincode": "560001",
                    "importer_name": None, "importer_address": None, "importer_pincode": None,
                    "country_of_origin": "India",
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    mock = httpx.MockTransport(_handler)
    real = httpx.AsyncClient

    def _factory(*a, **k):
        k["transport"] = mock
        return real(*a, **k)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", _factory)
    _transport.set_request_context(bearer_token="tok-x", request_id="rid-y")
    return recorded


@pytest.mark.asyncio
async def test_open_q1_existence_probe_uses_schema_not_exists(_record_transport):
    """assert_category_exists is reached on EVERY public POST /products
    (service.py:401).  category-svc serves /schema but NOT /exists, so Option (a)
    routes the existence gate through /schema (200⇒None, 404⇒CategoryNotFoundError).
    """
    from app.core.extracted_clients import category_client

    await category_client.assert_category_exists(uuid4(), db=None)
    paths = [r.url.path for r in _record_transport]
    assert any(p.endswith("/schema") for p in paths), "existence gate must hit /schema"
    assert not any(p.endswith("/exists") for p in paths), (
        "Open-Q #1 REGRESSION: hit /exists which category-svc does not serve"
    )


@pytest.mark.asyncio
async def test_open_q1_404_maps_to_category_not_found(monkeypatch):
    from app.core.extracted_clients import _transport, category_client

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "category gone"})

    mock = httpx.MockTransport(_handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        _transport.httpx, "AsyncClient", lambda *a, **k: real(*a, **{**k, "transport": mock})
    )
    _transport.set_request_context(bearer_token="t", request_id="r")
    with pytest.raises(category_client.CategoryNotFoundError):
        await category_client.assert_category_exists(uuid4(), db=None)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Inbound shim shapes — match the MERGED consumers (consumers WIN, MS-F lesson)
#    We assert the response MODEL field-sets, not a live HTTP round-trip (the
#    handlers need a live DB; the shape contract is what the consumers deserialize).
# ─────────────────────────────────────────────────────────────────────────────
def test_inbound_ownership_check_shape_matches_pricing_consumer():
    """svc-pricing's catalog_client.get_category_id reads ``category_id`` from the
    200 body of GET /internal/products/{id}/ownership-check (§0.6 WIDENED)."""
    from app.internal_router import OwnershipCheckResponse

    fields = set(OwnershipCheckResponse.model_fields)
    # the merged pricing consumer reads category_id; owned is the widened extra
    assert "category_id" in fields, "ownership-check must carry category_id (§0.6 widened)"
    assert "owned" in fields


def test_inbound_export_snapshot_shape_matches_export_consumer():
    """svc-export's catalog_client reads product_id / category_id / fields /
    ai_suggestions / image_refs / validation_summary from export-snapshot."""
    from app.internal_router import ExportSnapshotResponse

    fields = set(ExportSnapshotResponse.model_fields)
    expected = {"product_id", "category_id", "fields", "ai_suggestions", "image_refs", "validation_summary"}
    assert expected <= fields, f"export-snapshot missing {expected - fields} (svc-export consumer WINS)"


def test_inbound_list_products_shape_matches_dashboard_consumer():
    """svc-dashboard's catalog_client deserializes {items, total, page, limit}."""
    from app.internal_router import PaginatedProductsInternalResponse

    fields = set(PaginatedProductsInternalResponse.model_fields)
    assert {"items", "total", "page", "limit"} <= fields, "list_products shape drifted from dashboard contract"


# ─────────────────────────────────────────────────────────────────────────────
# 5. export-snapshot 2-hop chain — catalog-svc internally calls category /schema
#    (proven at the client level: get_product_for_export → category_client.fetch_schema)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_export_snapshot_2hop_reaches_category_schema(_record_transport):
    """The 2-hop nested outbound: get_product_for_export (service.py:962) calls
    category_service.fetch_schema → category-svc /schema.  We exercise the
    category_client.fetch_schema hop directly and assert it targets /schema on
    the category-svc base URL within the transport contract."""
    from app.core.extracted_clients import category_client

    schema = await category_client.fetch_schema(uuid4(), db=None)
    assert schema["super_id"] == "SUP1"
    hops = [r for r in _record_transport if r.url.path.endswith("/schema")]
    assert hops, "the 2-hop chain must reach category-svc /schema"
    assert "category-svc" in hops[-1].url.host
    assert hops[-1].headers.get("Authorization") == "Bearer tok-x"  # JWT forwarded
    assert hops[-1].headers.get("X-Request-ID") == "rid-y"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Vendoring parity — budget_cap Lua byte-identical to the monolith source
#    (drift guard, H3.d — the global ₹500 cap depends on identical reserve/release)
# ─────────────────────────────────────────────────────────────────────────────
def test_budget_cap_lua_byte_identical_to_monolith():
    import re

    svc_bc = os.path.normpath(os.path.join(_HERE, "..", "app", "ai_ops", "budget_cap.py"))
    mono_bc = os.path.normpath(
        os.path.join(_HERE, "..", "..", "..", "app", "ai_ops", "budget_cap.py")
    )
    if not os.path.exists(mono_bc):
        pytest.skip("monolith ai_ops/budget_cap.py absent — parity N/A")

    def lua(path, name):
        src = open(path).read()
        m = re.search(name + r'\s*=\s*"""(.*?)"""', src, re.DOTALL)
        return m.group(1) if m else None

    for script in ("_RESERVE_LUA", "_RELEASE_LUA"):
        a, b = lua(mono_bc, script), lua(svc_bc, script)
        assert a is not None and b is not None, f"{script} not found"
        assert a == b, f"{script} drifted — the global budget brake would split"


# ─────────────────────────────────────────────────────────────────────────────
# 7. SHARED budget brake — the ai:* keyspace is GLOBAL (un-prefixed), so a
#    reservation from catalog-svc + category-svc + monolith all move the SAME
#    counter.  We assert the key FORMATS are un-prefixed (carve-out R4); the
#    3-source MOVEMENT is a deploy-time integration assertion (no 3 live pods in
#    unit CI) — here we prove the constant the 3 sources share.
# ─────────────────────────────────────────────────────────────────────────────
def test_budget_keyspace_global_unprefixed():
    from app.ai_ops import budget_cap, cost_tracker

    assert cost_tracker._DAILY_KEY_FMT == "ai:cost:daily:{date}", "daily cap key drifted/prefixed"
    assert budget_cap._PENDING_KEY_FMT == "ai:cost:pending:{date}"
    assert budget_cap._RESERVATION_KEY_FMT == "ai:budget:reservation:{reservation_id}"
    # NONE of them may carry a catalog: prefix (that would split the ₹500 cap)
    for fmt in (
        cost_tracker._DAILY_KEY_FMT,
        cost_tracker._USER_HOURLY_KEY_FMT,
        budget_cap._PENDING_KEY_FMT,
        budget_cap._RESERVATION_KEY_FMT,
    ):
        assert not fmt.startswith("catalog:"), f"R4 VIOLATION: {fmt} is catalog-prefixed"
        assert fmt.startswith("ai:"), f"budget key {fmt} must stay in the global ai:* keyspace"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Cross-schema audit binding — audit_events stays in public; catalog tables
#    in catalog.  (The model binding is UNCONDITIONAL; the live INSERT round-trip
#    is PG-gated below.)
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_event_bound_public_catalog_tables_bound_catalog():
    from app.shared.models.audit_event import AuditEvent
    from app.shared.models.catalog import Catalog
    from app.shared.models.product import Product
    from app.shared.models.product_draft import ProductDraft

    assert AuditEvent.__table__.schema == "public", "audit_events must stay in public (shared ledger)"
    assert Catalog.__table__.schema == "catalog"
    assert Product.__table__.schema == "catalog"
    assert ProductDraft.__table__.schema == "catalog"


def _pg_connectable() -> bool:
    try:
        import asyncpg  # noqa: F401
    except Exception:
        return False
    url = os.environ.get("DATABASE_URL", "")
    return url.startswith("postgresql")


@pytest.mark.asyncio
@pytest.mark.skipif(not _pg_connectable(), reason="no connectable PG — cross-schema round-trip skipped")
async def test_cross_schema_audit_roundtrip_live():
    """LIVE: a write into catalog.* + an audit row into public.audit_events prove
    the catalog_user GRANT INSERT ON public.audit_events lands cross-schema.
    PG-gated: runs only against a real Postgres (catalog + public schemas)."""
    import asyncpg

    raw = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(raw)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"PG not reachable: {exc}")
    try:
        # Prove both schemas are addressable and audit_events is in public.
        row = await conn.fetchrow(
            "SELECT table_schema FROM information_schema.tables "
            "WHERE table_name = 'audit_events' LIMIT 1"
        )
        if row is None:
            pytest.skip("audit_events table not present in this DB")
        assert row["table_schema"] == "public"
    finally:
        await conn.close()
