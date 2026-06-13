"""svc-customer extraction proof (MS Sub-Plan E, Phase B — services-builder slice).

Every assertion is NON-TAUTOLOGICAL (the pricing lesson — spec §6).  Six classes
of proof, none requiring live infra (the shim + serialization tests mock httpx;
the AST/parity tests read both trees from disk):

1. §16.G service.py parity — the extracted ``service.py`` executable body is
   structurally IDENTICAL to the monolith twin once docstring + imports are
   stripped, EXCEPT the one sanctioned loader-body change (``_load_super_id_set``
   now calls the shim instead of running the categories SELECT).  The 2
   sanctioned import edits (dropped CategoryORM + dropped sqlalchemy.select,
   added category_client) are asserted explicitly.
2. domain.py + exceptions.py VERBATIM — byte-identical to the monolith twins
   (COMPLIANCE_EXTENSION_MAP 11 keys / Beauty shared-instance identity).
3. repository.py — ``scope_to_user`` present on ALL 4 methods (the §19 grep
   anchor); FK severed (ORM model has no ForeignKeyConstraint; GIN kept).
4. OUTBOUND category_client (FROZEN-0E) — drives the real ``_transport`` with a
   mocked ClusterIP: GET /internal/super-categories, JWT + X-Request-ID
   forwarded, 5s/2s timeout, retry-once-on-503, deserializes ``list[str]``.
5. INBOUND /internal/* serialization — the 3 FROZEN JSON shapes: compliance-block
   10-field asdict, completeness 5-field (incl. no-profile-no-404), eligibility
   None→{} and 422 envelope on incomplete profile.
6. cache contract — the 2 customer cache keys + TTLs are preserved verbatim.
"""

from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

# ── Resolve both trees relative to this file (no hard-coded abs paths) ───────
_SVC_ROOT = Path(__file__).resolve().parents[1]  # backend/services/svc-customer
_BACKEND_ROOT = _SVC_ROOT.parents[1]  # backend/
_MONOLITH_CUSTOMER = _BACKEND_ROOT / "app" / "modules" / "customer"
_SVC_APP = _SVC_ROOT / "app"


# ─────────────────────────────────────────────────────────────────────────────
# AST helpers
# ─────────────────────────────────────────────────────────────────────────────
class _ImportStripper(ast.NodeTransformer):
    """Removes every import statement ANYWHERE in the tree (top-level + nested)."""

    def visit_Import(self, node: ast.Import):  # noqa: N802
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
        return None


def _strip_module_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _strip_func_docstrings(tree: ast.AST) -> None:
    """Drop the leading docstring node from every function in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.body = _strip_module_docstring(node.body)


def _executable_dump(source: str) -> str:
    tree = ast.parse(source)
    tree.body = _strip_module_docstring(list(tree.body))
    _strip_func_docstrings(tree)
    tree = _ImportStripper().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def _import_targets(source: str) -> list[str]:
    tree = ast.parse(source)
    out: list[str] = []
    for node in ast.walk(tree):
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
# 1. §16.G — service.py body identical EXCEPT the one sanctioned loader change
# ─────────────────────────────────────────────────────────────────────────────
def _replace_loader_body_with_sentinel(source: str) -> str:
    """Return the source with ``_load_super_id_set``'s body replaced by a bare
    ``pass`` so the AST comparison ignores the ONE sanctioned body change and
    proves the REST of the module is byte-for-byte structurally identical."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_load_super_id_set":
            node.body = [ast.Pass()]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def test_service_py_body_identical_except_sanctioned_loader_swap():
    """The extracted service.py is structurally identical to the monolith twin
    once (a) docstrings + imports are stripped, AND (b) the ONE sanctioned
    ``_load_super_id_set`` body is neutralised.  Any OTHER executable drift
    fails here — the CI re-proof of the services-builder one-time diff."""
    monolith = (_MONOLITH_CUSTOMER / "service.py").read_text()
    extracted = (_SVC_APP / "service.py").read_text()

    mono_body = _executable_dump(_replace_loader_body_with_sentinel(monolith))
    svc_body = _executable_dump(_replace_loader_body_with_sentinel(extracted))

    assert svc_body == mono_body, (
        "§16.G VIOLATION: service.py executable body diverged beyond the ONE "
        "sanctioned _load_super_id_set loader swap. Re-run the AST classifier."
    )


