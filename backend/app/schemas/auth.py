"""Auth request and response schemas."""

import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

INDIAN_PHONE_RE = re.compile(r"^\+91[6-9]\d{9}$")


class SendOTPRequest(BaseModel):
    phone: str = Field(..., description="Indian phone number in +91XXXXXXXXXX format")

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not INDIAN_PHONE_RE.match(v):
            raise ValueError("phone must be in +91XXXXXXXXXX format")
        return v


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=4, max_length=6)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not INDIAN_PHONE_RE.match(v):
            raise ValueError("phone must be in +91XXXXXXXXXX format")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    name: str | None = None
    plan: str
    catalogs_used: int
    catalogs_limit: int


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class SendOTPResponse(BaseModel):
    sent: bool = True
    dev_otp: str | None = Field(
        default=None,
        description="Echoed OTP when APP_ENV=development; null in production.",
    )
