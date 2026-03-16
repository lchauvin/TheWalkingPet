import uuid
from datetime import datetime

from pydantic import BaseModel

from src.db.models import Species


class PetCreate(BaseModel):
    name: str
    species: Species
    breed: str | None = None
    description: str | None = None
    is_microchipped: bool = False
    latitude: float | None = None
    longitude: float | None = None


class PetUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    description: str | None = None
    is_microchipped: bool | None = None
    latitude: float | None = None
    longitude: float | None = None


class PetImageOut(BaseModel):
    id: uuid.UUID
    image_path: str
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PetOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    species: Species
    breed: str | None
    description: str | None
    is_microchipped: bool
    latitude: float | None
    longitude: float | None
    created_at: datetime
    images: list[PetImageOut] = []

    model_config = {"from_attributes": True}