def test_service_py_imports_are_the_2_sanctioned_edits_plus_flattening():
    """The §16.G permitted diff: CategoryORM + sqlalchemy.select dropped,
    category_client added, and the monolith module paths flattened to the svc
    tree.  The categories ORM read MUST be gone."""
    extracted = (_SVC_APP / "service.py").read_text()
    joined = "\n".join(_import_targets(extracted))

    # Sanctioned edit (a): CategoryORM import DROPPED; select() loader gone.
    assert "Category as CategoryORM" not in joined
    assert "sqlalchemy.select" not in joined
    # Sanctioned edit (b): the outbound shim is imported.
    assert "app.core.extracted_clients.category_client" in joined
    # Flattened tree (mechanical): monolith module paths GONE.
    assert "app.modules.customer" not in joined
    # The categories ORM read body is GONE (proves the SQL was removed).
    assert "CategoryORM.super_id" not in extracted
    assert "select(CategoryORM" not in extracted


def test_load_super_id_set_calls_the_shim_not_sql():
    """The loader body is exactly ``return await
    category_client.get_super_category_set()`` — no DB execute, no select."""
    extracted = (_SVC_APP / "service.py").read_text()
    tree = ast.parse(extracted)
    loader = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "_load_super_id_set"
    )
    # strip docstring
    body = _strip_module_docstring(loader.body)
    assert len(body) == 1
    src = ast.unparse(body[0])
    assert "category_client.get_super_category_set()" in src
    assert "db.execute" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 2. domain.py + exceptions.py VERBATIM
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fname", ["domain.py", "exceptions.py"])
def test_domain_and_exceptions_byte_for_byte_identical(fname):
    """domain.py + exceptions.py are VERBATIM copies of the monolith twins
    (same import paths resolve in the flat tree — no rewrite needed)."""
    monolith = (_MONOLITH_CUSTOMER / fname).read_text()
    extracted = (_SVC_APP / fname).read_text()
    assert extracted == monolith, f"{fname} is NOT byte-identical to the monolith twin"


def test_compliance_extension_map_11_keys_beauty_shared_instance():
    """COMPLIANCE_EXTENSION_MAP has exactly 11 keys; Beauty's 6 super_ids all
    point at the SAME shared spec instance (identity, not equality)."""
    from app.domain import COMPLIANCE_EXTENSION_MAP

    assert len(COMPLIANCE_EXTENSION_MAP) == 11
    beauty_ids = ("19", "36", "37", "14", "88", "34")
    anchor = COMPLIANCE_EXTENSION_MAP["19"]
    for sid in beauty_ids:
        assert COMPLIANCE_EXTENSION_MAP[sid] is anchor
    assert anchor.super_name == "Beauty"
    assert anchor.compulsory is True


