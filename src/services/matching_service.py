"""Core matching pipeline:
1. GPS bounding box filter → active lost declarations within radius
2. Species filter
3. pgvector cosine similarity against candidate pet_images
4. Threshold → create Match records
"""
from __future__ import annotations

import logging
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import LostDeclaration, LostStatus, Match, MatchStatus, PetImage, Sighting, Species
from src.utils.geo import bounding_box, haversine_km

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.50


async def find_candidate_declarations(
    db: AsyncSession,
    lat: float,
    lon: float,
    species: Species | None,
) -> list[LostDeclaration]:
    """Find ACTIVE lost declarations whose search radius encompasses the given point."""
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, 10.0)

    stmt = (
        select(LostDeclaration)
        .options(selectinload(LostDeclaration.pet))
        .where(
            LostDeclaration.status == LostStatus.ACTIVE,
            LostDeclaration.last_seen_lat.between(min_lat, max_lat),
            LostDeclaration.last_seen_lon.between(min_lon, max_lon),
        )
    )
    if species:
        from src.db.models import Pet
        stmt = stmt.join(LostDeclaration.pet).where(Pet.species == species)

    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    filtered = [
        decl for decl in candidates
        if haversine_km(lat, lon, decl.last_seen_lat, decl.last_seen_lon) <= decl.search_radius_km
    ]
    logger.info(
        f"[Matching] GPS filter: sighting=({lat:.5f},{lon:.5f}) species={species} "
        f"→ {len(candidates)} bbox candidates, {len(filtered)} within radius"
    )
    for decl in candidates:
        dist = haversine_km(lat, lon, decl.last_seen_lat, decl.last_seen_lon)
        logger.info(
            f"[Matching]   decl={decl.id} pet={decl.pet_id} radius={decl.search_radius_km}km dist={dist:.3f}km {'✓' if dist <= decl.search_radius_km else '✗'}"
        )
    return filtered


async def run_matching(
    db: AsyncSession,
    sighting: Sighting,
) -> list[Match]:
    """Run the full matching pipeline for a newly created sighting."""
    if sighting.embedding is None:
        return []

    candidates = await find_candidate_declarations(
        db, sighting.latitude, sighting.longitude, sighting.species_detected
    )
    if not candidates:
        logger.info(f"[Matching] No candidate declarations for sighting={sighting.id}")
        return []

    pet_ids = [decl.pet_id for decl in candidates]
    decl_by_pet: dict[uuid.UUID, LostDeclaration] = {decl.pet_id: decl for decl in candidates}

    embedding_literal = "[" + ",".join(str(v) for v in sighting.embedding) + "]"
    query_vec = cast(literal(embedding_literal), Vector(256))

    result = await db.execute(
        select(
            PetImage.pet_id,
            (1 - PetImage.embedding.cosine_distance(query_vec)).label("similarity"),
        )
        .where(PetImage.pet_id.in_(pet_ids), PetImage.embedding.isnot(None))
        .order_by(PetImage.embedding.cosine_distance(query_vec))
    )
    rows = result.fetchall()

    best_per_pet: dict[uuid.UUID, float] = {}
    for row in rows:
        pet_id = row.pet_id
        sim = float(row.similarity)
        if pet_id not in best_per_pet or sim > best_per_pet[pet_id]:
            best_per_pet[pet_id] = sim

    logger.info(f"[Matching] Similarity scores: {[f'{pid}: {sim:.3f}' for pid, sim in best_per_pet.items()]}")

    matches = []
    for pet_id, similarity in best_per_pet.items():
        if similarity < SIMILARITY_THRESHOLD:
            logger.info(f"[Matching] pet={pet_id} score={similarity:.3f} below threshold {SIMILARITY_THRESHOLD} — no match")
            continue
        decl = decl_by_pet[pet_id]
        match = Match(
            id=uuid.uuid4(),
            sighting_id=sighting.id,
            lost_declaration_id=decl.id,
            similarity_score=similarity,
            status=MatchStatus.PENDING,
        )
        db.add(match)
        matches.append(match)

    if matches:
        await db.commit()
        for m in matches:
            await db.refresh(m)

    return matches
