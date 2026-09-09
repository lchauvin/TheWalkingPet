import uuid
from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import RefreshToken, User
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


async def register_user(db: AsyncSession, email: str, password: str, display_name: str | None) -> User:
    email = email.strip().lower()
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
    user = await db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not user.hashed_password:
        raise ValueError("Invalid credentials")
    if not verify_password(password, user.hashed_password):
        raise ValueError("Invalid credentials")
    return user


async def issue_tokens(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Mint an access/refresh pair and record the refresh token server-side."""
    jti = uuid.uuid4()
    refresh_token, expires_at = create_refresh_token(str(user_id), jti)

    db.add(RefreshToken(id=jti, user_id=user_id, expires_at=expires_at))
    await db.commit()

    return {
        "access_token": create_access_token(str(user_id)),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def google_auth(db: AsyncSession, id_token: str) -> dict:
    """Verify a Google ID token and return our JWT tokens, creating the user if needed."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    if not settings.google_client_id:
        raise ValueError("Google sign-in is not available")

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception:
        # The upstream message can echo token internals; keep it out of the response.
        raise ValueError("Invalid Google ID token")

    google_id = payload["sub"]
    email = (payload.get("email") or "").strip().lower() or None
    display_name = payload.get("name")

    # An unverified Google email must not be able to claim an existing account.
    email_verified = bool(payload.get("email_verified"))

    user = await db.scalar(select(User).where(User.google_id == google_id))

    if not user and email and email_verified:
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

    return await issue_tokens(db, user.id)


async def _consume_refresh_token(db: AsyncSession, refresh_token: str) -> tuple[User, RefreshToken]:
    """Validate a refresh token and return its user and (still-live) record."""
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Token is not a refresh token")

    try:
        user_uuid = uuid.UUID(str(payload.get("sub")))
        jti = uuid.UUID(str(payload.get("jti")))
    except (ValueError, TypeError):
        raise ValueError("Invalid or expired refresh token")

    record = await db.get(RefreshToken, jti)
    if not record or record.user_id != user_uuid:
        raise ValueError("Invalid or expired refresh token")

    if record.revoked_at is not None:
        # Replay of an already-rotated token: the family is compromised, so drop
        # every outstanding token for this user rather than just this one.
        await revoke_all_for_user(db, user_uuid)
        raise ValueError("Refresh token has been revoked")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("Invalid or expired refresh token")

    user = await db.get(User, user_uuid)
    if not user:
        raise ValueError("Invalid or expired refresh token")

    return user, record


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    """Rotate a refresh token: the presented one is retired as the new one is issued."""
    user, record = await _consume_refresh_token(db, refresh_token)

    new_jti = uuid.uuid4()
    new_token, expires_at = create_refresh_token(str(user.id), new_jti)

    record.revoked_at = datetime.now(timezone.utc)
    record.replaced_by = new_jti
    db.add(RefreshToken(id=new_jti, user_id=user.id, expires_at=expires_at))
    await db.commit()

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": new_token,
        "token_type": "bearer",
    }


async def logout(db: AsyncSession, refresh_token: str | None, user_id: uuid.UUID) -> None:
    """Revoke the presented refresh token, or every token for the user if none given."""
    if not refresh_token:
        await revoke_all_for_user(db, user_id)
        return

    try:
        _, record = await _consume_refresh_token(db, refresh_token)
    except ValueError:
        # Already invalid — logout is idempotent and must not leak which case it was.
        return

    if record.user_id != user_id:
        return

    record.revoked_at = datetime.now(timezone.utc)
    await db.commit()


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def purge_expired_tokens(db: AsyncSession) -> int:
    """Delete refresh-token rows that can no longer authorise anything."""
    from sqlalchemy import delete

    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount or 0