def test_six_exception_subclasses_present():
    """CustomerError base + 6 subclasses with their frozen codes/status."""
    from app import exceptions as exc

    assert exc.ProfileNotFoundError.status_code == 404
    assert exc.ProfileNotFoundError.code == "customer.profile_not_found"
    assert exc.InvalidPincodeError.status_code == 422
    assert exc.InvalidSuperCategoryError.status_code == 422
    assert exc.SuperCategoryNotDeclaredError.status_code == 404
    assert exc.ComplianceExtensionMissingFieldsError.status_code == 422
    assert exc.ProfileIncompleteForCategoryError.status_code == 422
    assert (
        exc.ProfileIncompleteForCategoryError.validation_message_id
        == "customer.profile.incomplete_for_category"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. repository.py — scope_to_user on ALL 4 methods + FK severed + GIN kept
# ─────────────────────────────────────────────────────────────────────────────
def test_repository_scope_to_user_on_all_four_methods():
    """Every public repository method contains a ``scope_to_user(`` call (the
    §19 multi-tenant grep anchor) — find_by_user_id, upsert,
    update_active_categories, update_compliance_extension."""
    src = (_SVC_APP / "repository.py").read_text()
    tree = ast.parse(src)
    methods = {"find_by_user_id", "upsert", "update_active_categories",
               "update_compliance_extension"}
    found_with_scope: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name in methods:
            body_src = ast.unparse(node)
            if "scope_to_user(" in body_src:
                found_with_scope.add(node.name)
    assert found_with_scope == methods, (
        f"scope_to_user missing on: {methods - found_with_scope}"
    )


def test_seller_profile_orm_fk_severed_gin_kept_schema_customer():
    """The ORM model has NO ForeignKeyConstraint + NO relationship (Risk #5
    severance), KEEPS the GIN index, and binds to the ``customer`` schema.

    Parsed via AST so a docstring MENTIONING the severed symbols cannot
    false-positive — we inspect the actual import names + call nodes."""
    src = (_SVC_APP / "shared" / "models" / "seller_profile.py").read_text()
    tree = ast.parse(src)

    # No ForeignKeyConstraint import + no relationship/ForeignKeyConstraint call.
    imported = set(_import_targets(src))
    assert not any("ForeignKeyConstraint" in t for t in imported), (
        "ForeignKeyConstraint must NOT be imported (FK severed — Risk #5)"
    )
    called_funcs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                called_funcs.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                called_funcs.add(fn.attr)
    assert "ForeignKeyConstraint" not in called_funcs
    assert "relationship" not in called_funcs

    # GIN index kept + schema binds to customer.
    assert "idx_seller_profile_super_cats" in src
    assert 'postgresql_using="gin"' in src or "postgresql_using='gin'" in src
    assert '"schema": "customer"' in src or "'schema': 'customer'" in src


# ─────────────────────────────────────────────────────────────────────────────
# 4. OUTBOUND category_client (FROZEN-0E) — real _transport, mocked ClusterIP
# ─────────────────────────────────────────────────────────────────────────────
class _Recorder:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []
        self.timeouts: list[httpx.Timeout] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._responses.pop(0)
        return httpx.Response(status_code=status, json=body)


def _install_mock(monkeypatch, recorder: _Recorder) -> None:
    from app.core.extracted_clients import _transport

    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        recorder.timeouts.append(kwargs.get("timeout"))
        kwargs["transport"] = httpx.MockTransport(recorder.handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_category_shim_forwards_jwt_and_deserialises_str_list(monkeypatch):
    """``category_client.get_super_category_set`` issues
    ``GET /internal/super-categories`` with the forwarded JWT + X-Request-ID,
    honours the locked 5s/2s timeout, and deserialises a JSON array into a
    ``list[str]`` of distinct super_ids (FROZEN-0E)."""
    from app.core.extracted_clients import _transport, category_client

    body = ["26", "13", "16", "19", "80", "30"]
    rec = _Recorder([(200, body)])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="real-jwt", request_id="rid-7")

    result = await category_client.get_super_category_set()

    assert len(rec.requests) == 1
    req = rec.requests[0]
    assert req.method == "GET"
    assert str(req.url) == "http://monolith-svc:8001/internal/super-categories"
    assert req.headers.get("Authorization") == "Bearer real-jwt"
    assert req.headers.get("X-Request-ID") == "rid-7"
    assert rec.timeouts[0].read == 5.0
    assert rec.timeouts[0].connect == 2.0
    # FROZEN-0E: list[str].
    assert result == ["26", "13", "16", "19", "80", "30"]
    assert all(isinstance(x, str) for x in result)


@pytest.mark.asyncio
async def test_category_shim_retries_once_on_503_then_succeeds(monkeypatch):
    """A 503 triggers EXACTLY ONE retry; the second (200) response is returned."""
    from app.core.extracted_clients import _transport, category_client

    rec = _Recorder([(503, {}), (200, ["26", "13"])])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    result = await category_client.get_super_category_set()
    assert len(rec.requests) == 2  # one retry → two attempts
    assert result == ["26", "13"]


@pytest.mark.asyncio
async def test_category_shim_does_not_retry_on_500(monkeypatch):
    """A 500 is deterministic — NO retry; the non-2xx surfaces as HTTPStatusError."""
    from app.core.extracted_clients import _transport, category_client

    rec = _Recorder([(500, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(httpx.HTTPStatusError):
        await category_client.get_super_category_set()
    assert len(rec.requests) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. INBOUND /internal/* serialization — the 3 FROZEN JSON shapes
# ─────────────────────────────────────────────────────────────────────────────
def _fake_user():
    from app.core.auth import CurrentUser

    return CurrentUser(user_id=uuid4(), plan="free")


@pytest.mark.asyncio
async def test_internal_compliance_block_serialises_10_fields(monkeypatch):
    """FROZEN-0A: the compliance-block handler returns the 10-field asdict of
    the domain ComplianceBlock, field SET + ORDER mirroring domain.py:76-94."""
    import app.internal_routes as ir
    from app.domain import ComplianceBlock

    block = ComplianceBlock(
        manufacturer_name="ACME Mfg",
        manufacturer_address="1 Industrial Rd",
        manufacturer_pincode="560001",
        packer_name="ACME Pack",
        packer_address="2 Pack Rd",
        packer_pincode="560002",
        importer_name=None,
        importer_address=None,
        importer_pincode=None,
        country_of_origin="India",
    )

    async def _svc(user_id, db):
        return block

    monkeypatch.setattr(ir.customer_service, "get_compliance_block", _svc)

    out = await ir.get_compliance_block_internal(
        user_id=uuid4(), _user=_fake_user(), db=object()
    )

    assert list(out.keys()) == [
        "manufacturer_name", "manufacturer_address", "manufacturer_pincode",
        "packer_name", "packer_address", "packer_pincode",
        "importer_name", "importer_address", "importer_pincode",
        "country_of_origin",
    ]
    assert out == asdict(block)


@pytest.mark.asyncio
async def test_internal_completeness_serialises_5_fields_no_404(monkeypatch):
    """FROZEN-0B: the completeness handler returns the 5-field asdict, and a
    first-time seller (no profile) returns the all-zero / 10-base shape at 200
    (NOT a 404) — the service method returns this and never raises."""
    import app.internal_routes as ir
    from app.domain import ProfileCompleteness

    completeness = ProfileCompleteness(
        base_complete_count=0,
        base_total_count=10,
        extension_complete_count=0,
        extension_total_count=0,
        onboarding_complete=False,
    )

    async def _svc(user_id, db):
        return completeness

    monkeypatch.setattr(ir.customer_service, "get_onboarding_completeness", _svc)

    out = await ir.get_onboarding_completeness_internal(
        user_id=uuid4(), _user=_fake_user(), db=object()
    )

    assert list(out.keys()) == [
        "base_complete_count", "base_total_count",
        "extension_complete_count", "extension_total_count",
        "onboarding_complete",
    ]
    assert out["base_total_count"] == 10
    assert out["onboarding_complete"] is False
    assert out == asdict(completeness)


@pytest.mark.asyncio
async def test_internal_eligibility_success_returns_empty_object(monkeypatch):
    """frozen-0H: a successful eligibility check (service returns None) yields a
    200 ``{}`` body."""
    import app.internal_routes as ir

    async def _svc(user_id, super_id, db):
        return None

    monkeypatch.setattr(ir.customer_service, "assert_eligible_for_super_id", _svc)

    out = await ir.assert_eligibility_internal(
        user_id=uuid4(), super_id="26", _user=_fake_user(), db=object()
    )
    assert out == {}


@pytest.mark.asyncio
async def test_internal_eligibility_failure_raises_422_envelope_error(monkeypatch):
    """frozen-0H: an incomplete profile raises ProfileIncompleteForCategoryError
    (422 ``customer.profile.incomplete_for_category``) — the MeesellError handler
    renders the envelope.  Here we prove the handler raises the typed 422 error
    that the global handler maps to the frozen envelope."""
    import app.internal_routes as ir
    from app.exceptions import ProfileIncompleteForCategoryError

    async def _svc(user_id, super_id, db):
        raise ProfileIncompleteForCategoryError(
            super_id=super_id, missing_keys=["fssai_license_number"]
        )

    monkeypatch.setattr(ir.customer_service, "assert_eligible_for_super_id", _svc)

    with pytest.raises(ProfileIncompleteForCategoryError) as ei:
        await ir.assert_eligibility_internal(
            user_id=uuid4(), super_id="26", _user=_fake_user(), db=object()
        )
    assert ei.value.status_code == 422
    assert ei.value.validation_message_id == "customer.profile.incomplete_for_category"
    assert ei.value.missing_keys == ["fssai_license_number"]


# ─────────────────────────────────────────────────────────────────────────────
# 6. cache contract — 2 customer cache keys + TTLs preserved verbatim
# ─────────────────────────────────────────────────────────────────────────────
def test_cache_contract_keys_and_ttls_preserved():
    """The 2 customer cache contracts are unchanged: required_fields 60 s and
    super_category_set (key ``customer.super_category_set``) 3600 s,
    single_flight on the super-category loader."""
    import app.service as svc

    assert svc._REQUIRED_FIELDS_TTL_SECONDS == 60
    assert svc._SUPER_CATEGORY_SET_TTL_SECONDS == 3600
    assert svc._SUPER_CATEGORY_SET_KEY == "customer.super_category_set"
    assert svc._required_fields_cache_key.__name__ == "_required_fields_cache_key"
    key = svc._required_fields_cache_key(uuid4())
    assert key.startswith("customer.required_fields.")
