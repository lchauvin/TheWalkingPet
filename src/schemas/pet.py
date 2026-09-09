import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.db.models import Species


class PetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    species: Species
    breed: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_microchipped: bool = False
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    breed: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_microchipped: bool | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


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
