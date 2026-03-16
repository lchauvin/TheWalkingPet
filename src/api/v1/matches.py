import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dependencies import get_current_user, get_db
from src.db.models import LostDeclaration, Match, MatchStatus, Pet, Sighting
from src.schemas.match import MatchConfirmOut, MatchOut

router = APIRouter()


async def _get_match_for_owner(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> Match:
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    decl = await db.get(LostDeclaration, match.lost_declaration_id)
    pet = await db.get(Pet, decl.pet_id) if decl else None
    if not pet or pet.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your match")

    return match


@router.get("", response_model=list[MatchOut])
async def list_matches(
    status_filter: MatchStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = (
        select(Match)
        .join(LostDeclaration, Match.lost_declaration_id == LostDeclaration.id)
        .join(Pet, LostDeclaration.pet_id == Pet.id)
        .where(Pet.owner_id == current_user.id)
        .options(selectinload(Match.sighting))
    )
    if status_filter:
        stmt = stmt.where(Match.status == status_filter)

    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


@router.post("/{match_id}/confirm", response_model=MatchConfirmOut)
async def confirm_match(
    match_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    match = await _get_match_for_owner(db, match_id, current_user.id)
    match.status = MatchStatus.CONFIRMED
    await db.commit()
    await db.refresh(match)

    sighting = await db.get(Sighting, match.sighting_id)
    return MatchConfirmOut(
        id=match.id,
        status=match.status,
        similarity_score=match.similarity_score,
        sighting_lat=sighting.latitude if sighting else None,
        sighting_lon=sighting.longitude if sighting else None,
    )


@router.post("/{match_id}/reject", response_model=MatchOut)
async def reject_match(
    match_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    match = await _get_match_for_owner(db, match_id, current_user.id)
    match.status = MatchStatus.REJECTED
    await db.commit()
    await db.refresh(match)
    return match
