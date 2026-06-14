"""svc-category Phase-B services-builder invariant tests.

These lock the load-bearing extraction invariants the services-builder owns.
The FULL hybrid-mode integration suite (``test_category_extraction.py`` —
PRIMITIVE_VALUES parity against migrated rows, budget-brake 2-service round
trip, frozen shim shapes) is authored by the backend-coordinator in Phase C.

Invariants proven here:

1. ``app.main`` boots with the 6-middleware §4.H chain (7 user middleware,
   CORS outermost → Audit innermost).
2. §16.G: ``service.py`` differs from the monolith ONLY in the 3 import-line
   rewires (zero call-site changes) — proven by AST parity after recursive
   import + docstring strip.
3. The SHARED budget keyspace (``ai:*`` on DB 0) is UN-prefixed (global cap);
   category's OWN cache keys (DB 3) ARE ``category:``-prefixed.
4. The vendored ``budget_cap`` Lua scripts are byte-identical to source.
5. PRIMITIVE_VALUES / envelope cardinalities are byte-identical (11/7/9/8/2/3).
6. The 5 ORM models bind to the correct schemas (3 ``category``, 2 ``public``).

Run::

    cd backend/services/svc-category
    PYTHONPATH=. <venv>/bin/python -m pytest tests/test_svc_category_invariants.py
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

# Resolve the monolith source tree (4 levels up: tests/ → svc-category/ →
# services/ → backend/, then app/modules/category/).
_SVC_ROOT = pathlib.Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _SVC_ROOT.parents[1]
_MONO_CATEGORY = _BACKEND_ROOT / "app" / "modules" / "category"


# ── 1. main boots with the 6-mw chain ──────────────────────────────────────
def test_main_boots_with_six_mw_chain() -> None:
    import app.main as m

    names = [mw.cls.__name__ for mw in m.app.user_middleware]
    # Starlette stores users[0] = outermost (CORS) … users[-1] = innermost (Audit).
    assert names == [
        "CORSMiddleware",
        "RequestIdMiddleware",
        "AuthContextMiddleware",
        "TenancyContextMiddleware",
        "RateLimitMiddleware",
        "PlanGuardMiddleware",
        "AuditMiddleware",
    ], names


def test_health_route_present() -> None:
    import app.main as m

    paths = {r.path for r in m.app.routes if hasattr(r, "path")}
    assert "/health" in paths


# ── 2. §16.G service.py call-site preservation ─────────────────────────────
class _ImportStripper(ast.NodeTransformer):
    """Drop ALL import nodes recursively + the module docstring."""

    def visit_Import(self, node: ast.Import):  # noqa: N802
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
        return None


def _strip(tree: ast.Module) -> ast.Module:
    # Drop module docstring (first stmt if it's a bare string constant).
    body = list(tree.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    tree.body = body
    return _ImportStripper().visit(tree)


def test_service_py_call_site_parity() -> None:
    svc_src = (_SVC_ROOT / "app" / "service.py").read_text()
    mono_src = (_MONO_CATEGORY / "service.py").read_text()

    svc_dump = ast.dump(_strip(ast.parse(svc_src)))
    mono_dump = ast.dump(_strip(ast.parse(mono_src)))
    assert svc_dump == mono_dump, (
        "service.py executable body diverged from monolith beyond imports — "
        "§16.G call-site preservation VIOLATED"
    )


def test_service_py_diff_is_imports_only() -> None:
    """The literal text diff is exactly the 3 import-line rewires."""
    svc_lines = (_SVC_ROOT / "app" / "service.py").read_text().splitlines()
    mono_lines = (_MONO_CATEGORY / "service.py").read_text().splitlines()
    assert len(svc_lines) == len(mono_lines)
    diff_lines = [
        (m, s) for m, s in zip(mono_lines, svc_lines) if m != s
    ]
    # Exactly 3 changed lines, all import rewires (app.modules.category → app).
    assert len(diff_lines) == 3, diff_lines
    for mono, svc in diff_lines:
        assert "app.modules.category" in mono
        assert "app.modules.category" not in svc


def test_smart_picker_call_site_byte_identical() -> None:
    """The load-bearing call_gemini("smart_picker.v1", ...) site is unchanged."""
    svc_src = (_SVC_ROOT / "app" / "service.py").read_text()
    assert '"smart_picker.v1"' in svc_src
    assert "from app.ai_ops import client as ai_client" in svc_src


# ── 3. budget-key carve-out vs cache-key prefix ────────────────────────────
def test_budget_keys_unprefixed_global() -> None:
    import app.ai_ops.budget_cap as bc
    import app.ai_ops.cost_tracker as ct

    for fmt in (
        bc._PENDING_KEY_FMT,
        bc._RESERVATION_KEY_FMT,
        ct._DAILY_KEY_FMT,
        ct._USER_HOURLY_KEY_FMT,
    ):
        assert fmt.startswith("ai:"), fmt
        assert "category" not in fmt, f"budget key {fmt} must NOT be category-prefixed"


def test_cache_keys_category_prefixed() -> None:
    import app.core.cache as cache

    assert cache._versioned_key("schema:abc", None) == "meesell:v1:category:schema:abc"
    assert cache._versioned_key("category_tree", None) == "meesell:v1:category:category_tree"


# ── 4. vendored budget_cap Lua byte-identical ──────────────────────────────
def _lua_bodies(path: pathlib.Path) -> tuple[str, str]:
    t = path.read_text()
    reserve = re.search(r'_RESERVE_LUA = """(.*?)"""', t, re.S).group(1)
    release = re.search(r'_RELEASE_LUA = """(.*?)"""', t, re.S).group(1)
    return reserve, release


def test_budget_cap_lua_byte_identical() -> None:
    svc = _lua_bodies(_SVC_ROOT / "app" / "ai_ops" / "budget_cap.py")
    mono = _lua_bodies(_BACKEND_ROOT / "app" / "ai_ops" / "budget_cap.py")
    assert svc[0] == mono[0], "_RESERVE_LUA drifted from source"
    assert svc[1] == mono[1], "_RELEASE_LUA drifted from source"


def test_budget_cap_file_byte_identical() -> None:
    svc = (_SVC_ROOT / "app" / "ai_ops" / "budget_cap.py").read_text()
    mono = (_BACKEND_ROOT / "app" / "ai_ops" / "budget_cap.py").read_text()
    assert svc == mono


# ── 5. PRIMITIVE_VALUES / envelope cardinality parity ──────────────────────
def test_primitive_values_parity() -> None:
    from app.i18n import schema_contract as sc

    assert len(sc.PRIMITIVE_VALUES) == 11
    assert len(sc.ENVELOPE_KEYS) == 7
    assert len(sc.FIELD_SHAPE_KEYS) == 9
    assert len(sc.DATA_TYPE_VALUES) == 8
    assert len(sc.COMPLIANCE_SHAPE_VALUES) == 2
    assert len(sc.ENUM_RESOLVER_VALUES) == 3


def test_schema_contract_byte_identical() -> None:
    svc = (_SVC_ROOT / "app" / "i18n" / "schema_contract.py").read_text()
    mono = (_BACKEND_ROOT / "app" / "i18n" / "schema_contract.py").read_text()
    assert svc == mono


# ── 6. ORM schema bindings ─────────────────────────────────────────────────
def test_orm_schema_bindings() -> None:
    from app.shared.models import (
        AuditEvent,
        Category,
        FieldEnumValue,
        Template,
        User,
    )

    assert Category.__table__.schema == "category"
    assert Template.__table__.schema == "category"
    assert FieldEnumValue.__table__.schema == "category"
    assert AuditEvent.__table__.schema == "public"
    assert User.__table__.schema == "public"


def test_mappers_configure_clean() -> None:
    """No dangling Product/Catalog relationship after dropping them."""
    from sqlalchemy.orm import configure_mappers

    configure_mappers()  # raises if any relationship target is unresolved


# ── trim guard ─────────────────────────────────────────────────────────────
def test_only_smart_picker_prompt_vendored() -> None:
    prompts = _SVC_ROOT / "app" / "ai_ops" / "prompts"
    files = {p.name for p in prompts.glob("*.py")}
    assert "smart_picker_v1.py" in files
    assert "autofill_v1.py" not in files
    assert "watermark_v1.py" not in files


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
