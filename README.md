# TheWalkingPet v2

Find lost pets by photo. Someone photographs a stray; the backend segments the
animal, embeds it, and compares that embedding against pets reported missing
nearby. The owner gets a push notification with a similarity score and, once
they confirm the match, the sighting location.

- **Backend** — FastAPI + PostgreSQL/pgvector, YOLOv8m-seg for detection and
  DINOv2 ViT-L/14 for 1024-dimensional embeddings.
- **Mobile** — Flutter (Android), Riverpod, go_router, Firebase Cloud Messaging.

---

## Requirements

| | |
|---|---|
| Python | 3.11 |
| PostgreSQL | 16 with the `vector` extension (`pgvector/pgvector:pg16`) |
| Flutter | 3.11+ |
| Docker | for the containerised stacks |

Both models run server-side. Inference is CPU-viable but slow; a CUDA GPU is
strongly recommended for anything beyond local testing.

---

## Local development

```bash
cp .env.example .env          # then edit JWT_SECRET_KEY at minimum
docker compose up -d db
alembic upgrade head
uvicorn src.main:app --reload --port 8010
```

Or run the whole stack in containers:

```bash
docker compose up -d --build
```

The API is then on <http://localhost:8010>, with interactive docs at `/docs`
(disabled automatically when `ENVIRONMENT=production`).

### The mobile app

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_HOST=http://10.0.2.2:8010   # 10.0.2.2 = host, from the Android emulator
```

`API_HOST` sets the compiled-in default. It can also be changed at runtime from
the in-app **Settings** screen, which stays reachable while signed out —
a stale address would otherwise make login impossible to recover from.

---

## Production deployment

```bash
cp .env.example .env.prod                 # fill in real secrets
mkdir -p secrets
cp /path/to/firebase-key.json secrets/firebase-credentials.json

docker compose -f docker-compose.prod.yml up -d --build
```

The production stack differs from development in ways that matter:

| | Development | Production |
|---|---|---|
| Source | bind-mounted, `--reload` | baked into the image |
| Postgres | published on `127.0.0.1:9876` | reachable only on the compose network |
| TLS | none | Caddy, automatic Let's Encrypt |
| Migrations | run by hand | `migrate` service, before the app starts |
| Scheduler | in-process | its own single-instance service |
| Rate limits | per-process counters | shared through Redis |
| Firebase key | file in the repo root | Docker secret |
| API docs | `/docs` | disabled |

Set `DOMAIN` and `ACME_EMAIL` in `.env.prod`; Caddy provisions the certificate
on first boot, which needs ports 80 and 443 reachable from the internet.

**The app refuses to start with `ENVIRONMENT=production` while any example
credential is still in place** — the default JWT secret, the default database
password, or `DEBUG=true`. Generate a real secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Sizing

Each uvicorn worker loads its own copy of DINOv2 ViT-L/14, about 1.2 GB
resident. Budget roughly **1.5 GB per `WEB_CONCURRENCY` step** and set it
deliberately; the default is 2.

Model weights are baked into the image at build time
(`scripts/prefetch_models.py`), so a container start needs no network and no
warm-up download.

### Health endpoints

| Path | Meaning |
|---|---|
| `/health` | Liveness — the process is up. |
| `/health/ready` | Readiness — the database answers *and* both models are resident. Returns 503 otherwise. |

Point your orchestrator's readiness probe at `/health/ready`; the Docker
`HEALTHCHECK` already does.

### Signing a release build

```bash
keytool -genkey -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload

cp mobile/android/key.properties.example mobile/android/key.properties
# fill in the passwords and the keystore path
```

`key.properties` is gitignored. Without it the release build is *unsigned* and
says so — it no longer silently falls back to debug keys. **Keep the keystore
safe: losing it means you can never publish an update to the same listing.**

```bash
cd mobile
flutter build appbundle --release --dart-define=API_HOST=https://your.domain
```

---

## Architecture notes

### Matching

A new sighting runs through `src/services/matching_service.py`:

1. A bounding box at `MAX_SEARCH_RADIUS_KM` (10 km) narrows candidate
   declarations, then an exact haversine check keeps those whose own
   `search_radius_km` actually reaches the sighting.
2. Species from YOLO filters further, when it detected one.
3. pgvector cosine similarity runs against the pet's aggregate embedding,
   falling back to per-image maximum where no aggregate exists.
4. The final score is `0.7 × image similarity + 0.3 × distance score`, where
   distance decays as `exp(-km / 3)`. Above 0.70 a `Match` row is created and
   the owner is notified.

A declaration's search radius widens on its own as time passes — 0.5 km on day
0, 1 km after a day, 2 km after three, 5 km after a week
(`src/services/radius_expansion.py`).

### Embedding dimension

`EMBEDDING_DIM` must equal the width of the `vector(N)` columns *and* the
embedder's output. DINOv2 ViT-L/14 produces **1024**. Changing the model means a
migration to re-type every vector column plus a full re-embed
(`scripts/reembed_all.py`) — the stored vectors are meaningless in another
model's space.

### Images

Photos are served by an authenticated route (`GET /api/v1/media/{path}`), not a
public static mount. A request is authorised against the row that owns the
file: you may fetch your own pets' photos, sightings you reported, and sightings
matched against one of your pets. Everything else is a 404 — whether a given
image exists is itself information about someone else's pet.

Stored paths are relative and POSIX (`pets/<id>/file.jpg`). Migration 007
normalises rows written before that.

### Sessions

Access tokens last 30 minutes; refresh tokens are recorded server-side in
`refresh_tokens` and **rotate on every use**. Presenting an already-rotated
token is treated as a stolen-token replay and revokes every outstanding session
for that user. `POST /api/v1/auth/logout` revokes the presented token, or all of
them when the body is omitted.

### Background jobs

`scripts/run_scheduler.py` runs radius expansion and refresh-token cleanup in a
**single dedicated process**. Every API container sets `RUN_SCHEDULER=false`; a
second scheduler would double-expand every search radius.

---

## Testing

```bash
pip install -e ".[dev]"
pytest -q
```

The suite needs no database, GPU or network. CI additionally applies every
migration up, down and up again against a real pgvector instance, builds the
Docker image, and runs `flutter analyze` and `flutter test`.

---

## Operations

```bash
alembic upgrade head            # apply migrations
alembic downgrade -1            # roll back one

python -m scripts.reembed_all   # re-embed every pet image after a model change
python -m scripts.seed_db       # development fixtures
```

Logs go to stdout; set `LOG_JSON=true` in a deployment so a log shipper can
parse them.
