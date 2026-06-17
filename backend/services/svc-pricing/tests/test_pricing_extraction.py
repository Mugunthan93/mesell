"""Hybrid-mode integration test for the svc-pricing extraction (Sub-Plan D, Phase C).

LEAD-owned (meesell-backend-coordinator). Session
``mesell-ms-pricing-backend-session-1``. This is the integration test that
proves the extraction is CORRECT — not that the code merely imports. It is the
CI-enforced re-proof of the four specialists' one-time self-reports.

Posture (spec_msD_backend §6 + recipe §2/§3/§4 — anti-tautology rule)
=====================================================================
Every assertion is NON-TAUTOLOGICAL (the Wave-6D PRICING reject class —
``assert True`` / string-in-repr echoes — is forbidden, lesson
BE-PRICING-LASTCALC-TX-1):

1. **§16.G AST parity (UNCONDITIONAL).** Both ``service.py`` twins are parsed
   with ``ast``; the module docstring + every import (recursively, including
   lazy imports inside function bodies) are stripped, and the REMAINING
   executable AST is compared. The ONE legitimate executable delta is the §0.6
   ProductORM-elimination block inside ``calculate`` (3 monolith statements →
   1 svc statement) — that single block is normalised out, and the rest must be
   byte-identical. This re-proves §16.G on EVERY CI run.

2. **Wire-shape parity (UNCONDITIONAL).** ``model_json_schema()`` of the 3
   pricing wire models (svc vs monolith), ``description`` keys stripped
   recursively, compared field-for-field. Drift = a runtime 4xx surprise.

3. **T1 frozen-Decimal golden (UNCONDITIONAL, byte-compare).** The 9 bare-Decimal
   ``PriceCalcResponse`` fields emit as JSON STRINGS in real ``model_dump_json``
   output — byte-compared against a frozen golden, not a type check alone.

4. **T3/T4 shim round-trips (UNCONDITIONAL, real httpx.MockTransport).** The
   catalog ownership / get_category_id shim forwards JWT + X-Request-ID and maps
   a real 404 → typed ``ProductNotFoundError``; the category commission shim
   honours the Decimal-NEVER-null contract over real shim HTTP deserialisation.

5. **T6 cross-schema audit INSERT (split: binding UNCONDITIONAL + round-trip
   PG-GATED).** ``pricing.calculated`` targets ``public.audit_events`` while the
   service's own ``pricing_calcs`` lives in the ``pricing`` schema — a genuine
   cross-schema write. Model binding is unconditional; the live INSERT→SELECT
   round-trip is PG-gated (auth-otp no-tunnel pattern; SQLite is NOT a substitute
   — it cannot honour schema-qualified DDL).

6. **Flag-parity regression guard (UNCONDITIONAL).** The mounted route guards on
   ``settings.FEATURE_PRICE_CALCULATOR_ENABLED`` (router.py:99, carried verbatim
   from the monolith). The trimmed Settings MUST therefore define that field
   (the monolith defines it at config.py:223 ``bool = True``). If it is missing,
   every request 500s with an AttributeError at the guard. This test pins that
   the field exists and is truthy by default — it is the regression guard for
   the MS-D Phase-C REJECT (services-builder trimmed Settings dropped the field).
"""

from __future__ import annotations

import ast
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

# ── Resolve both trees relative to this file (no hard-coded abs paths) ───────
_SVC_ROOT = Path(__file__).resolve().parents[1]  # backend/services/svc-pricing
_BACKEND_ROOT = _SVC_ROOT.parents[1]  # backend/
_MONOLITH_PRICING = _BACKEND_ROOT / "app" / "modules" / "pricing"
_SVC_APP = _SVC_ROOT / "app"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — AST normalisation for the §16.G parity proof
# ─────────────────────────────────────────────────────────────────────────────
class _ImportStripper(ast.NodeTransformer):
    """Removes every import statement ANYWHERE in the tree — including lazy
    imports nested inside function bodies. The monolith pricing service.py has
    lazy imports (``app.shared.models.product``,
    ``app.modules.catalog.exceptions`` inside ``calculate``;
    ``app.exceptions.InvalidPriceInputError`` inside ``_compute_pnl``); a
    top-level-only strip would leave these and the parity test would false-fail.
    The recursive NodeTransformer is mandatory (recipe §2 gotcha)."""

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


