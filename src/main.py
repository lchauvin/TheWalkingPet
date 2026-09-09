"""FastAPI application entry point."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from src.utils.logging_config import configure_logging

configure_logging()

from fastapi import FastAPI, Request, status  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.middleware import SlowAPIMiddleware  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.config import settings  # noqa: E402
from src.dependencies import ml_models, set_ml_models  # noqa: E402
from src.utils.rate_limit import limiter  # noqa: E402

logger = logging.getLogger(__name__)

_DEFAULT_JWT = "change_me_to_a_random_secret_key_at_least_32_chars"
_DEFAULT_DB_PASSWORD = "twp_secret"


def _validate_runtime_security() -> None:
    """Refuse to start a production process with development credentials."""
    problems: list[str] = []

    if settings.jwt_secret_key == _DEFAULT_JWT:
        problems.append("JWT_SECRET_KEY is still the example value")
    elif len(settings.jwt_secret_key) < 32:
        problems.append("JWT_SECRET_KEY is shorter than 32 characters")

    if settings.postgres_password == _DEFAULT_DB_PASSWORD:
        problems.append("POSTGRES_PASSWORD is still the example value")

    if settings.debug:
        problems.append("DEBUG is enabled")

    if not problems:
        return

    if settings.is_production:
        raise RuntimeError(
            "Refusing to start in production: " + "; ".join(problems)
        )
    for problem in problems:
        logger.warning("[Security] %s — fix before deploying", problem)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_runtime_security()

    from src.ml.detector import PetDetector
    from src.ml.embedder import PetEmbedder

    embedder = PetEmbedder()
    detector = PetDetector(model_name=settings.yolo_model)
    set_ml_models(embedder, detector)
    logger.info("[Startup] ML models loaded")

    scheduler = None
    if settings.run_scheduler:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        from src.services.maintenance import purge_expired_refresh_tokens
        from src.services.radius_expansion import expand_radii

        scheduler = AsyncIOScheduler()
        scheduler.add_job(expand_radii, "interval", hours=1, id="radius_expansion")
        scheduler.add_job(
            purge_expired_refresh_tokens, "interval", hours=24, id="purge_refresh_tokens"
        )
        scheduler.start()
        logger.info("[Startup] Scheduler started")
    else:
        logger.info("[Startup] Scheduler disabled (RUN_SCHEDULER=false)")

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("[Shutdown] Scheduler stopped")


app = FastAPI(
    title="TheWalkingPet API",
    version="2.0.0",
    lifespan=lifespan,
    # The interactive docs describe every endpoint and schema; keep them off in
    # production unless deliberately switched back on.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please wait and try again."},
    )


app.add_middleware(SlowAPIMiddleware)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


from src.api.v1.router import router as v1_router  # noqa: E402

app.include_router(v1_router, prefix="/api/v1")

os.makedirs(settings.storage_path, exist_ok=True)


@app.get("/health", tags=["ops"])
async def health():
    """Liveness only — the process is up and serving."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["ops"])
async def readiness():
    """Readiness — refuses traffic until the database and models can serve a request."""
    from src.db.session import AsyncSessionLocal

    checks = {"database": False, "embedder": False, "detector": False}

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("[Health] Database check failed")

    checks["embedder"] = ml_models.embedder is not None
    checks["detector"] = ml_models.detector is not None

    ready = all(checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )
