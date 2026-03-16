"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import settings
from src.dependencies import set_ml_models

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    from src.ml.detector import PetDetector
    from src.ml.embedder import PetEmbedder

    embedder = PetEmbedder(checkpoint_path=settings.model_checkpoint_path)
    detector = PetDetector()
    set_ml_models(embedder, detector)
    logger.info("[Startup] ML models loaded")

    # Background radius expansion scheduler (every hour)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from src.services.radius_expansion import expand_radii

    scheduler = AsyncIOScheduler()
    scheduler.add_job(expand_radii, "interval", hours=1, id="radius_expansion")
    scheduler.start()
    logger.info("[Startup] Scheduler started")

    yield

    # --- Shutdown ---
    scheduler.shutdown(wait=False)
    logger.info("[Shutdown] Scheduler stopped")


app = FastAPI(
    title="TheWalkingPet API",
    version="2.0.0",
    lifespan=lifespan,
)

from src.api.v1.router import router as v1_router  # noqa: E402
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
