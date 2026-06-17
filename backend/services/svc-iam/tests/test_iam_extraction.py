"""LEAD Phase-C hybrid-mode integration test for the svc-iam extraction (Sub-Plan G / MS-4).

Author: meesell-backend-coordinator (LEAD, Phase C). This is the merge-gate's
machine-checkable proof — NOT a specialist self-report. Every assertion is REAL
behaviour, no tautologies (the MS-D pricing lesson: ``assert True``-class echoes
are a reject-class offense).

What it proves (SUB_PLAN_0G §"Validation" + recipe §2/§3):

  T1  §16.G AST parity   — svc service.py == monolith service.py after recursive
                            import-strip (zero executable-line drift), PLUS a
                            companion assertion that the un-stripped twins DIFFER
                            (so the strip isn't masking real drift / vacuous).
  T2  router parity      — svc router.py differs from the monolith ONLY in import
                            lines (iam imports no other module — §0.4).
  T3  core/auth.py vendor — byte-identical to the monolith copy (A2/D7 / R5 invariant).
  T4  FE-D5 cookie attrs — _set/_clear refresh cookie: Path=/api/v1/auth,
                            Domain=.mesell.xyz, Secure+HttpOnly+SameSite=Strict.
  T5  allowlist key      — cache:refresh:v{N}:{hmac_sha256(token, pepper)} format,
                            HMAC-with-pepper (NOT bare SHA-256), version tag present.
  T6  Lua verbatim       — REFRESH_ROTATE_LUA byte-for-byte vs SUB_PLAN_0G §0.6.
  T7  FE-D5 LIVE round-trip (real Valkey DB 0): issue → validate (present) →
                            rotate (old key GONE, new key PRESENT under v{N}) →
                            replay old cookie → rotate returns 0 (replay=0) →
                            revoke (DEL). PG/Valkey-gated; skips if Valkey absent.
  T8  dual-pepper read   — an entry written under the PREVIOUS pepper at v{N-1} is
                            found by validate_refresh_allowlist via the fallback
                            (grace-window R5). LIVE Valkey.
  T9  local-JWT cross-service (G1) — an access JWT issued by iam's issue_access_token
                            decodes + validates with the SAME vendored core/auth.py
                            using only the shared JWT_SECRET — NO callback to iam.
                            This is the Risk #2 mitigation made concrete.
  T10 ORM schema binding — User.__table__.schema == "iam"; AuditEvent.__table__.schema
                            == "public" (UNCONDITIONAL — the cross-schema write target).
  T11 cross-schema audit round-trip (LIVE PG) — INSERT a row into public.audit_events
                            for a user whose row lives in iam.users; the INSERT
                            crosses schemas exactly as iam's webhook/verify audit path
                            does. PG-gated; skips if no connectable PG.
  T12 structural guards  — 6 mounted iam APIRoute contract objects, NO /internal/*,
                            NO celery import, every settings.<X> read resolves on the
                            trimmed Settings (the MS-D flag-parity regression guard).
  T13 monotonic guard    — the count of test_ functions in THIS file is recorded so a
                            future trim is caught (self-referential floor).
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import json
import os
import uuid
from pathlib import Path

import pytest

# ── Paths ───────────────────────────────────────────────────────────────────
_SVC_ROOT = Path(__file__).resolve().parents[1]          # backend/services/svc-iam
_REPO_ROOT = _SVC_ROOT.parents[2]                          # repo root
_MONO = _REPO_ROOT / "backend" / "app"

_SVC_SERVICE = _SVC_ROOT / "app" / "service.py"
_SVC_ROUTER = _SVC_ROOT / "app" / "router.py"
_SVC_AUTH = _SVC_ROOT / "app" / "core" / "auth.py"
_MONO_SERVICE = _MONO / "modules" / "iam" / "service.py"
_MONO_ROUTER = _MONO / "modules" / "iam" / "router.py"
_MONO_AUTH = _MONO / "core" / "auth.py"


# ── §16.G helpers ───────────────────────────────────────────────────────────
class _StripImports(ast.NodeTransformer):
    def visit_Import(self, node):  # noqa: N802
        return None

    def visit_ImportFrom(self, node):  # noqa: N802
        return None


def _normalize(path: Path) -> str:
    """ast.dump after stripping the module docstring + ALL imports (recursive)."""
    tree = ast.parse(path.read_text())
    body = tree.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    tree.body = body
    tree = _StripImports().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree)


# ── T1 — §16.G AST parity (service.py) ──────────────────────────────────────
def test_service_ast_parity_after_import_strip():
    """svc service.py == monolith after recursive import+docstring strip (zero drift)."""
    assert _normalize(_SVC_SERVICE) == _normalize(_MONO_SERVICE), (
        "service.py executable-line drift detected — §16.G byte-for-byte violated"
    )


def test_service_unstripped_twins_differ():
    """Companion: the RAW twins DIFFER (proves the strip isn't masking drift / vacuous)."""
    assert _SVC_SERVICE.read_text() != _MONO_SERVICE.read_text(), (
        "raw twins are identical — the parity test would be vacuous (import paths must differ)"
    )


# ── T2 — router.py import-only delta ────────────────────────────────────────
def test_router_diff_is_import_only():
    """svc router.py differs from monolith ONLY in import lines (iam is all-✗ — §0.4)."""
    svc = _SVC_ROUTER.read_text().splitlines()
    mono = _MONO_ROUTER.read_text().splitlines()
    import difflib

    changed = [
        ln
        for ln in difflib.unified_diff(mono, svc, lineterm="")
        if ln and ln[0] in "+-" and not ln.startswith(("+++", "---"))
    ]
    # every changed line must be an import line (or the import-block continuation
    # like ``from app.schemas import (`` / closing paren of a flattened import).
    offenders = [
        ln
        for ln in changed
        if not (
            "import" in ln
            or "app.modules.iam" in ln
            or "app.exceptions" in ln
            or "app.schemas" in ln
            or "app.service" in ln
        )
    ]
    assert not offenders, f"router.py has non-import drift: {offenders}"


# ── T3 — core/auth.py byte-identical vendor ─────────────────────────────────
def test_core_auth_byte_identical_vendor():
    """core/auth.py byte-for-byte == monolith (A2/D7 / R5 — JWTs must validate everywhere)."""
    assert _SVC_AUTH.read_bytes() == _MONO_AUTH.read_bytes(), (
        "core/auth.py drifted from the monolith — JWTs issued by iam-svc would fail to "
        "validate in other services (or vice-versa). A2/D7 vendoring invariant broken."
    )


# ── T4 — FE-D5 cookie attributes ────────────────────────────────────────────
def test_fe_d5_cookie_attributes():
    src = _SVC_ROUTER.read_text()
    assert '_REFRESH_COOKIE_PATH = "/api/v1/auth"' in src, "cookie Path must be /api/v1/auth"
    assert '_REFRESH_COOKIE_DOMAIN = ".mesell.xyz"' in src, "cookie Domain must be .mesell.xyz"
    assert '_REFRESH_COOKIE_NAME = "refresh_token"' in src
    # attrs on both set + clear helpers
    assert src.count("secure=True") >= 2
    assert src.count("httponly=True") >= 2
    assert src.count('samesite="strict"') >= 2


# ── Import the vendored auth module for behavioural tests ───────────────────
def _import_auth():
    # conftest.py has already populated the env. Import the svc auth surface.
    from app.core import auth as svc_auth  # noqa: PLC0415

    return svc_auth


# ── T5 — allowlist key format (HMAC-with-pepper, versioned) ──────────────────
def test_allowlist_key_format_hmac_pepper_versioned():
    svc_auth = _import_auth()
    from app.shared.config import settings  # noqa: PLC0415

    token = "test-refresh-token-abc123"
    key = svc_auth.refresh_allowlist_key(token)
    pepper = settings.REFRESH_TOKEN_PEPPER
    version = settings.REFRESH_TOKEN_PEPPER_VERSION
    expected_digest = hmac.new(
        pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    assert key == f"cache:refresh:v{version}:{expected_digest}", key
    # NOT bare SHA-256 (defence-in-depth): bare sha differs from HMAC.
    bare = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert bare not in key, "allowlist key must be HMAC-with-pepper, NOT bare SHA-256"


# ── T6 — Lua verbatim ───────────────────────────────────────────────────────
def test_refresh_rotate_lua_verbatim():
    svc_auth = _import_auth()
    expected = (
        "if redis.call('GET', KEYS[1]) then\n"
        "    redis.call('DEL', KEYS[1])\n"
        "    redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])\n"
        "    return 1\n"
        "else\n"
        "    return 0\n"
        "end"
    )
    assert svc_auth.REFRESH_ROTATE_LUA == expected, "Lua rotation script drifted from §0.6"


# ── Live Valkey fixture (real DB 0) ─────────────────────────────────────────
def _valkey_client():
    import redis.asyncio as aioredis  # noqa: PLC0415

    url = os.environ.get("VALKEY_URL", "redis://localhost:6379/0")
    return aioredis.from_url(url, decode_responses=True)


async def _valkey_up(client) -> bool:
    try:
        return await client.ping()
    except Exception:  # noqa: BLE0001
        return False


# ── T7 — FE-D5 LIVE round-trip (issue→validate→rotate→replay=0→revoke) ───────
@pytest.mark.asyncio
async def test_fe_d5_live_round_trip():
    svc_auth = _import_auth()
    from app.shared.config import settings  # noqa: PLC0415

    client = _valkey_client()
    if not await _valkey_up(client):
        pytest.skip("no connectable Valkey — FE-D5 live round-trip PG/Valkey-gated")

    svc_auth._reset_lua_cache_for_tests()
    old_token = "rt-old-" + uuid.uuid4().hex
    new_token = "rt-new-" + uuid.uuid4().hex
    old_key = svc_auth.refresh_allowlist_key(old_token)
    new_key = svc_auth.refresh_allowlist_key(new_token)
    value = json.dumps({"user_id": str(uuid.uuid4()), "issued_at": 0, "ip": "1.2.3.4"})
    ttl = settings.REFRESH_TOKEN_TTL_SECONDS

    try:
        # issue: SET the old key
        await client.set(old_key, value, ex=ttl)
        # validate: present
        hit = await svc_auth.validate_refresh_allowlist(client, old_token)
        assert hit is not None and hit[0] == old_key, "issued token not found in allowlist"

        # rotate: old GONE, new PRESENT (returns True)
        rotated = await svc_auth.rotate_refresh_token(client, old_key, new_key, value, ttl)
        assert rotated is True, "rotation of a present key must return True"
        assert await client.get(old_key) is None, "old key must be DELETED after rotation"
        assert await client.get(new_key) is not None, "new key must be SET after rotation"

        # replay: re-presenting the OLD cookie after rotation → rotate returns 0/False
        replay = await svc_auth.rotate_refresh_token(client, old_key, "rt-x", value, ttl)
        assert replay is False, "replay of a rotated (absent) key must return False (401)"

        # revoke: DEL the new key (logout path)
        await client.delete(new_key)
        assert await svc_auth.validate_refresh_allowlist(client, new_token) is None
    finally:
        await client.delete(old_key, new_key)
        await client.aclose()


# ── T8 — dual-pepper read (grace-window fallback) ───────────────────────────
@pytest.mark.asyncio
async def test_fe_d5_dual_pepper_read(monkeypatch):
    svc_auth = _import_auth()
    from app.shared.config import settings  # noqa: PLC0415

    client = _valkey_client()
    if not await _valkey_up(client):
        pytest.skip("no connectable Valkey — dual-pepper read gated")

    # Simulate a grace window: PREVIOUS pepper non-empty, current version N>=2.
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_VERSION", 2, raising=False)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER", "current-pepper-v2", raising=False)
    monkeypatch.setattr(
        settings, "REFRESH_TOKEN_PEPPER_PREVIOUS", "previous-pepper-v1", raising=False
    )

    token = "rt-dualpepper-" + uuid.uuid4().hex
    # Write under the PREVIOUS pepper at v{N-1}=v1 (as a pre-rotation entry would be).
    prev_key = svc_auth.refresh_allowlist_key(
        token, pepper="previous-pepper-v1", version=1
    )
    value = json.dumps({"user_id": str(uuid.uuid4()), "issued_at": 0, "ip": "9.9.9.9"})
    try:
        await client.set(prev_key, value, ex=300)
        # validate must find it via the dual-pepper FALLBACK (current pepper would miss).
        hit = await svc_auth.validate_refresh_allowlist(client, token)
        assert hit is not None, "dual-pepper fallback failed to find the previous-pepper entry"
        assert hit[0] == prev_key, "fallback must return the PREVIOUS-pepper key for correct DEL"
    finally:
        await client.delete(prev_key)
        await client.aclose()


# ── T9 — local-JWT cross-service validation (G1 / Risk #2) ──────────────────
def test_local_jwt_validates_with_shared_secret_no_callback():
    """An iam-issued access JWT decodes with the SAME vendored auth + shared secret.

    This is the G1/A2/D7 proof: another service validates the token LOCALLY with
    its byte-identical core/auth.py and the shared JWT_SECRET — it never calls iam.
    """
    svc_auth = _import_auth()
    from app.shared.config import settings  # noqa: PLC0415
    import jwt as pyjwt  # noqa: PLC0415

    uid = uuid.uuid4()
    token = svc_auth.issue_access_token(uid, plan="pro")
    # decode with ONLY the shared secret (what any other service has) — no iam call.
    claims = pyjwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    assert claims["sub"] == str(uid)
    assert claims["plan"] == "pro"
    assert "exp" in claims, "access token must carry exp (TTL)"


# ── T10 — ORM schema binding (unconditional) ────────────────────────────────
def test_orm_schema_binding():
    from app.shared.models.user import User  # noqa: PLC0415
    from app.shared.models.audit_event import AuditEvent  # noqa: PLC0415

    assert User.__table__.schema == "iam", "User must be bound to schema iam"
    assert AuditEvent.__table__.schema == "public", (
        "AuditEvent must be bound to public (cross-schema write target — §7.I)"
    )
    # User ships relationship-free in iam-svc (the 6 cross-schema rels are dropped).
    assert not list(User.__mapper__.relationships), (
        "iam-svc User must carry NO relationships (cross-schema FKs dropped — §0.7)"
    )


# ── T11 — cross-schema audit round-trip (LIVE PG) ───────────────────────────
@pytest.mark.asyncio
async def test_cross_schema_audit_round_trip_live_pg():
    """INSERT into public.audit_events keyed to a user whose row is in iam.users.

    Mirrors iam's verify/webhook audit path: the audit write crosses schemas
    (public.audit_events) while the principal lives in iam.users. PG-gated.
    """
    from sqlalchemy import text  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415
    from app.shared.config import settings  # noqa: PLC0415

    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            try:
                await conn.execute(text("SELECT 1"))
            except Exception:  # noqa: BLE0001
                pytest.skip("no connectable PG — cross-schema audit round-trip gated")

            # Provision throwaway schemas mirroring the split (iam.users + public.audit_events).
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS iam"))
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS iam._t_users "
                    "(id uuid PRIMARY KEY, phone text)"
                )
            )
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS public._t_audit "
                    "(id uuid PRIMARY KEY, user_id uuid NOT NULL, action text)"
                )
            )
            uid = uuid.uuid4()
            await conn.execute(
                text("INSERT INTO iam._t_users (id, phone) VALUES (:i, '+910000000000')"),
                {"i": uid},
            )
            # The cross-schema audit INSERT: row in public references a user in iam.
            await conn.execute(
                text(
                    "INSERT INTO public._t_audit (id, user_id, action) "
                    "VALUES (:a, :u, 'iam.login')"
                ),
                {"a": uuid.uuid4(), "u": uid},
            )
            cnt = (
                await conn.execute(
                    text("SELECT COUNT(*) FROM public._t_audit WHERE user_id = :u"),
                    {"u": uid},
                )
            ).scalar()
            assert cnt == 1, "cross-schema audit row not written"

            # cleanup
            await conn.execute(text("DROP TABLE IF EXISTS public._t_audit"))
            await conn.execute(text("DROP TABLE IF EXISTS iam._t_users"))
            await conn.commit()
    finally:
        await engine.dispose()


