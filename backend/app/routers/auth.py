"""Phone OTP login + JWT auth endpoints."""

import logging
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import create_token, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    SendOTPRequest,
    SendOTPResponse,
    UserResponse,
    VerifyOTPRequest,
)
from app.services.otp_service import OTPService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def get_valkey(request: Request) -> redis.Redis:
    return request.app.state.valkey


def get_otp_service(
    valkey: Annotated[redis.Redis, Depends(get_valkey)],
) -> OTPService:
    return OTPService(valkey)


@router.post("/otp/send", response_model=SendOTPResponse, summary="Send OTP to phone number")
async def send_otp(
    data: SendOTPRequest,
    otp_service: Annotated[OTPService, Depends(get_otp_service)],
) -> SendOTPResponse:
    code = await otp_service.send_otp(data.phone)
    return SendOTPResponse(sent=True, dev_otp=code if settings.is_dev else None)


@router.post("/otp/verify", response_model=AuthResponse, summary="Verify OTP and return JWT")
async def verify_otp(
    data: VerifyOTPRequest,
    otp_service: Annotated[OTPService, Depends(get_otp_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    ok = await otp_service.verify_otp(data.phone, data.otp)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(phone=data.phone, plan="free")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user registered: {user.id} ({data.phone})")

    token = create_token(user.id, user.plan)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(user)
