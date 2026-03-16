import uuid
from datetime import datetime

from pydantic import BaseModel

from src.db.models import Species


class SightingCreate(BaseModel):
    latitude: float
    longitude: float


class SightingOut(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID | None
    image_path: str
    latitude: float
    longitude: float
    species_detected: Species | None
    created_at: datetime

    model_config = {"from_attributes": True}
