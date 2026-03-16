import uuid
from datetime import datetime

from pydantic import BaseModel

from src.db.models import MatchStatus


class MatchOut(BaseModel):
    id: uuid.UUID
    sighting_id: uuid.UUID
    lost_declaration_id: uuid.UUID
    similarity_score: float
    status: MatchStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchWithDetails(MatchOut):
    sighting_lat: float | None = None
    sighting_lon: float | None = None
    sighting_image_path: str | None = None
    pet_name: str | None = None


class MatchConfirmOut(BaseModel):
    id: uuid.UUID
    status: MatchStatus
    similarity_score: float
    sighting_lat: float | None = None
    sighting_lon: float | None = None

    model_config = {"from_attributes": True}
