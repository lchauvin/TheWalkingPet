"""FastAPI dependency injection: DB session, current user, ML models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import AsyncSessionLocal
from src.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=True)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class MLModels:
    embedder: object | None = None
    detector: object | None = None


ml_models = MLModels()


def set_ml_models(embedder, detector) -> None:
    ml_models.embedder = embedder
    ml_models.detector = detector


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    from src.db.models import User

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise _UNAUTHORIZED

    if payload.get("type") != "access":
        raise _UNAUTHORIZED

    try:
        user_uuid = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise _UNAUTHORIZED

    user = await db.get(User, user_uuid)
    if not user:
        raise _UNAUTHORIZED

    return user


def get_embedder():
    if ml_models.embedder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Embedder not ready"
        )
    return ml_models.embedder


def get_detector():
    if ml_models.detector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Detector not ready"
        )
    return ml_models.detector
