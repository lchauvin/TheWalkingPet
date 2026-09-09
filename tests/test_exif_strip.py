"""GPS must not survive into a stored image.

The app stopped re-encoding picked photos so their EXIF lives long enough to
be read, so originals now arrive with the photographer's coordinates in them.
Stored images are served over the media route, so those tags have to go.
"""
import io

import piexif
import pytest
from fastapi import UploadFile
from PIL import Image

from src.storage.image_store import ImageStore


# 48.8584 N, 2.2945 E as EXIF rationals ((deg, 1), (min, 1), (sec, 100)).
_LAT = ((48, 1), (51, 1), (3024, 100))
_LON = ((2, 1), (17, 1), (4020, 100))


def _jpeg_with_gps(size=(64, 48)) -> bytes:
    """A real JPEG carrying GPS and orientation tags."""
    exif = {
        "0th": {piexif.ImageIFD.Orientation: 1},
        "Exif": {},
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: _LAT,
            piexif.GPSIFD.GPSLongitudeRef: b"E",
            piexif.GPSIFD.GPSLongitude: _LON,
        },
        "1st": {},
        "thumbnail": None,
    }
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 90, 60)).save(buf, "JPEG", exif=piexif.dump(exif))
    return buf.getvalue()


def _upload(data: bytes, content_type="image/jpeg", filename="photo.jpg") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        headers={"content-type": content_type},
    )


@pytest.fixture
def store(tmp_path):
    return ImageStore(base_path=str(tmp_path))


def test_the_fixture_really_carries_gps():
    # Guards every assertion below from passing on an image that never had GPS.
    assert piexif.load(_jpeg_with_gps())["GPS"]


@pytest.mark.asyncio
async def test_gps_is_stripped_from_a_stored_jpeg(store):
    path = await store.save(_upload(_jpeg_with_gps()), "sightings")
    assert not piexif.load(str(store.path_for(path)))["GPS"]


@pytest.mark.asyncio
async def test_stripping_leaves_the_picture_itself_alone(store):
    original = _jpeg_with_gps(size=(96, 72))
    path = await store.save(_upload(original), "sightings")

    with Image.open(store.path_for(path)) as stored:
        assert stored.size == (96, 72)
    # piexif rewrites only the metadata segment, so the entropy-coded image
    # data is byte-identical — no generational loss on every upload.
    with Image.open(io.BytesIO(original)) as before:
        with Image.open(store.path_for(path)) as after:
            assert before.tobytes() == after.tobytes()


@pytest.mark.asyncio
async def test_non_gps_tags_are_kept(store):
    path = await store.save(_upload(_jpeg_with_gps()), "sightings")
    exif = piexif.load(str(store.path_for(path)))
    assert exif["0th"].get(piexif.ImageIFD.Orientation) == 1


@pytest.mark.asyncio
async def test_a_jpeg_without_exif_is_stored_unchanged(store):
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buf, "JPEG")
    raw = buf.getvalue()

    path = await store.save(_upload(raw), "sightings")
    assert store.path_for(path).read_bytes() == raw


@pytest.mark.asyncio
async def test_stripping_can_be_turned_off(store):
    path = await store.save(_upload(_jpeg_with_gps()), "sightings", strip_gps=False)
    assert piexif.load(str(store.path_for(path)))["GPS"]
