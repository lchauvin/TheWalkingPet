import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Pet, PetImage
from src.schemas.pet import PetCreate, PetUpdate
from src.storage.image_store import image_store


async def create_pet(db: AsyncSession, owner_id: uuid.UUID, data: PetCreate) -> Pet:
    pet = Pet(id=uuid.uuid4(), owner_id=owner_id, **data.model_dump())
    db.add(pet)
    await db.commit()
    return await get_pet(db, pet.id)


async def get_pet(db: AsyncSession, pet_id: uuid.UUID) -> Pet | None:
    result = await db.execute(
        select(Pet).options(selectinload(Pet.images)).where(Pet.id == pet_id)
    )
    return result.scalar_one_or_none()


async def get_user_pets(db: AsyncSession, owner_id: uuid.UUID) -> list[Pet]:
    result = await db.execute(
        select(Pet).options(selectinload(Pet.images)).where(Pet.owner_id == owner_id)
    )
    return list(result.scalars().all())


async def update_pet(db: AsyncSession, pet: Pet, data: PetUpdate) -> Pet:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(pet, field, value)
    await db.commit()
    await db.refresh(pet)
    return pet


async def delete_pet(db: AsyncSession, pet: Pet) -> None:
    await db.delete(pet)
    await db.commit()


MAX_IMAGES_PER_PET = 10


async def delete_pet_image(
    db: AsyncSession,
    pet: Pet,
    image_id: uuid.UUID,
) -> None:
    image = next((img for img in pet.images if img.id == image_id), None)
    if not image:
        raise LookupError("Image not found")
    image_store.delete(image.image_path)
    await db.delete(image)
    await db.commit()


async def add_pet_image(
    db: AsyncSession,
    pet_id: uuid.UUID,
    file: UploadFile,
    embedder,
    detector,
    is_primary: bool = False,
) -> PetImage:
    import io
    from PIL import Image

    pet = await get_pet(db, pet_id)
    if pet and len(pet.images) >= MAX_IMAGES_PER_PET:
        raise ValueError(f"Maximum of {MAX_IMAGES_PER_PET} images per pet reached")

    path = await image_store.save(file, subfolder=f"pets/{pet_id}")

    await file.seek(0)
    content = await file.read()
    pil_image = Image.open(io.BytesIO(content)).convert("RGB")

    detection = detector.best_detection(pil_image)
    crop = detection["masked"] if detection else pil_image

    embedding = embedder.embed_image(crop)

    pet_image = PetImage(
        id=uuid.uuid4(),
        pet_id=pet_id,
        image_path=path,
        embedding=embedding,
        is_primary=is_primary,
    )
    db.add(pet_image)
    await db.commit()
    await db.refresh(pet_image)
    return pet_image