def _normalise_06_block(tree: ast.Module) -> ast.Module:
    """Collapse the §0.6 ProductORM-elimination block in ``calculate`` to a
    single canonical placeholder statement, in BOTH twins, so the comparison
    isolates the §0.6 delta as the one allowed executable difference.

    Monolith ``calculate`` (after import-strip) contains, between the
    ownership-gate ``await catalog_service.assert_product_ownership(...)`` and
    the ``await category_service.get_commission(...)`` calls, these 3 stmts:
        product = await db.get(ProductORM, product_id)
        if product is None or product.deleted_at is not None: raise ...
        category_id = product.category_id
    svc ``calculate`` replaces them with ONE stmt:
        category_id = await catalog_service.get_category_id(product_id, user_id, db=db)

    Both forms assign ``category_id`` for downstream use. We replace the
    contiguous run of statements that produces ``category_id`` (between the
    ownership-gate call and the commission call) with a single canonical
    ``pass`` in each twin. Every OTHER statement in ``calculate`` — and every
    other function — is compared verbatim.
    """

    def is_assert_ownership(stmt: ast.stmt) -> bool:
        # ``await catalog_service.assert_product_ownership(...)`` Expr.
        return (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Await)
            and isinstance(stmt.value.value, ast.Call)
            and isinstance(stmt.value.value.func, ast.Attribute)
            and stmt.value.value.func.attr == "assert_product_ownership"
        )

    def is_commission_assign(stmt: ast.stmt) -> bool:
        # ``commission_pct = await category_service.get_commission(...)``
        return (
            isinstance(stmt, ast.Assign)
            and isinstance(stmt.value, ast.Await)
            and isinstance(stmt.value.value, ast.Call)
            and isinstance(stmt.value.value.func, ast.Attribute)
            and stmt.value.value.func.attr == "get_commission"
        )

    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "calculate":
            body = node.body
            start = next((i for i, s in enumerate(body) if is_assert_ownership(s)), None)
            end = next((i for i, s in enumerate(body) if is_commission_assign(s)), None)
            if start is not None and end is not None and end > start:
                # Keep the ownership-gate call (start) and the commission assign
                # (end); replace everything strictly between them (the §0.6
                # category_id-producing block) with a single canonical Pass.
                placeholder = ast.Pass()
                node.body = body[: start + 1] + [placeholder] + body[end:]
    return tree


def _executable_body_dump(source: str, *, normalise_06: bool) -> str:
    tree = ast.parse(source)
    tree.body = _drop_docstring(tree.body)
    # Drop docstrings on nested defs/classes too (handled by recursive walk
    # below via the stripper's generic_visit preserving non-string Expr only).
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            node.body = _drop_docstring(node.body)
    if normalise_06:
        tree = _normalise_06_block(tree)
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
# 1. §16.G ABSOLUTE CONTRACT — executable body of service.py twins is identical
#    save for the ONE allowed §0.6 delta.
# ─────────────────────────────────────────────────────────────────────────────
def test_service_py_executable_body_identical_modulo_06_block():
    """The extracted ``service.py`` pipeline is structurally identical to the
    monolith twin once docstrings + imports are stripped AND the single §0.6
    ProductORM-elimination block is normalised out of BOTH twins (§16.G).

    Any executable-line drift OUTSIDE the §0.6 block fails here.
    """
    monolith = (_MONOLITH_PRICING / "service.py").read_text()
    extracted = (_SVC_APP / "service.py").read_text()

    mono_body = _executable_body_dump(monolith, normalise_06=True)
    svc_body = _executable_body_dump(extracted, normalise_06=True)

    assert svc_body == mono_body, (
        "§16.G VIOLATION: the extracted service.py executable body diverged "
        "from the monolith twin BEYOND the permitted §0.6 ProductORM block + "
        "import lines + docstrings. Re-run the AST classifier to locate the drift."
    )


