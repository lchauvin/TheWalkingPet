import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.config import settings
from src.db.models import LostStatus

Latitude = Field(ge=-90, le=90)
Longitude = Field(ge=-180, le=180)


class LostDeclarationCreate(BaseModel):
    pet_id: uuid.UUID
    last_seen_lat: float = Latitude
    last_seen_lon: float = Longitude
    # Capped at the matching bounding box: a wider radius would silently do nothing.
    search_radius_km: float = Field(default=0.5, gt=0, le=settings.max_search_radius_km)
    reward_amount: float | None = Field(default=None, ge=0, le=1_000_000)
    description: str | None = Field(default=None, max_length=2000)


class LostDeclarationUpdate(BaseModel):
    search_radius_km: float | None = Field(default=None, gt=0, le=settings.max_search_radius_km)
    reward_amount: float | None = Field(default=None, ge=0, le=1_000_000)
    description: str | None = Field(default=None, max_length=2000)
    status: LostStatus | None = None


class LostDeclarationOut(BaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    last_seen_lat: float
    last_seen_lon: float
    search_radius_km: float
    reward_amount: float | None
    status: LostStatus
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
