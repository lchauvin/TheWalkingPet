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
    sighting_image_path: str | None = None
    sighting_lat: float | None = None
    sighting_lon: float | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_match(cls, match) -> "MatchOut":
        return cls(
            id=match.id,
            sighting_id=match.sighting_id,
            lost_declaration_id=match.lost_declaration_id,
            similarity_score=match.similarity_score,
            status=match.status,
            created_at=match.created_at,
            sighting_image_path=match.sighting.image_path if match.sighting else None,
            sighting_lat=match.sighting.latitude if match.sighting else None,
            sighting_lon=match.sighting.longitude if match.sighting else None,
        )


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
