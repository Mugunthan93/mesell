"""svc-catalog services-builder invariant tests (Phase B).

Proves the LOAD-BEARING extraction invariants for the spine (SUB_PLAN_0H +
spec_msH_backend.md THE FIVE INVARIANTS).  The hybrid-mode integration test
(``test_catalog_extraction.py``) is the LEAD's Phase-C deliverable; THIS file is
the specialist-side proof the extraction is correct.

Covered:
  1. boot + §4.H middleware order
  2. §16.G AST recursive-strip parity — ZERO call-site drift (imports-only)
  3. the 5 import-line rewires (2 cross-module + 3 module-flatten)
  4. the 8 outbound call-site symbols present on the re-exported shims
  5. SHARED budget brake — ``ai:*`` keyspace UN-prefixed (R4 carve-out)
  6. budget_cap.py / cost_tracker.py Lua byte-identical to monolith (H3.d)
  7. scope_to_user preserved on every product/catalog read (§10 leak rule R7)
  8. ORM schema bindings (catalog→catalog; user/audit→public)
  9. ai_ops trim guard — only autofill_v1 prompt vendored (NOT smart/watermark)
 10. dead image getattr branch verbatim + NO image_client shim (R8)
 11. flag-parity — every ``settings.<X>`` read resolves on the trimmed Settings
 12. NO Celery (no celery_app / tasks)
 13. the 5 outbound shims round-trip (httpx.MockTransport) + JWT/X-Request-ID
     forwarding + 503/504-only-retry
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

# Monolith source (read-only — the §16.G twin).
# tests/ → svc-catalog (parents[1]) → services (2) → backend (3) → backend/app.
_MONO_ROOT = Path(__file__).resolve().parents[3] / "app"
_SVC_ROOT = Path(__file__).resolve().parents[1] / "app"


# ─────────────────────────────────────────────────────────────────────────────
# 1. boot + §4.H middleware order
# ─────────────────────────────────────────────────────────────────────────────
def test_app_boots_and_middleware_order():
    from app.main import app

    names = [m.cls.__name__ for m in app.user_middleware]
    # Registration order is reverse of runtime; the §4.H runtime order is
    # CORS → request_id → request_context → auth → tenancy → rate_limit →
    # plan_guard → audit.  user_middleware[0] is outermost (CORS).
    assert names[0] == "CORSMiddleware"
    assert names[-1] == "AuditMiddleware"
    # The 6 §4.H chain members + RequestContext (extraction support) all present.
    for expected in (
        "CORSMiddleware",
        "RequestIdMiddleware",
        "RequestContextMiddleware",
        "AuthContextMiddleware",
        "TenancyContextMiddleware",
        "RateLimitMiddleware",
        "PlanGuardMiddleware",
        "AuditMiddleware",
    ):
        assert expected in names, expected


# ─────────────────────────────────────────────────────────────────────────────
# 2. §16.G AST recursive-strip parity — ZERO call-site drift
# ─────────────────────────────────────────────────────────────────────────────
class _StripImports(ast.NodeTransformer):
    def visit_Import(self, node):  # noqa: N802
        return None

    def visit_ImportFrom(self, node):  # noqa: N802
        return None


def _strip_docstring(tree: ast.Module) -> ast.Module:
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
    ):
        tree.body = tree.body[1:]
    return tree


def _normalized_dump(path: Path) -> str:
    tree = ast.parse(path.read_text())
    tree = _strip_docstring(tree)
    tree = _StripImports().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree)


def test_service_py_16g_ast_parity():
    """service.py stripped of imports + docstring == monolith twin (byte-identical)."""
    mono = _MONO_ROOT / "modules" / "catalog" / "service.py"
    svc = _SVC_ROOT / "service.py"
    assert _normalized_dump(mono) == _normalized_dump(svc), (
        "§16.G VIOLATION — service.py has executable drift beyond the import lines"
    )


def test_repository_py_is_byte_identical():
    """repository.py is byte-identical (zero rewires — same-path vendored imports)."""
    mono = (_MONO_ROOT / "modules" / "catalog" / "repository.py").read_text()
    svc = (_SVC_ROOT / "repository.py").read_text()
    assert mono == svc


def test_domain_and_exceptions_byte_identical():
    for fname in ("domain.py", "exceptions.py"):
        mono = (_MONO_ROOT / "modules" / "catalog" / fname).read_text()
        svc = (_SVC_ROOT / fname).read_text()
        assert mono == svc, fname


# ─────────────────────────────────────────────────────────────────────────────
# 3. the 5 import-line rewires (2 cross-module + 3 module-flatten)
# ─────────────────────────────────────────────────────────────────────────────
def test_only_import_lines_rewired():
    mono = (_MONO_ROOT / "modules" / "catalog" / "service.py").read_text().splitlines()
    svc = (_SVC_ROOT / "service.py").read_text().splitlines()
    diff_removed = [ln for ln in mono if ln not in svc]
    diff_added = [ln for ln in svc if ln not in mono]
    # Every changed line is an import line.
    for ln in diff_removed + diff_added:
        assert ln.lstrip().startswith(("from app", "import app")), ln
    # The 2 LOAD-BEARING cross-module rewires.
    src = "\n".join(svc)
    assert "from app.core.extracted_clients import category_client as category_service" in src
    assert "from app.core.extracted_clients import customer_client as customer_service" in src
    # The monolith cross-module imports are GONE.
    assert "from app.modules.category import service as category_service" not in src
    assert "from app.modules.customer import service as customer_service" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 4. the 8 outbound call-site symbols present on the re-exported shims
# ─────────────────────────────────────────────────────────────────────────────
def test_outbound_callsite_symbols_present():
    import app.service as svc

    assert svc.category_service.__name__.endswith("category_client")
    assert svc.customer_service.__name__.endswith("customer_client")
    for m in ("assert_category_exists", "fetch_schema", "get_field_enum"):
        assert hasattr(svc.category_service, m), m
    for m in ("assert_eligible_for_super_id", "get_compliance_block"):
        assert hasattr(svc.customer_service, m), m


# ─────────────────────────────────────────────────────────────────────────────
# 5 + 6. SHARED budget brake — ai:* UN-prefixed + Lua byte-identical (R4 / H3.d)
# ─────────────────────────────────────────────────────────────────────────────
def test_budget_keyspace_unprefixed_global():
    from app.ai_ops import budget_cap, cost_tracker

    # The 4 budget key families are LITERAL ``ai:*`` strings — NO catalog: prefix.
    assert cost_tracker._DAILY_KEY_FMT == "ai:cost:daily:{date}"
    assert cost_tracker._USER_HOURLY_KEY_FMT == "ai:cost:user:{user_id}:hourly:{date_hour}"
    assert budget_cap._PENDING_KEY_FMT == "ai:cost:pending:{date}"
    assert budget_cap._RESERVATION_KEY_FMT == "ai:budget:reservation:{reservation_id}"
    # Defensive: the literal "catalog:" prefix never appears on a budget key fmt.
    for fmt in (
        cost_tracker._DAILY_KEY_FMT,
        cost_tracker._USER_HOURLY_KEY_FMT,
        budget_cap._PENDING_KEY_FMT,
        budget_cap._RESERVATION_KEY_FMT,
    ):
        assert "catalog:" not in fmt
        assert fmt.startswith("ai:")


def test_budget_cap_and_cost_tracker_byte_identical_to_source():
    for fname in ("budget_cap.py", "cost_tracker.py"):
        mono = (_MONO_ROOT / "ai_ops" / fname).read_text()
        svc = (_SVC_ROOT / "ai_ops" / fname).read_text()
        assert mono == svc, f"{fname} drifted from source (H3.d Lua byte-identity)"


# ─────────────────────────────────────────────────────────────────────────────
# 7. scope_to_user preserved on every product/catalog read (§10 leak rule R7)
# ─────────────────────────────────────────────────────────────────────────────
def test_scope_to_user_preserved():
    repo_src = (_SVC_ROOT / "repository.py").read_text()
    mono_src = (_MONO_ROOT / "modules" / "catalog" / "repository.py").read_text()
    # The scope_to_user anchor count is preserved EXACTLY vs the monolith twin
    # (the §10 tenant-leak invariant — every product/catalog read passes through it).
    assert repo_src.count("scope_to_user") == mono_src.count("scope_to_user")
    # find_by_id (the cross-module ownership-check backing read) filters both
    # the owner AND soft-deletes (the §10 collapse-to-None rule).
    assert "scope_to_user(select(ProductORM), user_id)" in repo_src
    assert "ProductORM.deleted_at.is_(None)" in repo_src


# ─────────────────────────────────────────────────────────────────────────────
# 8. ORM schema bindings
# ─────────────────────────────────────────────────────────────────────────────
def test_orm_schema_bindings():
    from app.shared.models import AuditEvent, Catalog, Product, ProductDraft, User

    assert Product.__table__.schema == "catalog"
    assert Catalog.__table__.schema == "catalog"
    assert ProductDraft.__table__.schema == "catalog"
    # Shared public tables.
    assert User.__table__.schema == "public"
    assert AuditEvent.__table__.schema == "public"


def test_orm_mappers_configure_clean():
    from sqlalchemy.orm import configure_mappers

    import app.shared.models  # noqa: F401 — registers all 5 models

    configure_mappers()  # raises if a relationship references an unmapped class


# ─────────────────────────────────────────────────────────────────────────────
# 9. ai_ops trim guard — only autofill_v1 prompt vendored
# ─────────────────────────────────────────────────────────────────────────────
def test_ai_ops_trim_only_autofill():
    prompts = {p.name for p in (_SVC_ROOT / "ai_ops" / "prompts").iterdir() if p.suffix == ".py"}
    assert "autofill_v1.py" in prompts
    assert "smart_picker_v1.py" not in prompts
    assert "watermark_v1.py" not in prompts


# ─────────────────────────────────────────────────────────────────────────────
# 10. dead image getattr branch verbatim + NO image_client shim (R8)
# ─────────────────────────────────────────────────────────────────────────────
def test_dead_image_branch_verbatim_and_no_image_client():
    svc_src = (_SVC_ROOT / "service.py").read_text()
    # The dead branch travels verbatim (never resolves in the svc tree, caught
    # by ``except ImportError`` — never fires; image_refs stays empty tuple).
    assert "from app.modules import image as _image_module" in svc_src
    assert 'hasattr(image_service, "get_image_refs")' in svc_src
    # NO image_client shim authored.
    assert not (_SVC_ROOT / "core" / "extracted_clients" / "image_client.py").exists()


# ─────────────────────────────────────────────────────────────────────────────
# 11. flag-parity — every settings.<X> read resolves (MS-D lesson)
# ─────────────────────────────────────────────────────────────────────────────
def test_flag_parity_every_settings_read_resolves():
    from app.shared.config import settings

    pattern = re.compile(r"settings\.([A-Z_][A-Z0-9_]*)")
    referenced: set[str] = set()
    for py in _SVC_ROOT.rglob("*.py"):
        for m in pattern.finditer(py.read_text()):
            referenced.add(m.group(1))
    # The 3 LOAD-BEARING feature flags MUST be referenced (mount guard + 2 routes
    # will read them once router.py lands) and MUST resolve now.
    for flag in (
        "FEATURE_CATALOG_FORM_ENABLED",
        "FEATURE_AI_AUTOFILL_ENABLED",
        "FEATURE_LIVE_PREVIEW_ENABLED",
    ):
        assert hasattr(settings, flag), flag
    # Every settings.<X> referenced anywhere in the vendored tree resolves.
    missing = [name for name in referenced if not hasattr(settings, name)]
    assert not missing, f"trimmed Settings is missing referenced fields: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 12. NO Celery
# ─────────────────────────────────────────────────────────────────────────────
def test_no_celery():
    assert not (_SVC_ROOT / "celery_app.py").exists()
    assert not (_SVC_ROOT / "tasks.py").exists()
    # No celery DEPENDENCY line (comments mentioning "NO celery" are fine).
    req_lines = (
        (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().splitlines()
    )
    dep_lines = [ln.strip().lower() for ln in req_lines if ln.strip() and not ln.strip().startswith("#")]
    assert not any(ln.startswith("celery") for ln in dep_lines)


# ─────────────────────────────────────────────────────────────────────────────
# 13. the 5 outbound shims round-trip (httpx.MockTransport) + forwarding
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def _mock_transport(monkeypatch):
    """Patch the extracted_clients transport's httpx.AsyncClient with a
    MockTransport that records requests + asserts JWT / X-Request-ID forwarding.
    """
    from app.core.extracted_clients import _transport

    recorded: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        path = request.url.path
        # Open-Q #1 (Option a, LEAD ruling 2026-06-14): assert_category_exists
        # probes /schema (NOT a dedicated /exists — category-svc does not serve
        # one). A /exists hit here would be a regression → 404 below.
        if path.endswith("/schema"):
            return httpx.Response(200, json={"fields": [], "super_id": "SUP1"})
        if "/field-enum/" in path:
            return httpx.Response(
                200, json={"enum_entries": [{"canonical": "Red"}], "total": 1, "truncated": False}
            )
        if path.endswith("/eligibility"):
            return httpx.Response(200, json={})
        if path.endswith("/compliance-block"):
            return httpx.Response(
                200,
                json={
                    "manufacturer_name": "Acme",
                    "manufacturer_address": "1 St",
                    "manufacturer_pincode": "560001",
                    "packer_name": "Acme",
                    "packer_address": "1 St",
                    "packer_pincode": "560001",
                    "importer_name": None,
                    "importer_address": None,
                    "importer_pincode": None,
                    "country_of_origin": "India",
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    mock = httpx.MockTransport(_handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = mock
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", _factory)
    _transport.set_request_context(bearer_token="tok-abc", request_id="rid-123")
    return recorded


@pytest.mark.asyncio
async def test_category_client_shims_roundtrip(_mock_transport):
    from app.core.extracted_clients import category_client

    cid = uuid4()
    await category_client.assert_category_exists(cid, db=None)
    schema = await category_client.fetch_schema(cid, db=None)
    assert schema["super_id"] == "SUP1"
    enum = await category_client.get_field_enum(cid, "color", db=None)
    assert enum["enum_entries"][0]["canonical"] == "Red"
    # Open-Q #1 ruling: the existence gate must hit /schema, never /exists.
    paths = [r.url.path for r in _mock_transport]
    assert any(p.endswith("/schema") for p in paths), "existence probe must use /schema"
    assert not any(p.endswith("/exists") for p in paths), (
        "Open-Q #1 regression: assert_category_exists hit /exists (category-svc "
        "does not serve it) — must probe /schema per the LEAD ruling"
    )
    # JWT + X-Request-ID forwarded on every hop; targets category-svc base URL.
    for req in _mock_transport:
        assert req.headers.get("Authorization") == "Bearer tok-abc"
        assert req.headers.get("X-Request-ID") == "rid-123"
        assert "category-svc" in req.url.host


@pytest.mark.asyncio
async def test_customer_client_shims_roundtrip(_mock_transport):
    from app.core.extracted_clients import customer_client

    uid = uuid4()
    await customer_client.assert_eligible_for_super_id(uid, "SUP1", db=None)
    block = await customer_client.get_compliance_block(uid, db=None)
    assert block.manufacturer_name == "Acme"
    assert block.country_of_origin == "India"
    assert block.importer_name is None
    # eligibility uses the ?super_id= query param; targets customer-svc base URL.
    elig = [r for r in _mock_transport if r.url.path.endswith("/eligibility")][0]
    assert elig.url.params.get("super_id") == "SUP1"
    for req in _mock_transport:
        assert "customer-svc" in req.url.host


@pytest.mark.asyncio
async def test_category_client_404_maps_to_typed_exception(monkeypatch):
    from app.core.extracted_clients import _transport, category_client

    def _handler_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "nope"})

    real = httpx.AsyncClient

    def _factory(*a, **k):
        k["transport"] = httpx.MockTransport(_handler_404)
        return real(*a, **k)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", _factory)
    with pytest.raises(category_client.CategoryNotFoundError):
        await category_client.fetch_schema(uuid4(), db=None)


@pytest.mark.asyncio
async def test_transport_retries_once_only_on_503(monkeypatch):
    from app.core.extracted_clients import _transport

    calls = {"n": 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"detail": "transient"})

    real = httpx.AsyncClient

    def _factory(*a, **k):
        k["transport"] = httpx.MockTransport(_handler)
        return real(*a, **k)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", _factory)
    _transport.set_request_context(bearer_token=None, request_id=None)
    with pytest.raises(httpx.HTTPStatusError):
        await _transport.request_json(
            "GET", "/internal/categories/x/schema", base_url="http://category-svc:8001"
        )
    # First attempt + EXACTLY ONE retry on 503 = 2 calls.
    assert calls["n"] == 2
