"""OTP generation, storage in Valkey, and verification.

In development mode (`APP_ENV=development`) the OTP `1234` is always accepted
and MSG91 is not called. In any other mode, a 4-digit OTP is generated,
stored in Valkey with a 5-minute TTL, and dispatched via MSG91.
"""

import json
import logging
import secrets

import httpx
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 300
MAX_ATTEMPTS = 3
DEV_OTP = "1234"


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"


class OTPService:
    def __init__(self, valkey: redis.Redis):
        self.valkey = valkey

    async def send_otp(self, phone: str) -> str:
        """Generate an OTP, persist it, and dispatch via MSG91 (skipped in dev)."""
        if settings.is_dev:
            code = DEV_OTP
            logger.info(f"[dev] OTP for {phone} = {code} (MSG91 skipped)")
        else:
            code = f"{secrets.randbelow(10_000):04d}"

        payload = json.dumps({"code": code, "attempts": 0})
        await self.valkey.set(_otp_key(phone), payload, ex=OTP_TTL_SECONDS)

        if not settings.is_dev:
            await self._dispatch_msg91(phone, code)

        return code

    async def verify_otp(self, phone: str, code: str) -> bool:
        """Verify an OTP. Returns True on success, False on miss / lockout / expiry."""
        key = _otp_key(phone)
        raw = await self.valkey.get(key)
        if raw is None:
            return False

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self.valkey.delete(key)
            return False

        if data["code"] == code:
            await self.valkey.delete(key)
            return True

        attempts = data["attempts"] + 1
        if attempts >= MAX_ATTEMPTS:
            await self.valkey.delete(key)
            logger.info(f"OTP for {phone} exhausted after {attempts} attempts")
            return False

        ttl = await self.valkey.ttl(key)
        data["attempts"] = attempts
        await self.valkey.set(key, json.dumps(data), ex=max(ttl, 1))
        return False

    async def _dispatch_msg91(self, phone: str, code: str) -> None:
        """Send the OTP via MSG91. Logs and swallows transport errors."""
        if not settings.MSG91_AUTH_KEY:
            logger.warning("MSG91_AUTH_KEY not configured; OTP not dispatched")
            return

        url = "https://control.msg91.com/api/v5/otp"
        params = {
            "template_id": settings.MSG91_TEMPLATE_ID,
            "mobile": phone.lstrip("+"),
            "authkey": settings.MSG91_AUTH_KEY,
            "otp": code,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(f"MSG91 dispatch failed for {phone}: {exc}")
