"""Upload validation and path safety."""
import io

import pytest
from fastapi import UploadFile

from src.config import settings
from src.storage.image_store import ImageStore

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
JPEG_HEADER = b"\xff\xd8\xff\xe0"


def _upload(data: bytes, content_type: str, filename: str = "photo.png") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        headers={"content-type": content_type},
    )


@pytest.fixture
def store(tmp_path):
    return ImageStore(base_path=str(tmp_path))


@pytest.mark.asyncio
async def test_saves_a_png_under_a_relative_posix_path(store):
    path = await store.save(_upload(PNG_HEADER + b"x" * 100, "image/png"), "pets/abc")
    assert path.startswith("pets/abc/")
    assert path.endswith(".png")
    assert "\\" not in path
    assert store.path_for(path).is_file()


@pytest.mark.asyncio
async def test_rejects_a_disallowed_content_type(store):
    with pytest.raises(ValueError, match="Unsupported image format"):
        await store.save(_upload(b"<html>hi</html>", "text/html", "x.html"))


@pytest.mark.asyncio
async def test_rejects_content_that_is_not_an_image(store):
    # Declared as a PNG, but the bytes are not one.
    with pytest.raises(ValueError, match="does not look like an image"):
        await store.save(_upload(b"not an image at all", "image/png"))


@pytest.mark.asyncio
async def test_rejects_an_empty_upload(store):
    with pytest.raises(ValueError, match="empty"):
        await store.save(_upload(b"", "image/png"))


@pytest.mark.asyncio
async def test_enforces_the_size_limit(store, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0.001)  # ~1 KB
    with pytest.raises(ValueError, match="larger than"):
        await store.save(_upload(PNG_HEADER + b"x" * 5000, "image/png"))


@pytest.mark.asyncio
async def test_partial_file_is_cleaned_up_after_a_size_rejection(store, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0.001)
    with pytest.raises(ValueError):
        await store.save(_upload(PNG_HEADER + b"x" * 5000, "image/png"), "pets/abc")
    assert list(store.base_path.rglob("*.png")) == []


@pytest.mark.asyncio
async def test_client_filename_never_reaches_disk(store):
    path = await store.save(
        _upload(JPEG_HEADER + b"x" * 100, "image/jpeg", "../../evil.jpg"), "pets/abc"
    )
    assert "evil" not in path
    assert ".." not in path


@pytest.mark.parametrize(
    "escape",
    [
        "../../../etc/passwd",
        "/etc/passwd",
        "pets/../../../secret.txt",
        r"..\..\windows\win.ini",
        "pets/abc/../../../../outside.jpg",
    ],
)
def test_a_stored_path_can_never_escape_the_storage_root(store, escape):
    """Either refused outright, or contained — never resolving outside the root."""
    try:
        resolved = store.path_for(escape)
    except ValueError:
        return  # refused, which is the other acceptable outcome
    assert store.base_path in resolved.parents or resolved == store.base_path


def test_legacy_absolute_paths_still_resolve(store):
    # Rows written before migration 007 carried a storage/images prefix.
    resolved = store.path_for("storage/images/pets/abc/x.jpg")
    assert resolved == store.base_path / "pets" / "abc" / "x.jpg"


def test_windows_separators_still_resolve(store):
    resolved = store.path_for(r"storage\images\pets\abc\x.jpg")
    assert resolved == store.base_path / "pets" / "abc" / "x.jpg"
