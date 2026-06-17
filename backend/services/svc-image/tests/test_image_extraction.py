"""Phase-C extraction-gate tests for svc-image (MS-C image extraction).

Author: meesell-backend-coordinator (HYBRID step 3 — merge gate, Phase C).
Authority: SHIM_CONTRACT_export_callees.md §2.6 (FROZEN) · spec_msC_backend §6 ·
recipe_ms_extraction §7A (Option-B founder ruling) · BACKEND_ARCHITECTURE §16.G.

These tests assert REAL behaviour / REAL wire-shapes — NOT tautologies
(the pricing-saga lesson: never `assert True`-equivalents). Each test pins a
contract a future edit could silently break:

  1. test_mounted_routes_exact            — the app mounts EXACTLY the 3 expected
                                             routes at the EXACT frozen paths
                                             (row-26 lesson: inspect the real app,
                                             not schema existence).
  2. test_internal_shim_path_frozen       — the /internal callee shim path matches
                                             SHIM_CONTRACT §2.6 BYTE-FOR-BYTE
                                             (no /api/v1 prefix). This is the
                                             frozen contract the already-shipped
                                             svc-export image_client consumes.
  3. test_internal_shim_wire_shape        — ImagesListResponse JSON schema carries
                                             the 5 frozen §2.6 field names.
  4. test_internal_shim_no_jwt_dep        — the internal route has NO
                                             get_current_user dependency
                                             (cluster-internal trust, §2.6).
  5. test_public_routes_decorators        — public routes keep rate-limit / audit /
                                             auth posture (§11.B).
  6. test_option_b_no_products_read       — the repository issues NO products
                                             read (Option-B founder ruling: tenancy
                                             via assert_product_ownership HTTP shim,
                                             NOT a cross-schema SQL join / grant).
  7. test_service_parity_hook             — §16.G AST parity: extracted service.py
                                             is byte-identical to the monolith twin
                                             after stripping docstring + imports
                                             (the executable-line drift gate).

Run: PYTHONPATH=. python -m pytest tests/test_image_extraction.py -v
(requires the svc-image config env vars — see conftest below).
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

# ── Minimal config env so app.shared.config's §5.D startup guard passes at import
#    time. No DB / Valkey / GCS connection is made by these tests (route-table
#    introspection + AST parsing only). ────────────────────────────────────────
_TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://image_user:x@localhost:5432/meesell",
    "VALKEY_URL": "redis://localhost:6379/0",
    "JWT_SECRET": "test-secret",
    "GCS_BUCKET": "test-bucket",
    "GCS_PROJECT_ID": "test-project",
    "GEMINI_API_KEY": "test-gemini-key",
    "APP_ENV": "development",
    "AUDIT_PII_SALT": "test-salt",
    "CORS_ALLOWED_ORIGINS": "http://localhost:4200",
    "FEATURE_IMAGE_PRECHECK_ENABLED": "true",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)


# Repo paths — svc-image tree is …/backend/services/svc-image ; monolith twin is
# …/backend/app/modules/image. Resolve relative to this test file.
_SVC_ROOT = Path(__file__).resolve().parents[1]  # backend/services/svc-image
_REPO_ROOT = _SVC_ROOT.parents[2]                # repo root
_MONO_IMAGE = _REPO_ROOT / "backend" / "app" / "modules" / "image"

# Frozen contract constants (SHIM_CONTRACT §2.6 + spec_msC §0).
FROZEN_INTERNAL_PATH = "/internal/products/{product_id}/images"
PUBLIC_UPLOAD_PATH = "/api/v1/products/{id}/images"
PUBLIC_LIST_PATH = "/api/v1/products/{id}/images"
FROZEN_FIELDS = {"image_id", "idx", "status", "signed_url", "precheck_jsonb"}


def _route_table() -> list[tuple[frozenset[str], str]]:
    """Mount the real svc-image app and return (methods, path) for every
    method-bearing route. Imported lazily so the env above is set first."""
    from app.main import app  # noqa: WPS433 (deliberate lazy import)

    return [
        (frozenset(getattr(r, "methods", set()) or set()), r.path)
        for r in app.routes
        if hasattr(r, "methods")
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1 + 2. Mounted-route + frozen internal-path assertions (row-26 lesson)
# ─────────────────────────────────────────────────────────────────────────────
def test_mounted_routes_exact() -> None:
    """The assembled app mounts EXACTLY the 3 expected business routes at the
    exact frozen paths. This catches prefix-nesting drift that schema-existence
    checks miss (the row-26 lesson)."""
    table = _route_table()
    business = {
        (path, methods)
        for methods, path in table
        if path.startswith("/api/v1/products")
        or path.startswith("/internal/products")
        or "/internal/products" in path
    }
    paths = {path for _m, path in table}

    # Both public routes present at the exact frozen path.
    assert (PUBLIC_UPLOAD_PATH in paths), f"missing POST {PUBLIC_UPLOAD_PATH}; got {sorted(paths)}"
    upload = [m for m, p in table if p == PUBLIC_UPLOAD_PATH and "POST" in m]
    listr = [m for m, p in table if p == PUBLIC_LIST_PATH and "GET" in m]
    assert upload, "POST upload route not mounted"
    assert listr, "GET list route not mounted"

    # Exactly one internal shim route, and it must be at the frozen path.
    internal_paths = [p for _m, p in table if "internal" in p]
    assert len(internal_paths) == 1, f"expected exactly 1 internal route, got {internal_paths}"


def test_internal_shim_path_frozen() -> None:
    """The /internal callee shim MUST mount at the byte-for-byte frozen path
    `/internal/products/{product_id}/images` (NO /api/v1 prefix).

    The already-shipped svc-export image_client.py:73 calls
    f"/internal/products/{product_id}/images" relative to MONOLITH_INTERNAL_BASE_URL
    with NO Traefik StripPrefix on the east-west path (ingressroute.yaml: "/internal/*
    IS NOT ROUTED HERE"). A /api/v1-prefixed mount 404s at MS-2 cutover."""
    table = _route_table()
    internal = [p for _m, p in table if "internal" in p]
    assert internal == [FROZEN_INTERNAL_PATH], (
        f"FROZEN-CONTRACT VIOLATION (SHIM_CONTRACT §2.6): internal shim mounted at "
        f"{internal}, expected exactly [{FROZEN_INTERNAL_PATH!r}]. A /api/v1 prefix "
        f"means the svc-export caller 404s after MS-2 cutover."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Wire-shape parity — the 5 frozen §2.6 field names
# ─────────────────────────────────────────────────────────────────────────────
def test_internal_shim_wire_shape() -> None:
    """ImagesListResponse → images[] item carries the 5 FROZEN §2.6 field names.
    Extra fields are additive (allowed); the 5 frozen names must never be renamed."""
    from app.schemas import ImageSummary, ImagesListResponse

    schema = ImagesListResponse.model_json_schema()
    # Resolve the $ref to the item model and assert its properties.
    item_props = set(ImageSummary.model_json_schema()["properties"].keys())
    assert FROZEN_FIELDS.issubset(item_props), (
        f"frozen §2.6 fields missing/renamed: expected {FROZEN_FIELDS}, "
        f"got {item_props}"
    )
    assert "images" in schema["properties"], "ImagesListResponse must expose `images`"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Internal route has NO JWT dependency (cluster-internal trust)
# ─────────────────────────────────────────────────────────────────────────────
def test_internal_shim_no_jwt_dep() -> None:
    """The internal route must NOT depend on get_current_user (SHIM_CONTRACT §2.6
    — internal-network trust; the export worker forwards X-Request-ID only)."""
    from app.main import app

    internal_route = next(
        r for r in app.routes if hasattr(r, "path") and "internal" in r.path
    )
    dep_names = {
        getattr(d.call, "__name__", "")
        for d in internal_route.dependant.dependencies  # type: ignore[attr-defined]
    }
    # get_current_user must NOT be wired on the internal route.
    assert "get_current_user" not in dep_names, (
        f"internal shim must not require JWT; deps={dep_names}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Public-route posture (rate-limit / audit / auth)
# ─────────────────────────────────────────────────────────────────────────────
def test_public_routes_decorators() -> None:
    """Public routes preserve auth dep; the source carries the rate-limit + audit
    decorators (§11.B verbatim from monolith)."""
    from app.main import app

    upload = next(
        r for r in app.routes
        if hasattr(r, "path") and r.path == PUBLIC_UPLOAD_PATH and "POST" in r.methods
    )
    listr = next(
        r for r in app.routes
        if hasattr(r, "path") and r.path == PUBLIC_LIST_PATH and "GET" in r.methods
    )
    for route in (upload, listr):
        dep_names = {
            getattr(d.call, "__name__", "")
            for d in route.dependant.dependencies
        }
        assert "get_current_user" in dep_names, (
            f"public route {route.path} must require JWT; deps={dep_names}"
        )

    # Decorator source presence (rate_limit on both, audit_event on upload only).
    router_src = (_SVC_ROOT / "app" / "router.py").read_text()
    assert 'scope="image_upload", limit=10, window=60' in router_src
    assert 'scope="image_list", limit=600, window=3600' in router_src
    assert '@audit_event("image.upload.received")' in router_src


# ─────────────────────────────────────────────────────────────────────────────
# 6. Option-B: NO products read in the repository (founder ruling 2026-06-13)
# ─────────────────────────────────────────────────────────────────────────────
def test_option_b_no_products_read() -> None:
    """The svc-image repository must issue NO read of `products` — tenancy is
    proved by the catalog assert_product_ownership HTTP shim, not a cross-schema
    SQL join. Asserts the EXECUTABLE code (AST), not comments/docstrings, so a
    docstring mentioning the removed join does not false-pass."""
    repo_src = (_SVC_ROOT / "app" / "repository.py").read_text()
    tree = ast.parse(repo_src)

    # No import of the products ORM model.
    bad_imports = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
        and n.module is not None
        and "models.product" in n.module
        and not n.module.endswith("product_image")
    ]
    assert not bad_imports, "Option-B violation: repository imports the products ORM model"

    # No attribute access to a `ProductORM` / `Product` products model symbol,
    # and no .join() call against products in executable code.
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "ProductORM" not in names, "Option-B violation: ProductORM referenced in executable code"

    join_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "join"
    ]
    # A bare .join() on the image table to itself is not expected; any join is suspect.
    assert not join_calls, f"Option-B violation: repository issues a SQL .join() ({len(join_calls)} found)"


# ─────────────────────────────────────────────────────────────────────────────
# 7. §16.G AST parity hook — service.py byte-identical to monolith twin
# ─────────────────────────────────────────────────────────────────────────────
def _ast_norm(path: Path) -> str:
    """Strip the module docstring and ALL imports (recursively — lazy imports
    inside function bodies count), then ast.dump. Identical dump ⇒ zero
    executable-line drift (recipe §2)."""
    tree = ast.parse(path.read_text())
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(getattr(tree.body[0], "value", None), ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        tree.body = tree.body[1:]

    class _StripImports(ast.NodeTransformer):
        def visit_Import(self, node: ast.Import):  # noqa: N802
            return None

        def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
            return None

    _StripImports().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree)


@pytest.mark.skipif(
    not (_MONO_IMAGE / "service.py").exists(),
    reason="monolith image/service.py twin not present in this checkout",
)
def test_service_parity_hook() -> None:
    """§16.G: extracted service.py is byte-identical to the monolith twin after
    stripping docstring + imports. The ONLY allowed delta is the catalog import
    line (stripped here), so the executable bodies must match exactly."""
    svc = _ast_norm(_SVC_ROOT / "app" / "service.py")
    mono = _ast_norm(_MONO_IMAGE / "service.py")
    assert svc == mono, (
        "§16.G parity FAIL: svc-image service.py executable AST differs from the "
        "monolith twin (more than the import line changed)."
    )


@pytest.mark.skipif(
    not (_MONO_IMAGE / "tasks.py").exists(),
    reason="monolith image/tasks.py twin not present in this checkout",
)
def test_tasks_parity_hook() -> None:
    """§16.G: extracted tasks.py is byte-identical to the monolith twin (the
    watermark.v1 ai_ops call + cross-schema audit INSERT must be preserved)."""
    svc = _ast_norm(_SVC_ROOT / "app" / "tasks.py")
    mono = _ast_norm(_MONO_IMAGE / "tasks.py")
    assert svc == mono, "§16.G parity FAIL: svc-image tasks.py executable AST differs from monolith twin."
