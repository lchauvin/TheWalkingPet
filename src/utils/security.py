import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt silently truncates at 72 bytes; reject longer input rather than
# quietly ignoring the tail of a passphrase.
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode("utf-8")) > BCRYPT_MAX_BYTES:
        return False
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "type": "access",
            "jti": str(uuid.uuid4()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str, jti: uuid.UUID) -> tuple[str, datetime]:
    """Return the encoded refresh token and its expiry.

    The caller records `jti` server-side; a refresh token is only accepted while
    that row exists and is unrevoked, which is what makes logout and rotation
    real rather than advisory.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    token = jwt.encode(
        {
            "sub": subject,
            "iat": now,
            "exp": expires_at,
            "type": "refresh",
            "jti": str(jti),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
