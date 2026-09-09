import logging
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import LocationSource
from src.dependencies import get_current_user, get_db, get_detector, get_embedder
from src.schemas.sighting import SightingOut
from src.utils.rate_limit import limiter

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
@limiter.limit(settings.rate_limit_write)
async def submit_sighting(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    # Optional so an app build predating them still submits successfully.
    location_source: LocationSource = Form(LocationSource.DEVICE),
    taken_at: datetime | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    embedder=Depends(get_embedder),
    detector=Depends(get_detector),
):
    from src.schemas.sighting import SightingCreate
    from src.services import sighting_service

    data = SightingCreate(
        latitude=latitude,
        longitude=longitude,
        location_source=location_source,
        taken_at=taken_at,
    )
    try:
        sighting = await sighting_service.create_sighting(
            db, current_user.id, file, data, embedder, detector
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    background_tasks.add_task(_run_matching_bg, sighting.id)
    return sighting