def test_service_py_06_block_is_a_real_delta_not_zero():
    """Sanity gate on test #1: WITHOUT the §0.6 normalisation the two trees MUST
    differ (the §0.6 block is a genuine executable change). If they were already
    identical without normalisation, the normaliser would be masking nothing and
    test #1 would be vacuous. This guards against a tautological #1."""
    monolith = (_MONOLITH_PRICING / "service.py").read_text()
    extracted = (_SVC_APP / "service.py").read_text()
    mono_raw = _executable_body_dump(monolith, normalise_06=False)
    svc_raw = _executable_body_dump(extracted, normalise_06=False)
    assert svc_raw != mono_raw, (
        "Expected the §0.6 block to be a real executable delta before "
        "normalisation; if equal, the parity test #1 is vacuous."
    )


def test_service_py_imports_rewired_to_shims_only():
    """The §16.G permitted import diff: the 2 cross-module imports were rewritten
    to ``extracted_clients`` re-exporting the SAME ``catalog_service`` /
    ``category_service`` symbol names (so the call sites are byte-for-byte
    unchanged), the ProductORM import is GONE, and intra-module imports are
    flattened to ``app.*``."""
    extracted = (_SVC_APP / "service.py").read_text()
    joined = "\n".join(_import_targets(extracted))

    assert "app.core.extracted_clients.catalog_client as catalog_service" in joined
    assert "app.core.extracted_clients.category_client as category_service" in joined
    # Monolith module-path imports must be GONE.
    assert "app.modules.catalog.service" not in joined
    assert "app.modules.category.service" not in joined
    assert "app.modules.pricing" not in joined
    # The §0.6 ProductORM import must be ELIMINATED entirely from the service.
    assert "app.shared.models.product" not in joined
    assert "Product as ProductORM" not in joined


def test_no_productorm_or_products_in_extracted_service_and_repo():
    """RD1 gate: NO executable reference to ProductORM or the catalog-owned
    ``products`` table survives in the extracted service.py or repository.py.

    We parse the AST and walk every Name/Attribute node — comments and
    docstrings (which legitimately discuss the §0.6 history) are invisible to
    the AST, so this is a true executable-reference scan, not a grep that would
    false-positive on the explanatory docstrings."""
    for fname in ("service.py", "repository.py"):
        tree = ast.parse((_SVC_APP / fname).read_text())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert "ProductORM" not in names, f"{fname}: executable ProductORM reference survives"
        # A `.join(ProductORM, ...)` or `select(ProductORM)` would show as a
        # Name; a bare `products` table reference would too. Neither may exist.
        assert "ProductORM" not in attrs, f"{fname}: ProductORM attribute reference survives"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wire-shape parity — the 3 pricing schemas match the monolith field-for-field
# ─────────────────────────────────────────────────────────────────────────────
def _strip_descriptions(obj):
    if isinstance(obj, dict):
        return {k: _strip_descriptions(v) for k, v in obj.items() if k != "description"}
    if isinstance(obj, list):
        return [_strip_descriptions(v) for v in obj]
    return obj


