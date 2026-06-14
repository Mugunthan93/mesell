"""Integration — refresh-cookie environment-dependent attributes.

cookie-env-config feature.  The refresh cookie's ``Domain`` and ``Secure``
attributes derive from ``settings.COOKIE_DOMAIN`` / ``settings.COOKIE_SECURE``
so the cookie is accepted on ``http://localhost`` in local dev while remaining
``.mesell.xyz`` + ``Secure`` in production.

The FE-D5 security-critical attributes ``HttpOnly`` and ``SameSite=Strict`` are
code-enforced and must be present in EVERY environment.

We inspect the raw ``Set-Cookie`` header (not ``response.cookies``) because
httpx's cookie jar silently drops a ``.mesell.xyz``-domain cookie on a
``testserver`` request — see ``tests/integration/_cookie_helpers``.

The router's ``_set_refresh_cookie`` / ``_clear_refresh_cookie`` read
``settings.COOKIE_*`` at call time, so monkeypatching the singleton attrs
takes effect for the request under test.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.adapters.msg91 import Msg91Response

from tests.integration._cookie_helpers import extract_refresh_cookie


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_otp_in_valkey(phone: str, otp: str) -> None:
    """Bypass /otp/send: drop a known OTP record into Valkey directly."""
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )
    await valkey.set(f"otp:{phone}", payload, ex=300)


def _refresh_set_cookie_header(response) -> str:
    """Return the raw Set-Cookie header line carrying refresh_token."""
    for header in response.headers.get_list("set-cookie"):
        if "refresh_token=" in header:
            return header
    raise AssertionError("no refresh_token Set-Cookie header emitted")


def _assert_always_on(header: str) -> None:
    """FE-D5 security-critical attrs — present in EVERY environment."""
    low = header.lower()
    assert "httponly" in low, f"HttpOnly missing: {header!r}"
    assert "samesite=strict" in low, f"SameSite=Strict missing: {header!r}"
    assert "path=/api/v1/auth" in low, f"Path missing/wrong: {header!r}"


# ── env override matrix ──────────────────────────────────────────────────────
# (cookie_domain, cookie_secure, expect_domain_attr, expect_secure_attr)
_DEV = ("", False, False, False)
_PROD = (".mesell.xyz", True, True, True)


def _apply_env(monkeypatch, cookie_domain: str, cookie_secure: bool) -> None:
    """Override the settings singleton the router helpers read at call time."""
    from app.shared.config import settings

    monkeypatch.setattr(settings, "COOKIE_DOMAIN", cookie_domain, raising=False)
    monkeypatch.setattr(settings, "COOKIE_SECURE", cookie_secure, raising=False)


@pytest.mark.parametrize(
    "cookie_domain,cookie_secure,expect_domain,expect_secure",
    [_DEV, _PROD],
    ids=["dev", "prod"],
)
async def test_verify_cookie_env_attrs(
    iam_client,
    use_live_valkey,
    monkeypatch,
    cookie_domain,
    cookie_secure,
    expect_domain,
    expect_secure,
):
    """otp/verify Set-Cookie honours COOKIE_DOMAIN/COOKIE_SECURE; FE-D5 attrs always on."""
    _apply_env(monkeypatch, cookie_domain, cookie_secure)

    phone = "+915550000301"
    otp = "313131"
    await _seed_otp_in_valkey(phone, otp)

    async def _fake_send_otp(*args, **kwargs):
        return Msg91Response(success=True, request_id="test-req-id", message="")

    monkeypatch.setattr("app.adapters.msg91.send_otp", _fake_send_otp)

    r = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp},
    )
    assert r.status_code == 200, r.text
    assert extract_refresh_cookie(r), "verify must emit a non-empty refresh cookie"

    header = _refresh_set_cookie_header(r)
    low = header.lower()
    _assert_always_on(header)

    if expect_domain:
        assert "domain=.mesell.xyz" in low, f"expected Domain=.mesell.xyz: {header!r}"
    else:
        assert "domain=" not in low, f"dev must omit Domain: {header!r}"

    if expect_secure:
        assert "secure" in low, f"expected Secure: {header!r}"
    else:
        # Guard against substring false-positives (e.g. "samesite") — match the
        # standalone Secure attribute only.
        attrs = {p.strip().lower() for p in header.split(";")}
        assert "secure" not in attrs, f"dev must omit Secure: {header!r}"


@pytest.mark.parametrize(
    "cookie_domain,cookie_secure,expect_domain,expect_secure",
    [_DEV, _PROD],
    ids=["dev", "prod"],
)
async def test_logout_clear_cookie_env_attrs(
    iam_client,
    use_live_valkey,
    monkeypatch,
    cookie_domain,
    cookie_secure,
    expect_domain,
    expect_secure,
):
    """logout clear-cookie mirrors COOKIE_DOMAIN/COOKIE_SECURE (must match to clear)."""
    _apply_env(monkeypatch, cookie_domain, cookie_secure)

    # logout is idempotent — emits a clear-cookie regardless of cookie presence.
    r = await iam_client.post("/api/v1/auth/logout")
    assert r.status_code == 204, r.text

    header = _refresh_set_cookie_header(r)
    low = header.lower()
    _assert_always_on(header)

    if expect_domain:
        assert "domain=.mesell.xyz" in low, f"expected Domain=.mesell.xyz: {header!r}"
    else:
        assert "domain=" not in low, f"dev must omit Domain: {header!r}"

    if expect_secure:
        assert "secure" in low, f"expected Secure: {header!r}"
    else:
        attrs = {p.strip().lower() for p in header.split(";")}
        assert "secure" not in attrs, f"dev must omit Secure: {header!r}"
