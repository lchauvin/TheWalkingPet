import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, field_validator

from src.db.models import LocationSource, Species

# Phone clocks drift; anything beyond this is not drift but a bad value.
CLOCK_SKEW_TOLERANCE = timedelta(minutes=10)


class SightingCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    # Both default so that an app build predating this field keeps working:
    # it sends neither, and the sighting is recorded as device-located.
    location_source: LocationSource = LocationSource.DEVICE
    taken_at: datetime | None = None

    @field_validator("taken_at")
    @classmethod
    def _drop_future_timestamps(cls, v: datetime | None) -> datetime | None:
        """Discard a capture time in the future instead of trusting it.

        This value is client-supplied and drives the staleness of a sighting,
        so a wrong clock must not be able to make an old photo look fresh.
        """
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > datetime.now(timezone.utc) + CLOCK_SKEW_TOLERANCE:
            return None
        return v


class SightingOut(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID | None
    image_path: str
    latitude: float
    longitude: float
    species_detected: Species | None
    location_source: LocationSource
    taken_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
