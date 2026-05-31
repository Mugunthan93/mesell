"""OTPService — gen, store, verify, lockout, dev mode."""

import json
import uuid

import pytest
import pytest_asyncio
import redis.asyncio as redis

from app.services.otp_service import (
    DEV_OTP,
    MAX_ATTEMPTS,
    OTP_TTL_SECONDS,
    OTPService,
    _otp_key,
)


@pytest_asyncio.fixture
async def valkey():
    r = redis.from_url("redis://localhost:6381/14", decode_responses=True)
    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()


@pytest.mark.asyncio
async def test_dev_mode_uses_fixed_otp(valkey):
    svc = OTPService(valkey)
    code = await svc.send_otp("+919000000001")
    assert code == DEV_OTP
    raw = await valkey.get(_otp_key("+919000000001"))
    assert raw is not None
    assert json.loads(raw)["code"] == DEV_OTP
    ttl = await valkey.ttl(_otp_key("+919000000001"))
    assert 0 < ttl <= OTP_TTL_SECONDS


@pytest.mark.asyncio
async def test_verify_success_evicts_key(valkey):
    phone = "+919000000002"
    svc = OTPService(valkey)
    await svc.send_otp(phone)
    assert await svc.verify_otp(phone, DEV_OTP) is True
    assert await valkey.exists(_otp_key(phone)) == 0


@pytest.mark.asyncio
async def test_verify_wrong_code_decrements_attempts(valkey):
    phone = "+919000000003"
    svc = OTPService(valkey)
    await svc.send_otp(phone)
    for _ in range(MAX_ATTEMPTS - 1):
        assert await svc.verify_otp(phone, "0000") is False
    raw = json.loads(await valkey.get(_otp_key(phone)))
    assert raw["attempts"] == MAX_ATTEMPTS - 1
    # Last allowed wrong attempt evicts the key.
    assert await svc.verify_otp(phone, "0000") is False
    assert await valkey.exists(_otp_key(phone)) == 0


@pytest.mark.asyncio
async def test_verify_returns_false_when_no_otp(valkey):
    svc = OTPService(valkey)
    assert await svc.verify_otp("+919000000099", DEV_OTP) is False


@pytest.mark.asyncio
async def test_verify_corrupt_payload_evicts(valkey):
    phone = "+919000000004"
    await valkey.set(_otp_key(phone), "not-json", ex=300)
    svc = OTPService(valkey)
    assert await svc.verify_otp(phone, "1234") is False
    assert await valkey.exists(_otp_key(phone)) == 0


@pytest.mark.asyncio
async def test_ttl_preserved_across_attempts(valkey):
    """An incorrect attempt should not reset / extend the original TTL."""
    phone = "+919000000005"
    svc = OTPService(valkey)
    await svc.send_otp(phone)
    ttl_before = await valkey.ttl(_otp_key(phone))
    assert await svc.verify_otp(phone, "0000") is False
    ttl_after = await valkey.ttl(_otp_key(phone))
    # TTL must not jump forward — within ~1s of the original.
    assert ttl_after <= ttl_before
    assert ttl_after >= ttl_before - 2
