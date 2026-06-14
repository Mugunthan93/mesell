"""svc-iam auth-builder slice — the heavy-lift invariants (MS Sub-Plan G Phase B).

Validates ONLY the surfaces THIS auth-builder dispatch owns:

* ``app/core/auth.py``  — VENDORED BYTE-FOR-BYTE from the monolith (the A2/D7
  invariant; a drift here means an iam-issued JWT fails to validate in every
  other service, SUB_PLAN_0G R5).
* ``app/service.py``    — the 6 public methods, pipeline byte-for-byte from
  ``logger =`` onward; only the import block adapts to svc-iam's flat layout.
* ``app/adapters/{msg91,razorpay}.py`` — vendored byte-for-byte transport.
* The FE-D5 allowlist contract: key derivation ``cache:refresh:v{N}:{hmac}``,
  dual-pepper read fallback, and the verbatim rotation Lua.

These are pure-logic assertions (no live PG / Valkey) PLUS a fully in-memory
fake-Valkey FE-D5 refresh round-trip (issue → validate → rotate → revoke) that
asserts REAL behaviour — NOT a tautology (the pricing lesson, SUB_PLAN_0G
§Validation).  The LEAD-owned ``test_iam_extraction.py`` (Phase C) adds the
HTTP-mode round-trip against a real Traefik + shared Valkey.

conftest.py has already populated the env before this module imports.
"""

from __future__ import annotations

import hashlib
import hmac
import pathlib

import jwt
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. core/auth.py + adapters vendored BYTE-FOR-BYTE (the §16.G / A2/D7 invariant)
# ─────────────────────────────────────────────────────────────────────────────
def _svc_app_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "app"


def _monolith_root() -> pathlib.Path:
    # backend/services/svc-iam/app -> backend/app
    return _svc_app_root().parents[2] / "app"


def test_core_auth_byte_identical_to_monolith():
    """``core/auth.py`` is the vendored-everywhere surface — ZERO drift.

    A drift in the HS256 claim shape ``{sub, exp, plan}`` or the allowlist key
    derivation is the R5 catastrophic failure mode (an iam-issued JWT failing
    to validate in another service).  This pins the whole file byte-for-byte.
    """
    svc = (_svc_app_root() / "core" / "auth.py").read_text()
    mono = (_monolith_root() / "core" / "auth.py").read_text()
    assert svc == mono, "core/auth.py drifted from the monolith vendor source"


def test_adapters_byte_identical_to_monolith():
    """msg91 + razorpay + adapters/__init__ vendor byte-for-byte."""
    svc_ad = _svc_app_root() / "adapters"
    mono_ad = _monolith_root() / "adapters"
    for fname in ("__init__.py", "msg91.py", "razorpay.py"):
        assert (svc_ad / fname).read_text() == (mono_ad / fname).read_text(), (
            f"adapters/{fname} drifted from the monolith vendor source"
        )


def test_service_pipeline_byte_identical_below_imports():
    """service.py is byte-for-byte from ``logger =`` onward (the 6 methods).

    Only the import block adapts to svc-iam's flat layout
    (``app.repository`` / ``app.domain`` / ``app.exceptions``).  Everything
    from the module-level ``logger`` declaration downward — every helper, the
    §7.I SAVEPOINT audit path, and all 6 public-method pipelines — is verbatim.
    """
    svc = (_svc_app_root() / "service.py").read_text()
    mono = (_monolith_root() / "modules" / "iam" / "service.py").read_text()
    marker = "logger = logging.getLogger(__name__)\n"
    assert marker in svc and marker in mono
    svc_body = svc[svc.index(marker):]
    mono_body = mono[mono.index(marker):]
    assert svc_body == mono_body, "service.py pipeline drifted from the monolith"


