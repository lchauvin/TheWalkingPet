"""Regenerate the EXIF fixtures used by test/photo_metadata_test.dart.

The tests read real JPEG bytes rather than a stubbed tag map, because the parts
that break in practice — GPS rationals, and the hemisphere refs that decide a
coordinate's sign — only exist in a real file.

    python mobile/tool/make_exif_fixtures.py

Requires piexif and pillow, both already backend dependencies.
"""
from pathlib import Path

import piexif
from PIL import Image

FIXTURES = Path(__file__).resolve().parent.parent / "test" / "fixtures"


def _rationals(degrees: int, minutes: int, seconds: float):
    """EXIF stores a coordinate as degrees, minutes, seconds — each a rational."""
    return ((degrees, 1), (minutes, 1), (int(round(seconds * 100)), 100))


def make(name: str, gps=None, taken: str | None = None, size=(48, 36)) -> None:
    exif: dict = {
        "0th": {piexif.ImageIFD.Orientation: 1},
        "Exif": {},
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    if gps is not None:
        lat_ref, lat, lon_ref, lon = gps
        exif["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef: lat_ref.encode(),
            piexif.GPSIFD.GPSLatitude: _rationals(*lat),
            piexif.GPSIFD.GPSLongitudeRef: lon_ref.encode(),
            piexif.GPSIFD.GPSLongitude: _rationals(*lon),
        }

    if taken is not None:
        exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = taken.encode()

    path = FIXTURES / name
    Image.new("RGB", size, (130, 110, 80)).save(
        path, "JPEG", exif=piexif.dump(exif)
    )
    print(f"wrote {path}")


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)

    # Arc de Triomphe — 48.8584 N, 2.2945 E. Both signs positive.
    make(
        "gps_north_east.jpg",
        gps=("N", (48, 51, 30.24), "E", (2, 17, 40.2)),
        taken="2026:03:14 09:30:00",
    )
    # Sydney Opera House — 33.8568 S, 151.2153 E. Negative latitude.
    make("gps_south_east.jpg", gps=("S", (33, 51, 24.48), "E", (151, 12, 55.08)))
    # Machu Picchu — 13.1631 S, 72.5450 W. Both negative.
    make("gps_south_west.jpg", gps=("S", (13, 9, 47.16), "W", (72, 32, 42.0)))
    # A capture time but no location: the device-fallback path.
    make("no_gps.jpg", taken="2026:01:02 18:45:10")
    # Nothing to read at all.
    make("no_exif_at_all.jpg")


if __name__ == "__main__":
    main()
