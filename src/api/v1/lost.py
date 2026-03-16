import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db
from src.schemas.lost import LostDeclarationCreate, LostDeclarationOut, LostDeclarationUpdate
from src.services import lost_service

router = APIRouter()


@router.post("", response_model=LostDeclarationOut, status_code=status.HTTP_201_CREATED)
async def declare_lost(
    data: LostDeclarationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await lost_service.declare_lost(db, current_user.id, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("", response_model=list[LostDeclarationOut])
async def list_my_declarations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await lost_service.get_user_declarations(db, current_user.id)


@router.get("/nearby", response_model=list[LostDeclarationOut])
async def nearby_declarations(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(5.0),
    db: AsyncSession = Depends(get_db),
):
    return await lost_service.get_nearby_declarations(db, lat, lon, radius_km)


@router.get("/{declaration_id}", response_model=LostDeclarationOut)
async def get_declaration(
    declaration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    decl = await lost_service.get_declaration(db, declaration_id)
    if not decl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Declaration not found")
    return decl


@router.put("/{declaration_id}", response_model=LostDeclarationOut)
async def update_declaration(
    declaration_id: uuid.UUID,
    data: LostDeclarationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    decl = await lost_service.get_declaration(db, declaration_id)
    if not decl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Declaration not found")
    try:
        return await lost_service.update_declaration(db, current_user.id, decl, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
