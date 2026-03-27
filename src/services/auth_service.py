import uuid

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import User
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


async def register_user(db: AsyncSession, email: str, password: str, display_name: str | None) -> User:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise LookupError("Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not user.hashed_password:
        raise ValueError("Invalid credentials")
    if not verify_password(password, user.hashed_password):
        raise ValueError("Invalid credentials")
    return user


def issue_tokens(user_id: uuid.UUID) -> dict:
    subject = str(user_id)
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "bearer",
    }


async def google_auth(db: AsyncSession, id_token: str) -> dict:
    """Verify a Google ID token and return our JWT tokens, creating the user if needed."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    if not settings.google_client_id:
        raise ValueError("Google OAuth is not configured (GOOGLE_CLIENT_ID not set)")

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as e:
        raise ValueError(f"Invalid Google ID token: {e}")

    google_id = payload["sub"]
    email = payload.get("email")
    display_name = payload.get("name")

    user = await db.scalar(select(User).where(User.google_id == google_id))

    if not user and email:
        user = await db.scalar(select(User).where(User.email == email))
        if user:
            user.google_id = google_id
            await db.commit()

    if not user:
        if not email:
            raise ValueError("Google account email is required to create a user")
        user = User(
            id=uuid.uuid4(),
            email=email,
            google_id=google_id,
            display_name=display_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return issue_tokens(user.id)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Token is not a refresh token")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        raise ValueError("Invalid token subject")

    user = await db.get(User, user_uuid)
    if not user:
        raise ValueError("User not found")

    return issue_tokens(user.id)