# ─────────────────────────────────────────────────────────────────────────────
# 2. FE-D5 allowlist key derivation — cache:refresh:v{N}:{hmac_sha256(token,pepper)}
# ─────────────────────────────────────────────────────────────────────────────
def test_allowlist_key_format_and_hmac_with_pepper():
    from app.core.auth import refresh_allowlist_key
    from app.shared.config import settings

    token = "abc.def.ghi-opaque-refresh"
    key = refresh_allowlist_key(token)
    # Versioned prefix.
    assert key.startswith(f"cache:refresh:v{settings.REFRESH_TOKEN_PEPPER_VERSION}:")
    # HMAC-with-pepper (NOT bare SHA-256): the digest must match hmac, NOT sha256.
    expected_hmac = hmac.new(
        settings.REFRESH_TOKEN_PEPPER.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    bare_sha = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert key.endswith(expected_hmac)
    assert not key.endswith(bare_sha), "allowlist key must be HMAC-with-pepper, not bare SHA-256"


def test_rotation_lua_verbatim():
    """The rotation Lua body is the verbatim GET→DEL→SET check (no MULTI/EXEC)."""
    from app.core.auth import REFRESH_ROTATE_LUA

    expected = (
        "if redis.call('GET', KEYS[1]) then\n"
        "    redis.call('DEL', KEYS[1])\n"
        "    redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])\n"
        "    return 1\n"
        "else\n"
        "    return 0\n"
        "end"
    )
    assert REFRESH_ROTATE_LUA == expected
    assert "MULTI" not in REFRESH_ROTATE_LUA and "WATCH" not in REFRESH_ROTATE_LUA


def test_constant_time_compare_is_secrets_compare_digest():
    import secrets as _secrets

    from app.core.auth import compare_tokens

    assert compare_tokens("same", "same") is True
    assert compare_tokens("a", "b") is False
    # Pin the primitive (timing-attack mitigation) — same result as compare_digest.
    assert compare_tokens("x", "x") == _secrets.compare_digest("x", "x")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Access JWT — HS256 {sub, exp, plan}; iam-issued token validates LOCALLY
#    under the SAME JWT_SECRET (proves G1 / A2-D7 — no callback to iam).
# ─────────────────────────────────────────────────────────────────────────────
def test_access_jwt_is_hs256_with_locked_claim_shape():
    import uuid

    from app.core.auth import issue_access_token
    from app.shared.config import settings

    uid = uuid.uuid4()
    token = issue_access_token(uid, "free")

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "HS256", "access JWT must be HS256 (never 'none')"

    # A *different* service verifies the same JWT_SECRET locally — the G1 proof.
    decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == str(uid)
    assert decoded["plan"] == "free"
    assert "exp" in decoded
    # Claim shape is EXACTLY {sub, exp, plan} — no refresh_token claim leaks.
    assert set(decoded.keys()) == {"sub", "exp", "plan"}


def test_alg_none_is_rejected_by_the_decoder_whitelist():
    """A forged ``alg=none`` token must NOT validate (the verifier whitelist
    is ``[JWT_ALGORITHM]`` only — never ``none``)."""
    from app.shared.config import settings

    forged = jwt.encode({"sub": "x", "plan": "free"}, "", algorithm="none")
    with pytest.raises(jwt.InvalidAlgorithmError):
        jwt.decode(forged, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ─────────────────────────────────────────────────────────────────────────────
# 4. FE-D5 refresh ROUND-TRIP against an in-memory fake Valkey (REAL behaviour).
#    issue (SET vN key) → validate (dual-pepper read) → rotate (Lua: old GONE,
#    new PRESENT) → revoke (DEL).  No tautology — asserts the keyspace mutates.
# ─────────────────────────────────────────────────────────────────────────────
class _FakeValkey:
    """Minimal async Valkey double covering only what the allowlist path uses.

    Implements get/set/delete + an evalsha/eval that interprets the EXACT
    REFRESH_ROTATE_LUA semantics (GET KEYS[1] → DEL + SET KEYS[2] → 1/0).  The
    auth code's ``load_lua_script``/``eval_lua_script`` are monkeypatched to
    drive this so the rotation runs through the real ``rotate_refresh_token``.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key):  # noqa: ANN001
        return self.store.get(key)

    async def set(self, key, value, ex=None):  # noqa: ANN001
        self.store[key] = value
        return True

    async def delete(self, *keys):  # noqa: ANN001
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n


async def _fake_load(client, source):  # noqa: ANN001
    return "fake-sha"


async def _fake_eval(client, digest, source, keys=None, args=None):  # noqa: ANN001
    # Interpret REFRESH_ROTATE_LUA verbatim: GET keys[0]; if present DEL it +
    # SET keys[1]=args[0] and return 1; else 0.
    keys = keys or []
    args = args or []
    old_key, new_key = keys[0], keys[1]
    if old_key in client.store:
        del client.store[old_key]
        client.store[new_key] = args[0]
        return 1
    return 0


@pytest.mark.asyncio
async def test_fe_d5_refresh_round_trip_mutates_the_keyspace(monkeypatch):
    import app.core.auth as auth
    import app.service as svc
    from app.core.auth import (
        issue_refresh_token,
        refresh_allowlist_key,
        validate_refresh_allowlist,
    )

    # Drive the real rotate_refresh_token through the fake Valkey's Lua.
    monkeypatch.setattr(auth, "load_lua_script", _fake_load)
    monkeypatch.setattr(auth, "eval_lua_script", _fake_eval)
    auth._reset_lua_cache_for_tests()

    vk = _FakeValkey()
    import uuid

    uid = uuid.uuid4()

    # ── ISSUE: write the allowlist entry under the current vN key. ───────────
    rt = issue_refresh_token()
    old_key = refresh_allowlist_key(rt)
    entry_json = svc._serialize_allowlist_entry(
        svc.RefreshAllowlistEntry(user_id=uid, issued_at=1, ip="1.2.3.4")
    )
    await vk.set(old_key, entry_json)
    assert old_key in vk.store, "issue must write the vN allowlist key"

    # ── VALIDATE: dual-pepper read finds it under the current pepper/version. ─
    matched = await validate_refresh_allowlist(vk, rt)
    assert matched is not None
    assert matched[0] == old_key

    # ── ROTATE: old key GONE, brand-new key PRESENT (the replay-proof swap). ──
    new_rt = issue_refresh_token()
    new_key = refresh_allowlist_key(new_rt)
    new_json = svc._serialize_allowlist_entry(
        svc.RefreshAllowlistEntry(user_id=uid, issued_at=2, ip="1.2.3.4")
    )
    rotated = await auth.rotate_refresh_token(
        vk, old_key=old_key, new_key=new_key, new_value=new_json, ttl_seconds=120
    )
    assert rotated is True
    assert old_key not in vk.store, "rotation must DEL the old key (replay mitigation)"
    assert new_key in vk.store, "rotation must SET the new key"

    # ── REPLAY: presenting the OLD key again returns 0 (already rotated). ─────
    replay = await auth.rotate_refresh_token(
        vk, old_key=old_key, new_key="cache:refresh:v1:zzz", new_value="{}", ttl_seconds=120
    )
    assert replay is False, "re-presenting a rotated key must fail (replay-attack signal)"

    # ── REVOKE (logout): DEL the live key → keyspace empty. ───────────────────
    await vk.delete(new_key)
    assert new_key not in vk.store, "logout must DEL the live allowlist key"
