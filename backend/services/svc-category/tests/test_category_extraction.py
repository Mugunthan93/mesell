"""Hybrid-mode integration test for the svc-category extraction (Sub-Plan F, Phase C).

LEAD-owned (meesell-backend-coordinator). Session
``mesell-microservices-category-lead-session-2`` (Phase C, round 2 — the
round-1 super-categories REJECT was fixed by api-routes-builder; this test is
the CI-enforced re-proof of the extraction's correctness, NOT a re-statement of
the four specialists' self-reports).

Posture (recipe §2/§3/§4 — anti-tautology rule)
================================================
Every assertion is NON-TAUTOLOGICAL. No ``assert True``; no string-in-repr
echoes. The categories of proof, and how category DIFFERS from the pricing
(Sub-Plan D) template:

1. **§16.G AST parity (UNCONDITIONAL).** ``service.py`` twins are parsed with
   ``ast``; the module docstring + every import (recursively, including lazy
   imports inside function bodies) are stripped, and the REMAINING executable
   AST is compared for BYTE-IDENTITY. Unlike pricing, category has ZERO outbound
   domain calls (it is a pure callee — SUB_PLAN_0F "Cross-module edges —
   category as CALLER: ZERO"), so there is NO §0.6-style allowed executable
   delta to normalise out — the executable body is byte-identical modulo imports
   and docstrings, full stop. A companion test asserts the RAW (un-stripped)
   trees DIFFER, so the import-strip is not making the parity vacuous.

2. **picker.py byte-identity (UNCONDITIONAL).** The Smart Picker ranking helpers
   travel as pure code (picker.py imports NO ai_ops — the ``call_gemini``
   invocation lives in service.py). Byte-identity preserves the golden top-5
   recall ≥80% by construction.

3. **Budget-brake SHARED carve-out (UNCONDITIONAL) — the load-bearing R1 proof.**
   The vendored ``budget_cap.py`` + ``cost_tracker.py`` build the ``ai:cost:*`` /
   ``ai:budget:*`` keys as LITERAL un-prefixed strings. category's OWN cache keys
   (``core/cache.py``) carry the ``category:`` §2.E prefix; the AI budget keyspace
   does NOT. If the budget keys were ``category:``-prefixed, the GLOBAL ₹500 cap
   would split into N per-service caps (R1, P0). This test proves: (a) the
   vendored budget key formats are byte-identical to the monolith source, and
   (b) NO ``category:`` prefix is applied to any ``ai:*`` key (the DB-0 valkey
   factory applies no prefix; the ``category:`` prefix is confined to the DB-3
   cache key builder).

4. **PRIMITIVE_VALUES / envelope zero-drift parity (UNCONDITIONAL) — LIVE FE
   guard.** The vendored ``schema_contract`` frozensets (PRIMITIVE_VALUES,
   ENVELOPE_KEYS, FIELD_SHAPE_KEYS, DATA_TYPE_VALUES, COMPLIANCE_SHAPE_VALUES,
   ENUM_RESOLVER_VALUES) are compared BY VALUE against the monolith source,
   pinned to the 11 / 7 / 9 / 8 / 2 / 3 cardinalities. The live Angular wizard
   renders off the ``primitive`` value of each field; any drift is a runtime FE
   break.

5. **The 4 FROZEN ``/internal/*`` shim shapes (UNCONDITIONAL, AST of the route
   decorators).** Each shim's ``response_model`` declaration is parsed from
   ``internal_router.py`` and asserted against the MERGED CONSUMER's
   deserialisation (the client on develop), NOT the producer's schema. The live
   response body is additionally exercised by the specialist suite
   (test_svc_category_routes.py, 45 green); this lead test pins the FROZEN
   declarations so a future re-shape fails CI regardless of test harness:
   - schema    → object envelope (export/catalog read ``dict(payload)``)
   - field-enum → object envelope (export reads ``dict(payload)``)
   - commission → object ``{"commission_pct": "<decimal-string>"}`` NEVER null
                  (pricing reads ``payload.get("commission_pct")``)
   - super-categories → **BARE JSON ARRAY** ``["26","19",...]`` (customer does
                  ``[str(x) for x in payload]`` — iterates the body DIRECTLY).
                  This is the round-1 REJECT regression guard: an object envelope
                  here would make customer iterate dict KEYS → ``["super_categories"]``
                  → runtime break of customer super-category eligibility.

6. **Flag-parity regression guard (UNCONDITIONAL) — the MS-D lesson, copied
   forward.** The mounted ``/suggest`` route guards on
   ``settings.FEATURE_SMART_PICKER_ENABLED`` (router.py:134, carried verbatim
   from the monolith). The trimmed Settings MUST define that field or every
   request 500s with an AttributeError at the guard. This pins the field exists
   and is truthy by default.
"""

