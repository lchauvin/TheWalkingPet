"""Re-compute all existing embeddings using the new MegaDescriptor model.

Run after migrating to schema 003/004:

    python -m scripts.reembed_all

This script:
1. Re-embeds all PetImage rows using MegaDescriptor + TTA
2. Re-embeds all Sighting rows using MegaDescriptor (single-pass)
3. Recomputes the aggregate Pet.embedding for every pet
"""
from __future__ import annotations

import asyncio
import io
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run with `python scripts/reembed_all.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.db.models import Pet, PetImage, Sighting
from src.ml.detector import PetDetector
from src.ml.embedder import PetEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _load_image(path: str) -> Image.Image | None:
    # DB paths may already include the storage prefix (e.g. storage/images/pets/...)
    # Try the path as-is relative to project root first, then prepend storage_path.
    project_root = Path(__file__).resolve().parents[1]
    candidates = [
        project_root / path,
        Path(settings.storage_path) / path,
    ]
    for full_path in candidates:
        if full_path.exists():
            try:
                return Image.open(full_path).convert("RGB")
            except Exception as e:
                logger.warning(f"Failed to open {full_path}: {e}")
                return None
    logger.warning(f"Image not found: {path}")
    return None


def _aggregate_embedding(embeddings: list[list[float]]) -> list[float] | None:
    if not embeddings:
        return None
    arr = np.array(embeddings, dtype=np.float32)
    mean = arr.mean(axis=0)
    norm = np.linalg.norm(mean)
    return (mean / norm).tolist() if norm > 0 else mean.tolist()


async def reembed_pet_images(
    session: AsyncSession, embedder: PetEmbedder, detector: PetDetector
) -> None:
    result = await session.execute(select(PetImage))
    images = list(result.scalars().all())
    logger.info(f"Re-embedding {len(images)} pet images...")

    for i, pet_image in enumerate(images, 1):
        pil = _load_image(pet_image.image_path)
        if pil is None:
            continue
        detection = detector.best_detection(pil)
        crop = detection["masked"] if detection else pil
        pet_image.embedding = embedder.embed_image_tta(crop)
        if i % 10 == 0:
            await session.commit()
            logger.info(f"  {i}/{len(images)} pet images done")

    await session.commit()
    logger.info("Pet image re-embedding complete.")


async def reembed_sightings(session: AsyncSession, embedder: PetEmbedder, detector: PetDetector) -> None:
    result = await session.execute(select(Sighting))
    sightings = list(result.scalars().all())
    logger.info(f"Re-embedding {len(sightings)} sightings...")

    for i, sighting in enumerate(sightings, 1):
        pil = _load_image(sighting.image_path)
        if pil is None:
            continue
        detection = detector.best_detection(pil)
        crop = detection["masked"] if detection else pil
        sighting.embedding = embedder.embed_image(crop)
        if i % 10 == 0:
            await session.commit()
            logger.info(f"  {i}/{len(sightings)} sightings done")

    await session.commit()
    logger.info("Sighting re-embedding complete.")


async def update_pet_aggregates(session: AsyncSession) -> None:
    result = await session.execute(select(Pet))
    pets = list(result.scalars().all())
    logger.info(f"Updating aggregate embeddings for {len(pets)} pets...")

    for pet in pets:
        emb_result = await session.execute(
            select(PetImage.embedding).where(
                PetImage.pet_id == pet.id,
                PetImage.embedding.isnot(None),
            )
        )
        embeddings = [row.embedding for row in emb_result.fetchall()]
        pet.embedding = _aggregate_embedding(embeddings)

    await session.commit()
    logger.info("Pet aggregate embedding update complete.")


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    embedder = PetEmbedder()
    detector = PetDetector(model_name=settings.yolo_model)

    async with async_session() as session:
        await reembed_pet_images(session, embedder, detector)
        await reembed_sightings(session, embedder, detector)
        await update_pet_aggregates(session)

    await engine.dispose()
    logger.info("All done.")


if __name__ == "__main__":
    asyncio.run(main())
