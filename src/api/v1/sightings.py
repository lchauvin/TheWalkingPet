import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db, get_detector, get_embedder
from src.schemas.sighting import SightingOut

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_matching_bg(sighting_id: uuid.UUID) -> None:
    """Background task: open its own session to run matching + notify."""
    from src.db.models import Sighting
    from src.db.session import AsyncSessionLocal
    from src.services.matching_service import run_matching
    from src.services.notification_service import notify_match

    try:
        async with AsyncSessionLocal() as db:
            sighting = await db.get(Sighting, sighting_id)
            if not sighting:
                return
            matches = await run_matching(db, sighting)
            logger.info(f"[BG] sighting={sighting_id} produced {len(matches)} match(es)")
            for match in matches:
                await notify_match(match)
    except Exception:
        logger.exception(f"[BG] Error in matching background task for sighting={sighting_id}")


@router.post("", response_model=SightingOut, status_code=status.HTTP_201_CREATED)
async def submit_sighting(
    file: UploadFile,
    latitude: float = Form(...),
    longitude: float = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    embedder=Depends(get_embedder),
    detector=Depends(get_detector),
):
    from src.schemas.sighting import SightingCreate
    from src.services import sighting_service

    data = SightingCreate(latitude=latitude, longitude=longitude)
    sighting = await sighting_service.create_sighting(
        db, current_user.id, file, data, embedder, detector
    )
    background_tasks.add_task(_run_matching_bg, sighting.id)
    return sighting
