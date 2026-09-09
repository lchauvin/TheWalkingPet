# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder: install dependencies against the CPU torch index.
#
# `pip install .` ignores pyproject's [tool.uv.sources], which would otherwise
# resolve the default CUDA wheel (~2.5 GB) into a container with no GPU runtime.
# PIP_EXTRA_INDEX_URL below applies to every pip call in this stage, so the
# project install cannot re-resolve torch from PyPI and undo the CPU pin.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN pip install torch torchvision \
 && pip install .

# ---------------------------------------------------------------------------
# Model cache: bake the weights in so a cold start needs no network.
# ---------------------------------------------------------------------------
FROM builder AS models

ENV PATH="/opt/venv/bin:$PATH" \
    TORCH_HOME=/opt/ml-cache/torch \
    YOLO_CONFIG_DIR=/opt/ml-cache/ultralytics

# ultralytics imports cv2 at module load; these are the same OpenCV native
# libs the runtime stage installs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/prefetch_models.py ./scripts/prefetch_models.py
RUN mkdir -p /opt/ml-cache/ultralytics \
 && cd /opt/ml-cache && python /app/scripts/prefetch_models.py

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=models --chown=appuser:appuser /opt/ml-cache /opt/ml-cache

WORKDIR /app
COPY --chown=appuser:appuser pyproject.toml alembic.ini ./
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser scripts ./scripts

RUN mkdir -p /app/storage/images && chown -R appuser:appuser /app/storage

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TORCH_HOME=/opt/ml-cache/torch \
    YOLO_CONFIG_DIR=/opt/ml-cache/ultralytics \
    STORAGE_PATH=/app/storage/images \
    YOLO_MODEL=/opt/ml-cache/yolov8m-seg.pt \
    PORT=8010 \
    WEB_CONCURRENCY=2

USER appuser
EXPOSE 8010

# Readiness, not liveness: the container is only healthy once the database
# answers and both models are resident.
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health/ready" || exit 1

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*'"]
