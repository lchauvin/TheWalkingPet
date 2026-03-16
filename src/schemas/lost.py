import uuid
from datetime import datetime

from pydantic import BaseModel

from src.db.models import LostStatus


class LostDeclarationCreate(BaseModel):
    pet_id: uuid.UUID
    last_seen_lat: float
    last_seen_lon: float
    search_radius_km: float = 0.5
    reward_amount: float | None = None
    description: str | None = None


class LostDeclarationUpdate(BaseModel):
    search_radius_km: float | None = None
    reward_amount: float | None = None
    description: str | None = None
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
