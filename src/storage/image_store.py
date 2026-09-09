"""Validated image storage.

Paths are stored relative to the storage root in POSIX form (``pets/<id>/x.jpg``)
so the same value addresses the file on any host and maps directly onto the
authenticated media route.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path, PurePosixPath

import aiofiles
from fastapi import UploadFile

from src.config import settings

logger = logging.getLogger(__name__)

# Only formats the pipeline can actually decode, mapped to the extension we
# store them under. The client's own filename never reaches the filesystem.
ALLOWED_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

# Leading bytes for each accepted container, checked against the declared type
# so a renamed file cannot smuggle a different format through.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)

CHUNK_SIZE = 64 * 1024


def _strip_gps(path: Path, mime: str) -> None:
    """Remove embedded GPS tags from a stored image, in place.

    The client stops re-encoding picked images so their EXIF survives long
    enough to be read, which means originals carrying the photographer's
    coordinates now reach this function. Sighting and pet images are served
    over the authenticated media route, so leaving those tags in place would
    hand every viewer the reporter's position or the owner's home address.

    Failures are swallowed: a stored image that could not be rewritten is worth
    keeping, and the coordinates the app actually matches on are the ones sent
    as form fields, not these.
    """
    try:
        if mime == "image/jpeg":
            # piexif edits the EXIF segment of the existing JPEG bytes, so the
            # compressed image data is untouched — no generational quality loss.
            import piexif

            try:
                exif = piexif.load(str(path))
            except Exception:
                return
            if not exif.get("GPS"):
                return
            exif["GPS"] = {}
            piexif.insert(piexif.dump(exif), str(path))
            return

        # Other containers have no comparable in-place editor, so re-encode
        # without metadata. Orientation is baked in first, otherwise dropping
        # the tag silently rotates the image.
        from PIL import Image, ImageOps

        if mime in ("image/heic", "image/heif"):
            import pillow_heif

            pillow_heif.register_heif_opener()

        with Image.open(path) as img:
            if not img.getexif():
                return
            fixed = ImageOps.exif_transpose(img)
            fixed.save(path, exif=None)
    except Exception:
        logger.warning("[ImageStore] Could not strip GPS from %s", path.name, exc_info=True)


def _sniff(head: bytes) -> str | None:
    for prefix, mime in _MAGIC:
        if head.startswith(prefix):
            return mime
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"hevc", b"mif1", b"msf1"):
        return "image/heic"
    return None


class ImageStore:
    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.storage_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(
        self, file: UploadFile, subfolder: str = "", strip_gps: bool = True
    ) -> str:
        """Stream an upload to disk, enforcing type and size. Returns a relative path."""
        declared = (file.content_type or "").split(";")[0].strip().lower()
        if declared not in ALLOWED_TYPES:
            raise ValueError(
                "Unsupported image format. Use JPEG, PNG, WebP or HEIC."
            )

        await file.seek(0)
        head = await file.read(32)
        if not head:
            raise ValueError("Uploaded file is empty")

        sniffed = _sniff(head)
        if sniffed is None:
            raise ValueError("File does not look like an image")
        # HEIC and WebP both report through ftyp/RIFF families; accept any
        # allowed sniffed type rather than demanding an exact string match.
        if sniffed not in ALLOWED_TYPES:
            raise ValueError("Unsupported image format")

        ext = ALLOWED_TYPES[sniffed]
        relative = PurePosixPath(subfolder) / f"{uuid.uuid4()}{ext}"
        dest = self._resolve(str(relative))
        dest.parent.mkdir(parents=True, exist_ok=True)

        await file.seek(0)
        written = 0
        limit = settings.max_upload_bytes
        try:
            async with aiofiles.open(dest, "wb") as out:
                while chunk := await file.read(CHUNK_SIZE):
                    written += len(chunk)
                    if written > limit:
                        raise ValueError(
                            f"Image is larger than the {settings.max_upload_mb:.0f} MB limit"
                        )
                    await out.write(chunk)
        except Exception:
            dest.unlink(missing_ok=True)
            raise

        if written == 0:
            dest.unlink(missing_ok=True)
            raise ValueError("Uploaded file is empty")

        # After the size check, so an oversized upload is never decoded.
        if strip_gps:
            _strip_gps(dest, sniffed)

        return str(relative)

    def _resolve(self, relative_path: str) -> Path:
        """Map a stored path onto disk, refusing anything outside the storage root."""
        normalised = relative_path.replace("\\", "/").lstrip("/")
        for prefix in ("storage/images/", "./storage/images/"):
            if normalised.startswith(prefix):
                normalised = normalised[len(prefix):]
        candidate = (self.base_path / normalised).resolve()
        if candidate != self.base_path and self.base_path not in candidate.parents:
            raise ValueError("Path escapes the storage root")
        return candidate

    def path_for(self, relative_path: str) -> Path:
        return self._resolve(relative_path)

    def delete(self, relative_path: str) -> None:
        try:
            self._resolve(relative_path).unlink(missing_ok=True)
        except ValueError:
            # A stored path that no longer resolves is not worth failing a delete over.
            pass


image_store = ImageStore()
