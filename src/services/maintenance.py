"""Scheduled housekeeping."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def purge_expired_refresh_tokens() -> None:
    """Drop refresh-token rows that can no longer authorise anything."""
    from src.db.session import AsyncSessionLocal
    from src.services.auth_service import purge_expired_tokens

    try:
        async with AsyncSessionLocal() as db:
            removed = await purge_expired_tokens(db)
        if removed:
            logger.info("[Maintenance] Purged %d expired refresh token(s)", removed)
    except Exception:
        logger.exception("[Maintenance] Failed to purge expired refresh tokens")
