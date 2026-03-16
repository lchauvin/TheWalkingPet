import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db, get_detector, get_embedder
from src.schemas.pet import PetCreate, PetImageOut, PetOut, PetUpdate
from src.services import pet_service

router = APIRouter()


@router.post("", response_model=PetOut, status_code=status.HTTP_201_CREATED)
async def create_pet(
    data: PetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await pet_service.create_pet(db, current_user.id, data)


@router.get("", response_model=list[PetOut])
async def list_pets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await pet_service.get_user_pets(db, current_user.id)


@router.get("/{pet_id}", response_model=PetOut)
async def get_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pet = await pet_service.get_pet(db, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return pet


@router.put("/{pet_id}", response_model=PetOut)
async def update_pet(
    pet_id: uuid.UUID,
    data: PetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pet = await pet_service.get_pet(db, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return await pet_service.update_pet(db, pet, data)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pet = await pet_service.get_pet(db, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    await pet_service.delete_pet(db, pet)


@router.post("/{pet_id}/images", response_model=PetImageOut, status_code=status.HTTP_201_CREATED)
async def upload_pet_image(
    pet_id: uuid.UUID,
    file: UploadFile,
    is_primary: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    embedder=Depends(get_embedder),
    detector=Depends(get_detector),
):
    pet = await pet_service.get_pet(db, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return await pet_service.add_pet_image(db, pet_id, file, embedder, detector, is_primary)