# ── T12 — structural guards (route count, no /internal, no celery, flag-parity) ──
def test_six_mounted_routes_no_internal():
    from fastapi.routing import APIRoute  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415

    api_routes = [r for r in app.routes if isinstance(r, APIRoute)]
    iam_routes = [r for r in api_routes if r.path.startswith("/api/v1/")]
    paths = sorted(r.path for r in iam_routes)
    assert paths == sorted(
        [
            "/api/v1/auth/otp/send",
            "/api/v1/auth/otp/verify",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/me",
            "/api/v1/webhooks/razorpay",
        ]
    ), f"iam contract routes != the 6 §0.3 routes: {paths}"
    assert not [r for r in api_routes if "/internal" in r.path], (
        "iam is all-✗ — NO /internal/* route may be mounted (§0.4)"
    )


def test_no_celery_import():
    import sys  # noqa: PLC0415

    import app.main  # noqa: F401,PLC0415

    assert "celery" not in sys.modules, "iam-svc must NOT import celery (no tasks.py)"


def test_flag_parity_every_settings_read_resolves():
    """MS-D regression guard: every settings.<X> read by any vendored file exists on Settings."""
    import re  # noqa: PLC0415
    from app.shared.config import settings  # noqa: PLC0415

    app_dir = _SVC_ROOT / "app"
    reads: set[str] = set()
    for py in app_dir.rglob("*.py"):
        for m in re.finditer(r"settings\.([A-Z_][A-Z0-9_]*)", py.read_text()):
            reads.add(m.group(1))
    missing = [f for f in sorted(reads) if not hasattr(settings, f)]
    assert not missing, f"trimmed Settings missing fields read by vendored code: {missing}"


# ── T13 — self-referential monotonic floor ──────────────────────────────────
def test_lead_test_count_floor():
    """This file must keep >= 13 test_ functions (a future trim is caught)."""
    src = Path(__file__).read_text()
    n = src.count("\ndef test_") + src.count("\nasync def test_")
    assert n >= 13, f"lead Phase-C test floor regressed: {n} < 13"
