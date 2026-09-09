import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.config import settings


def _validate_password(value: str) -> str:
    if len(value) < settings.password_min_length:
        raise ValueError(
            f"Password must be at least {settings.password_min_length} characters"
        )
    if len(value.encode("utf-8")) > 72:
        # bcrypt truncates beyond 72 bytes; refuse rather than silently ignore.
        raise ValueError("Password is too long (max 72 bytes)")
    if value.strip() == "":
        raise ValueError("Password must not be blank")
    return value


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    _check_password = field_validator("password")(_validate_password)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(max_length=4096)


class LogoutRequest(BaseModel):
    """Revokes the given refresh token, or every session when omitted."""

    refresh_token: str | None = Field(default=None, max_length=4096)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(max_length=8192)


class FcmTokenUpdate(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=512)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    latitude: float | None
    longitude: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
