import asyncio
import io
import logging
import math
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Sighting, Species
from src.schemas.sighting import SightingCreate
from src.storage.image_store import image_store

logger = logging.getLogger(__name__)

_SPECIES_MAP = {"CAT": Species.CAT, "DOG": Species.DOG}


async def create_sighting(
    db: AsyncSession,
    reporter_id: uuid.UUID,
    file: UploadFile,
    data: SightingCreate,
    embedder,
    detector,
) -> Sighting:
    from PIL import Image

    path = await image_store.save(file, subfolder="sightings")

    await file.seek(0)
    content = await file.read()
    pil_image = Image.open(io.BytesIO(content)).convert("RGB")

    detection = await asyncio.to_thread(detector.best_detection, pil_image)
    if detection:
        crop = detection["masked"]
        species_detected = _SPECIES_MAP.get(detection["species"])
        logger.info(
            f"[Sighting] YOLO detected {detection['species']} "
            f"conf={detection['confidence']:.2f} "
            f"bbox={detection['bbox']} "
            f"original={pil_image.size} crop={crop.size}"
        )
    else:
        crop = pil_image
        species_detected = None
        logger.warning(
            f"[Sighting] No pet detected — using full image {pil_image.size}"
        )

    embedding = await asyncio.to_thread(embedder.embed_image, crop)
    norm = math.sqrt(sum(v * v for v in embedding))
    logger.info(f"[Sighting] Embedding dim={len(embedding)} norm={norm:.4f}")

    sighting = Sighting(
        id=uuid.uuid4(),
        reporter_id=reporter_id,
        image_path=path,
        embedding=embedding,
        latitude=data.latitude,
        longitude=data.longitude,
        species_detected=species_detected,
    )
    db.add(sighting)
    await db.commit()
    await db.refresh(sighting)
    return sighting