from __future__ import annotations

import ast
from pathlib import Path

# ── Resolve both trees relative to this file (no hard-coded abs paths) ───────
_SVC_ROOT = Path(__file__).resolve().parents[1]  # backend/services/svc-category
_BACKEND_ROOT = _SVC_ROOT.parents[1]  # backend/
_MONOLITH_CATEGORY = _BACKEND_ROOT / "app" / "modules" / "category"
_MONOLITH_AI_OPS = _BACKEND_ROOT / "app" / "ai_ops"
_MONOLITH_I18N = _BACKEND_ROOT / "app" / "i18n"
_SVC_APP = _SVC_ROOT / "app"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — AST normalisation for the §16.G parity proof
# ─────────────────────────────────────────────────────────────────────────────
class _ImportStripper(ast.NodeTransformer):
    """Removes every import statement ANYWHERE in the tree — including lazy
    imports nested inside function bodies. The monolith category service.py may
    carry lazy imports; a top-level-only strip would leave them and the parity
    test would false-fail. The recursive NodeTransformer is mandatory
    (recipe §2 gotcha)."""

    def visit_Import(self, node: ast.Import):  # noqa: N802
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
        return None


def _drop_docstring(body: list) -> list:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _executable_body_dump(source: str) -> str:
    tree = ast.parse(source)
    tree.body = _drop_docstring(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            node.body = _drop_docstring(node.body)
    tree = _ImportStripper().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def _raw_dump(source: str) -> str:
    tree = ast.parse(source)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


# ─────────────────────────────────────────────────────────────────────────────
# 1. §16.G — service.py executable body byte-identical (NO allowed delta;
#    category is a pure callee with ZERO outbound domain calls).
# ─────────────────────────────────────────────────────────────────────────────
def test_service_py_executable_body_identical():
    """The extracted ``service.py`` executable body is byte-identical to the
    monolith twin once docstrings + imports (recursively) are stripped.

    category has NO §0.6-style executable delta — it makes ZERO outbound domain
    calls, so unlike pricing there is nothing to normalise out. Any
    executable-line drift fails here (§16.G)."""
    monolith = (_MONOLITH_CATEGORY / "service.py").read_text()
    extracted = (_SVC_APP / "service.py").read_text()
    assert _executable_body_dump(extracted) == _executable_body_dump(monolith), (
        "§16.G VIOLATION: extracted service.py executable body diverged from the "
        "monolith twin beyond import lines + docstrings. category is a pure "
        "callee — there is NO allowed executable delta. Re-run the AST classifier."
    )


def test_service_py_imports_are_a_real_delta_not_zero():
    """Sanity gate on test #1: WITHOUT the import-strip the two trees MUST
    differ (the import lines DO change ``app.modules.category`` → ``app``).
    Proves the import-strip is not making the parity vacuous."""
    monolith = (_MONOLITH_CATEGORY / "service.py").read_text()
    extracted = (_SVC_APP / "service.py").read_text()
    assert _raw_dump(extracted) != _raw_dump(monolith), (
        "Expected the RAW service.py trees to DIFFER on import lines; identical "
        "raw trees would make the import-strip parity test vacuous."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. picker.py byte-identity — golden top-5 recall preserved by construction.
# ─────────────────────────────────────────────────────────────────────────────
def test_picker_py_byte_identical():
    """picker.py travels as PURE code (no ai_ops import). Byte-identity preserves
    the Smart Picker golden top-5 recall ≥80% by construction — there is no
    ranking-logic surface to re-drift."""
    monolith = (_MONOLITH_CATEGORY / "picker.py").read_bytes()
    extracted = (_SVC_APP / "picker.py").read_bytes()
    assert extracted == monolith, (
        "picker.py is NOT byte-identical to the monolith — the Smart Picker "
        "ranking pipeline drifted; golden recall is no longer guaranteed."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Budget-brake SHARED carve-out (R1, P0) — ai:* keys global/un-prefixed.
# ─────────────────────────────────────────────────────────────────────────────
def test_budget_cap_and_cost_tracker_byte_identical():
    """The vendored budget brake (budget_cap.py + cost_tracker.py) is
    byte-identical to the monolith source — so the reserve/release Lua scripts
    and the ``ai:cost:*`` / ``ai:budget:*`` key FORMATS are identical, and the
    GLOBAL ₹500 cap arithmetic is unchanged (F3.d drift guard)."""
    for fname in ("budget_cap.py", "cost_tracker.py"):
        mono = (_MONOLITH_AI_OPS / fname).read_bytes()
        svc = (_SVC_APP / "ai_ops" / fname).read_bytes()
        assert svc == mono, (
            f"ai_ops/{fname} drifted from the monolith source — the budget-brake "
            f"key formats / Lua scripts are no longer guaranteed identical (F3.d)."
        )


def test_budget_keyspace_is_not_category_prefixed():
    """R1 CARVE-OUT (P0): the ``ai:cost:*`` / ``ai:budget:*`` keys MUST stay
    un-prefixed/global so the ₹500 cap is shared across all AI services. If they
    got the ``category:`` §2.E prefix, the cap would split into N per-service
    caps.

    Proof: (a) the vendored key formats start with the literal ``ai:`` (NOT
    ``category:ai:``); (b) the DB-0 valkey factory applies NO prefix; (c) the
    ``category:`` prefix lives ONLY in the DB-3 cache key builder."""
    cost_tracker_src = (_SVC_APP / "ai_ops" / "cost_tracker.py").read_text()
    budget_cap_src = (_SVC_APP / "ai_ops" / "budget_cap.py").read_text()
    # (a) key formats are literal ai:* — never category:ai:*
    assert '_DAILY_KEY_FMT = "ai:cost:daily:{date}"' in cost_tracker_src, (
        "the daily-cost key format drifted from the global ``ai:cost:daily`` form"
    )
    assert "category:ai:" not in cost_tracker_src and "category:ai:" not in budget_cap_src, (
        "R1 VIOLATION (P0): an ``ai:*`` budget key is ``category:``-prefixed — the "
        "GLOBAL ₹500 cap would split into per-service caps."
    )
    # (b) DB-0 valkey factory applies no prefix; (c) category: confined to DB-3 cache.
    valkey_src = (_SVC_APP / "shared" / "valkey.py").read_text()
    cache_src = (_SVC_APP / "core" / "cache.py").read_text()
    assert "category:" not in _strip_comments_and_strings(valkey_src), (
        "the DB-0 valkey factory must apply NO ``category:`` prefix (budget keys "
        "are global) — found a ``category:`` token in live code."
    )
    assert "category:" in cache_src, (
        "the ``category:`` §2.E prefix should live in the DB-3 cache key builder."
    )


def _strip_comments_and_strings(src: str) -> str:
    """Crude AST-token walk: keep only NON-string, NON-comment tokens so a
    ``category:`` mention in a docstring/comment does not false-trip the
    valkey-prefix assertion."""
    import io
    import tokenize

    out: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                continue
            out.append(tok.string)
    except tokenize.TokenError:
        return src  # fall back to raw on a tokenizer edge case
    return " ".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 4. PRIMITIVE_VALUES / envelope zero-drift parity — LIVE frontend guard.
# ─────────────────────────────────────────────────────────────────────────────
def _load_frozensets(path: Path) -> dict:
    """Parse a schema_contract module via ``ast.literal_eval`` of its frozenset
    assignments — no import needed (avoids the ``from __future__`` ForwardRef
    trap and any package-context coupling)."""
    src = path.read_text()
    tree = ast.parse(src)
    wanted = {
        "PRIMITIVE_VALUES",
        "ENVELOPE_KEYS",
        "FIELD_SHAPE_KEYS",
        "DATA_TYPE_VALUES",
        "COMPLIANCE_SHAPE_VALUES",
        "ENUM_RESOLVER_VALUES",
    }
    out: dict = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            name = node.targets[0].id
        else:
            continue
        if name in wanted and node.value is not None:
            # frozenset({...}) call → eval the inner set literal
            val = node.value
            if isinstance(val, ast.Call) and getattr(val.func, "id", "") == "frozenset":
                if val.args:
                    out[name] = set(ast.literal_eval(val.args[0]))
            elif isinstance(val, ast.Set):
                out[name] = set(ast.literal_eval(val))
    return out


def test_schema_contract_frozensets_byte_identical_and_pinned():
    """The vendored ``schema_contract`` frozensets equal the monolith source BY
    VALUE, pinned to the 11 / 7 / 9 / 8 / 2 / 3 cardinalities. The live Angular
    wizard renders off the ``primitive`` value; any drift is an FE break (R3)."""
    mono = _load_frozensets(_MONOLITH_I18N / "schema_contract.py")
    svc = _load_frozensets(_SVC_APP / "i18n" / "schema_contract.py")

    expected_card = {
        "PRIMITIVE_VALUES": 11,
        "ENVELOPE_KEYS": 7,
        "FIELD_SHAPE_KEYS": 9,
        "DATA_TYPE_VALUES": 8,
        "COMPLIANCE_SHAPE_VALUES": 2,
    }
    for name, card in expected_card.items():
        assert name in mono and name in svc, f"{name} missing from a schema_contract twin"
        assert mono[name] == svc[name], (
            f"R3 VIOLATION: {name} drifted between monolith and svc-category "
            f"(monolith={sorted(mono[name])}, svc={sorted(svc[name])})."
        )
        assert len(svc[name]) == card, (
            f"{name} cardinality changed: expected {card}, got {len(svc[name])}."
        )
    # ENUM_RESOLVER_VALUES includes None → ast.literal_eval handles it; pin to 3.
    assert "ENUM_RESOLVER_VALUES" in svc and len(svc["ENUM_RESOLVER_VALUES"]) == 3, (
        "ENUM_RESOLVER_VALUES cardinality changed: expected 3 (incl. None)."
    )
    assert mono["ENUM_RESOLVER_VALUES"] == svc["ENUM_RESOLVER_VALUES"], (
        "ENUM_RESOLVER_VALUES drifted between monolith and svc-category."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. The 4 FROZEN /internal/* shim wire shapes — pinned at the response_model
#    declaration level via AST (no app mount → no Valkey/DB coupling). The wire
#    shape is fully DETERMINED by the route decorator's ``response_model`` and
#    the handler's return coercion. We assert against the MERGED CONSUMER's
#    deserialisation contract, NOT the producer's schema. The live response-body
#    behaviour is additionally exercised by the specialist suite
#    (test_svc_category_routes.py, 45 green) — this lead test pins the FROZEN
#    declarations so a future re-shape fails CI here regardless of harness.
# ─────────────────────────────────────────────────────────────────────────────
def _internal_route_response_models() -> dict:
    """Parse internal_router.py and map each ``@_internal_router.get(path=..,
    response_model=..)`` to a short string rendering of the response_model
    expression. No import — pure AST."""
    src = (_SVC_APP / "internal_router.py").read_text()
    tree = ast.parse(src)
    out: dict = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)):
                continue
            if deco.func.attr not in ("get", "post"):
                continue
            path = deco.args[0].value if deco.args and isinstance(deco.args[0], ast.Constant) else None
            rm = None
            for kw in deco.keywords:
                if kw.arg == "response_model":
                    rm = ast.unparse(kw.value)
            if path is not None:
                out[path] = rm
    return out


def test_super_categories_shim_declares_bare_list_str():
    """ROUND-1 REJECT REGRESSION GUARD. Shim #4 ``/super-categories`` declares
    ``response_model=list[str]`` — a BARE JSON ARRAY, NOT an object envelope.

    The merged customer client (svc-customer/.../category_client.py:50-51) does
    ``return [str(item) for item in payload]`` — it iterates the body DIRECTLY.
    An object envelope ``{"super_categories":[...]}`` (the round-1 defect) would
    make customer iterate dict KEYS → ``["super_categories"]`` → runtime break of
    customer super-category eligibility. FROZEN-0E. Pins SUB_PLAN_0F §F4."""
    models = _internal_route_response_models()
    assert "/super-categories" in models, "super-categories shim route is missing"
    assert models["/super-categories"] == "list[str]", (
        f"FROZEN-0E VIOLATION: /super-categories response_model is "
        f"{models['/super-categories']!r}, expected ``list[str]`` (a BARE array). "
        f"The round-1 reject was an object envelope here."
    )
    # And the wrapper schema that caused the round-1 reject must be GONE.
    schemas_src = (_SVC_APP / "schemas.py").read_text()
    assert "SuperCategoryListResponse" not in schemas_src, (
        "SuperCategoryListResponse (the round-1 object-envelope wrapper) must be "
        "deleted — its presence is the reject-class defect."
    )


def test_commission_shim_declares_object_with_decimal_field():
    """Shim #3 ``/categories/{id}/commission`` declares
    ``response_model=CommissionResponse`` (an OBJECT) whose ``commission_pct``
    is a bare ``Decimal`` → Pydantic v2 serialises it as a JSON STRING, NEVER
    null. The merged pricing client reads ``payload.get('commission_pct')``."""
    models = _internal_route_response_models()
    commission_path = next((p for p in models if p.endswith("/commission")), None)
    assert commission_path is not None, "commission shim route is missing"
    assert models[commission_path] == "CommissionResponse", (
        f"commission shim response_model is {models[commission_path]!r}, expected "
        f"the object ``CommissionResponse`` (pricing reads payload.get('commission_pct'))."
    )
    # The model field is a bare Decimal (no json_encoders → JSON string, never null).
    schemas_src = (_SVC_APP / "schemas.py").read_text()
    schemas_tree = ast.parse(schemas_src)
    field_type = None
    for node in ast.walk(schemas_tree):
        if isinstance(node, ast.ClassDef) and node.name == "CommissionResponse":
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.AnnAssign)
                    and isinstance(stmt.target, ast.Name)
                    and stmt.target.id == "commission_pct"
                ):
                    field_type = ast.unparse(stmt.annotation)
    assert field_type == "Decimal", (
        f"CommissionResponse.commission_pct annotation is {field_type!r}, expected "
        f"a bare ``Decimal`` (never-null Decimal-string contract, FROZEN by MS-D §1)."
    )


def test_schema_and_field_enum_shims_declare_object_envelopes():
    """Shims #1 (schema) + #2 (field-enum) declare object-envelope response
    models — export/catalog read them as ``dict(payload)``. Their object shape
    is correct (verified at round 1) and unchanged by the round-2 fix; this pins
    they did not regress to a bare array."""
    models = _internal_route_response_models()
    schema_path = next((p for p in models if p.endswith("/schema")), None)
    field_enum_path = next((p for p in models if "field-enum" in p), None)
    assert schema_path and models[schema_path] == "SchemaResponse", (
        f"schema shim response_model drifted: {models.get(schema_path)!r}"
    )
    assert field_enum_path and models[field_enum_path] == "FieldEnumResponse", (
        f"field-enum shim response_model drifted: {models.get(field_enum_path)!r}"
    )


def test_exactly_four_internal_shims_mounted():
    """The internal router exposes EXACTLY the 4 frozen shims: schema,
    field-enum, commission, super-categories. No more (no leaked surface), no
    fewer (all 4 callers — export/catalog/pricing/customer — are served)."""
    models = _internal_route_response_models()
    paths = set(models)
    assert len(paths) == 4, f"expected exactly 4 internal shims, got {len(paths)}: {sorted(paths)}"
    assert any(p.endswith("/schema") for p in paths)
    assert any("field-enum" in p for p in paths)
    assert any(p.endswith("/commission") for p in paths)
    assert "/super-categories" in paths


# ─────────────────────────────────────────────────────────────────────────────
# 6. Flag-parity regression guard — the MS-D lesson, carried forward.
# ─────────────────────────────────────────────────────────────────────────────
def test_smart_picker_flag_exists_on_trimmed_settings():
    """The mounted ``/suggest`` route guards on
    ``settings.FEATURE_SMART_PICKER_ENABLED`` (router.py:134, carried verbatim
    from the monolith). The trimmed Settings MUST define it or every request
    500s with an AttributeError at the guard (the MS-D flag-parity REJECT class).
    Pins the field exists and is truthy by default."""
    from app.shared.config import settings

    assert hasattr(settings, "FEATURE_SMART_PICKER_ENABLED"), (
        "FLAG-PARITY VIOLATION: the trimmed Settings dropped "
        "FEATURE_SMART_PICKER_ENABLED, which router.py:134 reads — every "
        "/suggest request would 500 with AttributeError at the flag guard."
    )
    assert settings.FEATURE_SMART_PICKER_ENABLED is True, (
        "FEATURE_SMART_PICKER_ENABLED default must be True (matches monolith "
        "config.py:184 bool=True; staging overrides to false via env)."
    )