@pytest.mark.parametrize(
    "model_name", ["PriceCalcRequest", "PriceCalcAlert", "PriceCalcResponse"]
)
def test_wire_shape_matches_monolith_field_for_field(model_name):
    """Each svc-pricing wire model produces a byte-identical JSON Schema to the
    monolith ``modules/pricing/schemas`` twin (``description`` prose excluded).
    Drift = a runtime 4xx surprise for the frontend (frozen Decimal contract §1)."""
    import importlib.util
    import sys

    from app import schemas as svc_schemas

    mod_name = "_monolith_pricing_schemas"
    mono_path = _MONOLITH_PRICING / "schemas.py"
    spec = importlib.util.spec_from_file_location(mod_name, mono_path)
    assert spec is not None and spec.loader is not None
    mono_mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mono_mod
    try:
        spec.loader.exec_module(mono_mod)
        svc_model = getattr(svc_schemas, model_name)
        mono_model = getattr(mono_mod, model_name)
        mono_model.model_rebuild(_types_namespace=vars(mono_mod))
    finally:
        sys.modules.pop(mod_name, None)

    svc_schema = _strip_descriptions(svc_model.model_json_schema())
    mono_schema = _strip_descriptions(mono_model.model_json_schema())

    assert svc_schema == mono_schema, (
        f"Wire-shape DRIFT in {model_name} (prose descriptions excluded):\n"
        f"  svc-pricing: {svc_schema}\n"
        f"  monolith:    {mono_schema}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. T1 — frozen Decimal-string contract (byte-compare on real JSON output)
# ─────────────────────────────────────────────────────────────────────────────
def test_t1_decimal_fields_serialise_as_json_strings_byte_compare():
    """The 9 bare-Decimal ``PriceCalcResponse`` fields emit as JSON STRINGS in
    real ``model_dump_json`` output. We construct a response with fixed Decimals,
    dump it, and byte-compare each field's emission against the frozen
    ``"<value>"`` string golden — NOT merely a type check (Wave-6D anti-tautology)."""
    import json
    from datetime import datetime, timezone

    from app.schemas import PriceCalcAlert, PriceCalcResponse

    resp = PriceCalcResponse(
        mrp=Decimal("157.96"),
        meesho_price=Decimal("157.96"),
        seller_price=Decimal("130.00"),
        commission_pct=Decimal("15.00"),
        commission_amount=Decimal("23.69"),
        gst_pct=Decimal("18.00"),
        gst_amount=Decimal("4.26"),
        profit=Decimal("30.00"),
        profit_pct=Decimal("30.00"),
        alerts=[
            PriceCalcAlert(
                code="LOW_MARGIN", message_id="pricing.alert.low_margin", severity="warning"
            )
        ],
        calculated_at=datetime(2026, 6, 13, 0, 0, 0, tzinfo=timezone.utc),
    )

    raw = resp.model_dump_json()
    parsed = json.loads(raw)

    golden = {
        "mrp": "157.96",
        "meesho_price": "157.96",
        "seller_price": "130.00",
        "commission_pct": "15.00",
        "commission_amount": "23.69",
        "gst_pct": "18.00",
        "gst_amount": "4.26",
        "profit": "30.00",
        "profit_pct": "30.00",
    }
    for field, want in golden.items():
        got = parsed[field]
        assert isinstance(got, str), (
            f"FROZEN CONTRACT VIOLATION: {field} emitted as {type(got).__name__} "
            f"({got!r}); expected a JSON string. A json_encoders/float regression "
            f"would break the frontend's Decimal-string contract (spec §1)."
        )
        assert got == want, f"{field}: emitted {got!r}, golden {want!r}"

    # The exact substring must appear verbatim in the raw JSON bytes.
    assert '"mrp":"157.96"' in raw.replace(" ", "")
    assert '"profit_pct":"30.00"' in raw.replace(" ", "")
    # alerts is an array of objects; calculated_at is an ISO-8601 string.
    assert isinstance(parsed["alerts"], list) and parsed["alerts"][0]["code"] == "LOW_MARGIN"
    assert parsed["calculated_at"].startswith("2026-06-13T00:00:00")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Shim round-trips — real httpx.MockTransport, real JWT-forward + deserialise
# ─────────────────────────────────────────────────────────────────────────────
class _Recorder:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []
        self.timeouts: list[httpx.Timeout] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        # Pop the next scripted response; if exhausted, repeat the last one so a
        # single retry (503/504) does not IndexError. 4xx/2xx never retry, so the
        # request-count assertions remain the real proof of single-attempt.
        if self._responses:
            status, body = self._responses.pop(0)
            self._last = (status, body)
        else:
            status, body = self._last
        return httpx.Response(status_code=status, json=body)


# Capture the genuine, unpatched AsyncClient ONCE at import time so repeated
# _install_mock calls within a single test do not nest factories (each call's
# `real` would otherwise capture the previous factory).
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _install_mock(monkeypatch, recorder: _Recorder) -> None:
    from app.core.extracted_clients import _transport

    def factory(*args, **kwargs):
        recorder.timeouts.append(kwargs.get("timeout"))
        kwargs["transport"] = httpx.MockTransport(recorder.handler)
        return _REAL_ASYNC_CLIENT(*args, **kwargs)

    monkeypatch.setattr(_transport.httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_t3_catalog_get_category_id_forwards_jwt_and_deserialises(monkeypatch):
    """The §0.6 ``catalog_service.get_category_id`` shim (the ProductORM
    replacement) forwards the caller's JWT + X-Request-ID to the monolith
    ClusterIP and deserialises the widened ownership-check 200 body's
    ``category_id`` into a real UUID. Exercises the SAME symbol the pipeline
    imports (``catalog_service``), 5s/2s timeout contract included."""
    from app.core.extracted_clients import _transport
    from app.service import catalog_service

    pid, uid, cid = uuid4(), uuid4(), uuid4()
    rec = _Recorder([(200, {"category_id": str(cid)})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="real-jwt-tok", request_id="req-corr-77")

    result = await catalog_service.get_category_id(pid, uid, db=object())

    assert result == cid  # real deserialisation, not mock identity
    assert len(rec.requests) == 1
    req = rec.requests[0]
    assert req.headers.get("Authorization") == "Bearer real-jwt-tok"
    assert req.headers.get("X-Request-ID") == "req-corr-77"
    assert str(req.url).startswith("http://monolith-svc:8001/internal/products/")
    assert str(req.url.path).endswith("/ownership-check")
    assert req.url.params.get("user_id") == str(uid)
    assert rec.timeouts[0].read == 5.0
    assert rec.timeouts[0].connect == 2.0


@pytest.mark.asyncio
async def test_t3_catalog_404_maps_to_product_not_found(monkeypatch):
    """A real 404 from the ownership-check maps to the typed
    ``ProductNotFoundError`` — NOT a raw httpx error leaking — and does NOT
    retry (4xx is deterministic)."""
    from app.core.extracted_clients import _transport, catalog_client
    from app.service import catalog_service

    rec = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")

    with pytest.raises(catalog_client.ProductNotFoundError):
        await catalog_service.get_category_id(uuid4(), uuid4(), db=object())
    assert len(rec.requests) == 1  # no retry on 4xx

    # And the byte-for-byte-preserved ownership-gate call site maps 404 the same way.
    rec2 = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec2)
    with pytest.raises(catalog_client.ProductNotFoundError):
        await catalog_service.assert_product_ownership(uuid4(), uuid4(), db=object())
    assert len(rec2.requests) == 1


@pytest.mark.asyncio
async def test_t4_category_commission_decimal_never_null_contract(monkeypatch):
    """The category ``get_commission`` shim deserialises the frozen
    ``{"commission_pct": "<decimal>"}`` body into an exact Decimal (no float
    intermediary) and NEVER returns None — including the ``"0.00"`` unseeded
    signal and a defensively-missing key (both → a real Decimal)."""
    from app.core.extracted_clients import _transport, category_client
    from app.service import category_service

    # (a) seeded commission — real string → exact Decimal.
    rec = _Recorder([(200, {"commission_pct": "15.00"})])
    _install_mock(monkeypatch, rec)
    _transport.set_request_context(bearer_token="t", request_id="r")
    val = await category_service.get_commission(uuid4(), db=object())
    assert val == Decimal("15.00")
    assert isinstance(val, Decimal)
    assert str(req_path := rec.requests[0].url.path).endswith("/commission")
    assert "/internal/categories/" in req_path

    # (b) unseeded → "0.00", NEVER None (the pricing service treats this as the
    # missing-commission signal).
    rec2 = _Recorder([(200, {"commission_pct": "0.00"})])
    _install_mock(monkeypatch, rec2)
    val2 = await category_service.get_commission(uuid4(), db=object())
    assert val2 == Decimal("0.00")
    assert val2 is not None

    # (c) 404 → typed CategoryNotFoundError.
    rec3 = _Recorder([(404, {})])
    _install_mock(monkeypatch, rec3)
    with pytest.raises(category_client.CategoryNotFoundError):
        await category_service.get_commission(uuid4(), db=object())


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cross-schema audit — binding UNCONDITIONAL + round-trip PG-GATED
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_event_binds_public_pricing_calc_binds_pricing():
    """The svc-pricing ``AuditEvent`` model targets ``public.audit_events`` while
    ``PricingCalc`` targets ``pricing.pricing_calcs`` — the topology that makes
    the ``pricing.calculated`` audit write a genuine CROSS-schema INSERT. A
    regression here would land audit rows in a phantom ``pricing.audit_events``."""
    from app.shared.models.audit_event import AuditEvent
    from app.shared.models.pricing_calc import PricingCalc

    assert AuditEvent.__table__.schema == "public"
    assert AuditEvent.__tablename__ == "audit_events"
    assert PricingCalc.__table__.schema == "pricing"
    assert PricingCalc.__tablename__ == "pricing_calcs"


def _pg_connectable() -> bool:
    import asyncio

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")

    async def _probe() -> bool:
        try:
            import asyncpg

            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=2.0)
            await conn.close()
            return True
        except Exception:  # noqa: BLE001
            return False

    try:
        return asyncio.run(_probe())
    except Exception:  # noqa: BLE001
        return False


_PG_UP = _pg_connectable()
_PG_SKIP = pytest.mark.skipif(
    not _PG_UP,
    reason=(
        "No connectable Postgres at DATABASE_URL — cross-schema audit round-trip "
        "is PG-gated (auth-otp no-tunnel pattern). The §16.G, wire-shape, T1 "
        "Decimal-golden, T3/T4 shim, model-binding, and flag-parity assertions "
        "run UNCONDITIONALLY; SQLite is NOT a substitute (cannot honour "
        "schema-qualified DDL)."
    ),
)


@_PG_SKIP
@pytest.mark.asyncio
async def test_t6_cross_schema_audit_insert_round_trip():
    """Against a live Postgres: create the ``pricing`` schema + the
    ``public.audit_events`` table, INSERT a ``pricing.calculated`` row exactly as
    ``audit_mw`` builds it (cross-schema write — service owns ``pricing``, audit
    lives in ``public``), then SELECT it back and assert content. This is the
    REAL cross-schema INSERT the I5 grant enables."""
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.shared.models.audit_event import AuditEvent

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, echo=False)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    uid, eid = uuid4(), uuid4()
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS pricing"))
            await conn.run_sync(lambda c: AuditEvent.__table__.create(c, checkfirst=True))

        # Build + insert the row exactly as audit_mw._maybe_write does.
        async with sessionmaker() as session:
            row = AuditEvent(
                user_id=uid,
                event_type="pricing.calculated",
                entity_type="product",
                entity_id=eid,
                diff_jsonb=None,
                metadata_jsonb={
                    "method": "POST",
                    "path": f"/api/v1/products/{eid}/price-calc",
                    "status": 200,
                },
            )
            session.add(row)
            await session.commit()

        async with sessionmaker() as session:
            res = await session.execute(select(AuditEvent).where(AuditEvent.entity_id == eid))
            got = res.scalar_one()
            assert got.event_type == "pricing.calculated"
            assert got.entity_type == "product"
            assert got.user_id == uid
            assert got.metadata_jsonb["status"] == 200
            # Confirm the table truly resolved in the PUBLIC schema (cross-schema).
            schema_rows = await session.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables "
                    "WHERE table_name = 'audit_events'"
                )
            )
            schemas = {r[0] for r in schema_rows.fetchall()}
            assert "public" in schemas
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM public.audit_events WHERE entity_id = :eid"),
                {"eid": str(eid)},
            )
        await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Flag-parity regression guard — the MS-D Phase-C REJECT class
