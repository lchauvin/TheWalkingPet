from fastapi import APIRouter

from src.api.v1 import auth, lost, matches, pets, sightings

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(pets.router, prefix="/pets", tags=["pets"])
router.include_router(lost.router, prefix="/lost-declarations", tags=["lost"])
router.include_router(sightings.router, prefix="/sightings", tags=["sightings"])
router.include_router(matches.router, prefix="/matches", tags=["matches"])
