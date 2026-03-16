import io
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Sighting, Species
from src.schemas.sighting import SightingCreate
from src.storage.image_store import image_store


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

    detection = detector.best_detection(pil_image)
    crop = detection["masked"] if detection else pil_image
    species_detected = _SPECIES_MAP.get(detection["species"]) if detection else None

    embedding = embedder.embed_image(crop)

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
