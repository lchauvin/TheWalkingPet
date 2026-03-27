"""FCM push notification service."""
from __future__ import annotations

import asyncio
import logging

from src.config import settings

FCM_TIMEOUT_SECONDS = 10
from src.db.models import Match

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _get_firebase_app():
    global _firebase_initialized
    if _firebase_initialized:
        return
    if not settings.firebase_credentials_path:
        return
    import firebase_admin
    from firebase_admin import credentials
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    _firebase_initialized = True


async def notify_match(match: Match) -> None:
    """Send a push notification to the pet owner for a new match."""
    from src.db.session import AsyncSessionLocal
    from src.db.models import LostDeclaration, Pet, User

    async with AsyncSessionLocal() as db:
        decl = await db.get(LostDeclaration, match.lost_declaration_id)
        if not decl:
            return
        pet = await db.get(Pet, decl.pet_id)
        if not pet:
            return
        owner = await db.get(User, pet.owner_id)
        if not owner:
            return

        if not owner.fcm_token:
            logger.info(f"[Notification] Match {match.id}: owner has no FCM token, skipping push.")
            return

        _get_firebase_app()

        if not _firebase_initialized:
            logger.info(
                f"[Notification] Firebase not configured. Match {match.id}: "
                f"sighting={match.sighting_id} score={match.similarity_score:.3f}"
            )
            return

        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"Possible sighting of {pet.name}!",
                    body=f"Someone may have spotted your pet. Similarity: {match.similarity_score:.0%}",
                ),
                data={
                    "match_id": str(match.id),
                    "sighting_id": str(match.sighting_id),
                    "similarity_score": str(round(match.similarity_score, 4)),
                },
                token=owner.fcm_token,
            )
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: messaging.send(message)),
                timeout=FCM_TIMEOUT_SECONDS,
            )
            logger.info(f"[Notification] Push sent for match {match.id}: {response}")
        except asyncio.TimeoutError:
            logger.error(
                f"[Notification] Push timed out after {FCM_TIMEOUT_SECONDS}s for match {match.id}"
            )
        except Exception as e:
            logger.error(f"[Notification] Failed to send push for match {match.id}: {e}")
