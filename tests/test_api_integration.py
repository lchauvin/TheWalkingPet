"""End-to-end API tests against a real database.

Skipped unless ``TWP_TEST_DATABASE=1`` and a migrated Postgres is reachable, so
``pytest`` still runs on a clean checkout. CI sets it against a pgvector service.

    docker run -d --name twp_test -e POSTGRES_USER=twp -e POSTGRES_PASSWORD=test_pw \\
      -e POSTGRES_DB=thewalkingpet -p 15432:5432 pgvector/pgvector:pg16
    POSTGRES_PORT=15432 POSTGRES_PASSWORD=test_pw alembic upgrade head
    TWP_TEST_DATABASE=1 POSTGRES_PORT=15432 POSTGRES_PASSWORD=test_pw pytest tests/test_api_integration.py
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TWP_TEST_DATABASE") != "1",
    reason="Set TWP_TEST_DATABASE=1 with a migrated Postgres to run these",
)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    import httpx

    from src.db.session import engine
    from src.dependencies import set_ml_models
    from src.main import app

    # The lifespan is deliberately not run: it would load DINOv2 (~5 s) per test
    # and start the scheduler. None of these endpoints reach the models — the
    # readiness probe only checks that they are set.
    set_ml_models(object(), object())

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        # Each test runs on its own event loop, and asyncpg connections are
        # bound to the loop that opened them. Without this the pool hands the
        # next test a connection belonging to a closed loop.
        await engine.dispose()


PASSWORD = "a-good-long-password"


async def _register_and_login(client) -> tuple[str, dict]:
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    return email, body


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# --------------------------------------------------------------------------- auth


async def test_register_rejects_a_short_password(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": f"x-{uuid.uuid4().hex[:8]}@example.com", "password": "short"},
    )
    assert r.status_code == 422


async def test_register_is_idempotent_on_conflict(client):
    email, _ = await _register_and_login(client)
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 409


async def test_me_returns_the_authenticated_user(client):
    email, tokens = await _register_and_login(client)
    r = await client.get("/api/v1/auth/me", headers=_auth(tokens))
    assert r.status_code == 200
    assert r.json()["email"] == email


async def test_refresh_rotates_and_invalidates_the_old_token(client):
    _, tokens = await _register_and_login(client)
    old = tokens["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old})
    assert r.status_code == 200
    new = r.json()["refresh_token"]
    assert new != old

    # Replaying the retired token must fail...
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": old})).status_code == 401
    # ...and must take the whole family down with it.
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": new})).status_code == 401


async def test_logout_revokes_the_refresh_token(client):
    _, tokens = await _register_and_login(client)
    r = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_auth(tokens),
    )
    assert r.status_code == 204

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


# ------------------------------------------------------------------- authorisation


async def test_nearby_declarations_require_authentication(client):
    r = await client.get("/api/v1/lost-declarations/nearby?lat=48.85&lon=2.35")
    assert r.status_code in (401, 403)


async def test_nearby_declarations_work_when_authenticated(client):
    _, tokens = await _register_and_login(client)
    r = await client.get(
        "/api/v1/lost-declarations/nearby?lat=48.85&lon=2.35", headers=_auth(tokens)
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_out_of_range_coordinates_are_refused(client):
    _, tokens = await _register_and_login(client)
    r = await client.get(
        "/api/v1/lost-declarations/nearby?lat=999&lon=2.35", headers=_auth(tokens)
    )
    assert r.status_code == 422


async def test_media_requires_authentication(client):
    r = await client.get("/api/v1/media/pets/anything/x.jpg")
    assert r.status_code in (401, 403)


async def test_media_hides_files_the_caller_may_not_see(client):
    _, tokens = await _register_and_login(client)
    r = await client.get("/api/v1/media/pets/anything/x.jpg", headers=_auth(tokens))
    # 404 rather than 403: existence is itself information about someone's pet.
    assert r.status_code == 404


async def test_a_user_cannot_read_another_users_pet(client):
    _, owner = await _register_and_login(client)
    r = await client.post("/api/v1/pets", json={"name": "Mia", "species": "CAT"}, headers=_auth(owner))
    pet_id = r.json()["id"]

    _, stranger = await _register_and_login(client)
    r = await client.get(f"/api/v1/pets/{pet_id}", headers=_auth(stranger))
    assert r.status_code == 404


# ----------------------------------------------------------------------- lost pets


async def test_declaring_a_pet_lost_requires_a_photo(client):
    _, tokens = await _register_and_login(client)
    r = await client.post("/api/v1/pets", json={"name": "Mia", "species": "CAT"}, headers=_auth(tokens))
    pet_id = r.json()["id"]

    r = await client.post(
        "/api/v1/lost-declarations",
        json={"pet_id": pet_id, "last_seen_lat": 48.85, "last_seen_lon": 2.35},
        headers=_auth(tokens),
    )
    assert r.status_code == 422
    assert "photo" in r.json()["detail"].lower()


async def test_search_radius_beyond_the_matching_cap_is_refused(client):
    from src.config import settings

    _, tokens = await _register_and_login(client)
    r = await client.post("/api/v1/pets", json={"name": "Mia", "species": "CAT"}, headers=_auth(tokens))
    pet_id = r.json()["id"]

    r = await client.post(
        "/api/v1/lost-declarations",
        json={
            "pet_id": pet_id,
            "last_seen_lat": 48.85,
            "last_seen_lon": 2.35,
            "search_radius_km": settings.max_search_radius_km + 100,
        },
        headers=_auth(tokens),
    )
    assert r.status_code == 422


# ------------------------------------------------------------------------- ops


async def test_readiness_reports_each_dependency(client):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    checks = r.json()["checks"]
    assert checks["database"] and checks["embedder"] and checks["detector"]