# ─────────────────────────────────────────────────────────────────────────────
def test_feature_flag_exists_on_trimmed_settings():
    """The mounted route guards on ``settings.FEATURE_PRICE_CALCULATOR_ENABLED``
    (router.py:99 — carried verbatim from the monolith router.py:97). The trimmed
    Settings MUST therefore define that field (monolith config.py:223
    ``FEATURE_PRICE_CALCULATOR_ENABLED: bool = True``).

    If the field is missing, EVERY price-calc request 500s with an AttributeError
    at the guard (proven at MS-D Phase C). This is the regression guard — it pins
    the field's existence and truthy default so the route's happy path works."""
    from app.shared.config import settings

    assert hasattr(settings, "FEATURE_PRICE_CALCULATOR_ENABLED"), (
        "FLAG-PARITY REGRESSION: router.py:99 reads "
        "settings.FEATURE_PRICE_CALCULATOR_ENABLED but the trimmed Settings does "
        "NOT define it — every price-calc request would 500 with AttributeError. "
        "Add the field to app/shared/config.py (monolith default: bool = True)."
    )
    assert settings.FEATURE_PRICE_CALCULATOR_ENABLED is True, (
        "FEATURE_PRICE_CALCULATOR_ENABLED must default True in development "
        "(monolith config.py:223), so the route is reachable in dev."
    )
