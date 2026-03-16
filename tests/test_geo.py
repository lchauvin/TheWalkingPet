"""Tests for geo utility functions."""
import pytest

from src.utils.geo import bounding_box, haversine_km


def test_haversine_same_point():
    assert haversine_km(48.8566, 2.3522, 48.8566, 2.3522) == pytest.approx(0.0)


def test_haversine_known_distance():
    # Paris to London is approximately 341 km
    paris = (48.8566, 2.3522)
    london = (51.5074, -0.1278)
    dist = haversine_km(*paris, *london)
    assert 330 < dist < 360


def test_bounding_box_shape():
    min_lat, max_lat, min_lon, max_lon = bounding_box(48.8566, 2.3522, 1.0)
    assert min_lat < 48.8566 < max_lat
    assert min_lon < 2.3522 < max_lon


def test_bounding_box_radius():
    # Points just outside the bounding box should fail the haversine check
    lat, lon = 48.8566, 2.3522
    radius = 1.0
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius)
    # Corner points should be further than radius
    corner_dist = haversine_km(lat, lon, min_lat, min_lon)
    assert corner_dist > radius
