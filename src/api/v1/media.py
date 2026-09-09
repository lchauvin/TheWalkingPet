"""Authenticated image delivery.

Replaces the open ``StaticFiles`` mount: pet photos and sighting photos are
personal data attached to a location, so each request is authorised against the
row that owns the file rather than protected by an unguessable path.
"""
from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import LostDeclaration, Match, Pet, PetImage, Sighting
from src.dependencies import get_current_user, get_db
from src.storage.image_store import image_store

router = APIRouter()

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")


async def _may_view(db: AsyncSession, path: str, user_id) -> bool:
    """A user may see their own pets' photos, and sightings tied to them."""
    owns_pet_image = await db.scalar(
        select(
            exists().where(
                PetImage.image_path == path,
                PetImage.pet_id == Pet.id,
                Pet.owner_id == user_id,
            )
        )
    )
    if owns_pet_image:
        return True

    sighting_id = await db.scalar(select(Sighting.id).where(Sighting.image_path == path))
    if sighting_id is None:
        return False

    # The reporter can always see what they submitted.
    reported_it = await db.scalar(
        select(
            exists().where(
                Sighting.id == sighting_id,
                Sighting.reporter_id == user_id,
            )
        )
    )
    if reported_it:
        return True

    # Otherwise only an owner the sighting was matched against.
    return bool(
        await db.scalar(
            select(
                exists().where(
                    Match.sighting_id == sighting_id,
                    Match.lost_declaration_id == LostDeclaration.id,
                    LostDeclaration.pet_id == Pet.id,
                    Pet.owner_id == user_id,
                )
            )
        )
    )


@router.get("/{path:path}")
async def get_media(
    path: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not path or ".." in path:
        raise _NOT_FOUND

    if not await _may_view(db, path, current_user.id):
        # Deliberately 404 rather than 403: whether a given image exists is
        # itself information about someone else's pet.
        raise _NOT_FOUND

    try:
        file_path = image_store.path_for(path)
    except ValueError:
        raise _NOT_FOUND

    if not file_path.is_file():
        raise _NOT_FOUND

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )
