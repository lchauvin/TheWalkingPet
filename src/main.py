"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s: %(message)s",
)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.dependencies import set_ml_models

logger = logging.getLogger(__name__)


def _validate_runtime_security() -> None:
    """Fail fast on obvious insecure production config."""
    is_local_db = settings.postgres_host in {"localhost", "127.0.0.1"}
    using_default_jwt = settings.jwt_secret_key == "change_me_to_a_random_secret_key_at_least_32_chars"
    if not settings.debug and not is_local_db and using_default_jwt:
        raise RuntimeError("Refusing to start with default JWT secret in non-local environment")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_runtime_security()

    # --- Startup ---
    from src.ml.detector import PetDetector
    from src.ml.embedder import PetEmbedder

    embedder = PetEmbedder(checkpoint_path=settings.model_checkpoint_path)
    detector = PetDetector(model_name=settings.yolo_model)
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

import os  # noqa: E402
os.makedirs(settings.storage_path, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")


@app.get("/health")
async def health():
    return {"status": "ok"}
