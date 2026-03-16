import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import LostDeclaration, LostStatus, Pet
from src.schemas.lost import LostDeclarationCreate, LostDeclarationUpdate
from src.utils.geo import haversine_km


async def declare_lost(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: LostDeclarationCreate,
) -> LostDeclaration:
    pet = await db.get(Pet, data.pet_id)
    if not pet:
        raise LookupError("Pet not found")
    if pet.owner_id != user_id:
        raise PermissionError("You do not own this pet")

    decl = LostDeclaration(
        id=uuid.uuid4(),
        pet_id=data.pet_id,
        last_seen_lat=data.last_seen_lat,
        last_seen_lon=data.last_seen_lon,
        search_radius_km=data.search_radius_km or 0.5,
        reward_amount=data.reward_amount,
        status=LostStatus.ACTIVE,
    )
    db.add(decl)
    await db.commit()
    await db.refresh(decl)
    return decl


async def get_declaration(
    db: AsyncSession, declaration_id: uuid.UUID
) -> LostDeclaration | None:
    return await db.get(LostDeclaration, declaration_id)


async def get_user_declarations(
    db: AsyncSession, user_id: uuid.UUID
) -> list[LostDeclaration]:
    result = await db.execute(
        select(LostDeclaration)
        .join(Pet, LostDeclaration.pet_id == Pet.id)
        .where(Pet.owner_id == user_id)
    )
    return list(result.scalars().all())


async def get_nearby_declarations(
    db: AsyncSession, lat: float, lon: float, radius_km: float
) -> list[LostDeclaration]:
    result = await db.execute(
        select(LostDeclaration).where(LostDeclaration.status == LostStatus.ACTIVE)
    )
    declarations = list(result.scalars().all())
    return [
        d for d in declarations
        if haversine_km(lat, lon, d.last_seen_lat, d.last_seen_lon) <= radius_km
    ]


async def update_declaration(
    db: AsyncSession,
    user_id: uuid.UUID,
    decl: LostDeclaration,
    data: LostDeclarationUpdate,
) -> LostDeclaration:
    pet = await db.get(Pet, decl.pet_id)
    if not pet or pet.owner_id != user_id:
        raise PermissionError("You do not own this declaration")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(decl, field, value)
    await db.commit()
    await db.refresh(decl)
    return decl
