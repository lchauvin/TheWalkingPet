"""Request-validation boundaries that the API relies on."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.config import settings
from src.db.models import LocationSource
from src.schemas.lost import LostDeclarationCreate, LostDeclarationUpdate
from src.schemas.sighting import SightingCreate
from src.schemas.user import UserRegister


def test_short_password_is_rejected():
    with pytest.raises(ValidationError):
        UserRegister(email="a@b.com", password="short")


def test_password_at_the_minimum_is_accepted():
    data = UserRegister(email="a@b.com", password="x" * settings.password_min_length)
    assert data.email == "a@b.com"


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_out_of_range_coordinates_are_rejected(lat, lon):
    with pytest.raises(ValidationError):
        SightingCreate(latitude=lat, longitude=lon)


def test_valid_coordinates_are_accepted():
    s = SightingCreate(latitude=48.8566, longitude=2.3522)
    assert s.latitude == pytest.approx(48.8566)


def test_search_radius_cannot_exceed_the_matching_cap():
    # A wider radius than the candidate bounding box would silently do nothing.
    with pytest.raises(ValidationError):
        LostDeclarationCreate(
            pet_id=uuid.uuid4(),
            last_seen_lat=0.0,
            last_seen_lon=0.0,
            search_radius_km=settings.max_search_radius_km + 1,
        )


def test_search_radius_must_be_positive():
    with pytest.raises(ValidationError):
        LostDeclarationUpdate(search_radius_km=0)


def test_negative_reward_is_rejected():
    with pytest.raises(ValidationError):
        LostDeclarationUpdate(reward_amount=-1)


def test_declaration_description_is_carried_on_the_schema():
    data = LostDeclarationCreate(
        pet_id=uuid.uuid4(),
        last_seen_lat=1.0,
        last_seen_lon=2.0,
        description="Ginger tabby, blue collar",
    )
    assert data.description == "Ginger tabby, blue collar"

# ------------------------------------------------- sighting location provenance


def test_location_defaults_to_the_device_when_unspecified():
    # An app build predating these fields sends neither; it must still validate,
    # and its sighting is device-located, which is what those builds do.
    s = SightingCreate(latitude=48.8566, longitude=2.3522)
    assert s.location_source is LocationSource.DEVICE
    assert s.taken_at is None


def test_exif_source_is_accepted():
    s = SightingCreate(
        latitude=48.8566, longitude=2.3522, location_source=LocationSource.EXIF
    )
    assert s.location_source is LocationSource.EXIF


def test_an_unknown_location_source_is_rejected():
    with pytest.raises(ValidationError):
        SightingCreate(latitude=0.0, longitude=0.0, location_source="GUESSED")


def test_a_past_capture_time_is_kept():
    taken = datetime.now(timezone.utc) - timedelta(days=3)
    s = SightingCreate(latitude=0.0, longitude=0.0, taken_at=taken)
    assert s.taken_at == taken


def test_a_future_capture_time_is_discarded():
    # A wrong phone clock must not be able to make an old photo look fresh.
    s = SightingCreate(
        latitude=0.0,
        longitude=0.0,
        taken_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    assert s.taken_at is None


def test_a_capture_time_within_clock_skew_is_kept():
    taken = datetime.now(timezone.utc) + timedelta(minutes=2)
    s = SightingCreate(latitude=0.0, longitude=0.0, taken_at=taken)
    assert s.taken_at == taken


def test_a_naive_capture_time_is_treated_as_utc():
    naive = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
    s = SightingCreate(latitude=0.0, longitude=0.0, taken_at=naive)
    assert s.taken_at is not None
    assert s.taken_at.tzinfo is not None
