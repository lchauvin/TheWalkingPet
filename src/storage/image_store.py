import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from src.config import settings


class ImageStore:
    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile, subfolder: str = "") -> str:
        dest_dir = self.base_path / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(file.filename or "image.jpg").suffix.lower() or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        dest = dest_dir / filename

        async with aiofiles.open(dest, "wb") as f:
            content = await file.read()
            await f.write(content)

        return str(dest)

    def delete(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()


image_store = ImageStore()
