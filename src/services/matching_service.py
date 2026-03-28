"""Core matching pipeline:
1. GPS bounding box filter → active lost declarations within radius
2. Species filter
3. pgvector cosine similarity against pet aggregate embedding (Phase 3)
   Falls back to per-image max similarity if pet.embedding is NULL
4. Combined score (image similarity + distance) → threshold → create Match records
"""
from __future__ import annotations

import logging
import math
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.db.models import LostDeclaration, LostStatus, Match, MatchStatus, Pet, PetImage, Sighting, Species
from src.utils.geo import bounding_box, haversine_km

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.70

# Combined score weights
IMAGE_WEIGHT = 0.7
DISTANCE_WEIGHT = 0.3

# Exponential decay scale: score = exp(-dist / scale)
# At 0km → 1.0, at 3km → 0.37, at 5km → 0.19, at 10km → 0.04
DISTANCE_SCALE_KM = 3.0


def _distance_score(dist_km: float) -> float:
    return math.exp(-dist_km / DISTANCE_SCALE_KM)


def _make_query_vec(embedding: list[float]):
    """Cast a Python embedding list to a pgvector literal."""
    vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
    return cast(literal(vec_str), Vector(settings.embedding_dim))


async def _get_confirmed_positions(
    db: AsyncSession,
    declaration_ids: list[uuid.UUID],
) -> dict[uuid.UUID, tuple[float, float]]:
    """Return latest confirmed sighting position per declaration."""
    if not declaration_ids:
        return {}

    result = await db.execute(
        select(
            Match.lost_declaration_id,
            Sighting.latitude,
            Sighting.longitude,
        )
        .join(Match, Match.sighting_id == Sighting.id)
        .where(
            Match.lost_declaration_id.in_(declaration_ids),
            Match.status == MatchStatus.CONFIRMED,
        )
        .order_by(Match.lost_declaration_id, Sighting.created_at.desc())
        .distinct(Match.lost_declaration_id)
    )
    return {
        row.lost_declaration_id: (row.latitude, row.longitude)
        for row in result.fetchall()
    }


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
        logger.debug(
            f"[Matching]   decl={decl.id} pet={decl.pet_id} "
            f"radius={decl.search_radius_km}km dist={dist:.3f}km "
            f"{'✓' if dist <= decl.search_radius_km else '✗'}"
        )
    return filtered


async def _image_similarity_fallback(
    db: AsyncSession,
    pet_ids: list[uuid.UUID],
    query_vec,
) -> dict[uuid.UUID, float]:
    """Per-image max-similarity fallback for pets lacking an aggregate embedding."""
    result = await db.execute(
        select(
            PetImage.pet_id,
            (1 - PetImage.embedding.cosine_distance(query_vec)).label("similarity"),
        )
        .where(PetImage.pet_id.in_(pet_ids), PetImage.embedding.isnot(None))
        .order_by(PetImage.embedding.cosine_distance(query_vec))
    )
    best: dict[uuid.UUID, float] = {}
    for row in result.fetchall():
        pid = row.pet_id
        sim = float(row.similarity)
        if pid not in best or sim > best[pid]:
            best[pid] = sim
    return best


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
    query_vec = _make_query_vec(sighting.embedding)

    # Phase 3: prefer aggregate pet embedding; fall back to per-image max
    similarity_scores: dict[uuid.UUID, float] = {}
    agg_rows = await db.execute(
        select(
            Pet.id,
            (1 - Pet.embedding.cosine_distance(query_vec)).label("similarity"),
        )
        .where(Pet.id.in_(pet_ids), Pet.embedding.isnot(None))
    )
    pets_with_agg_ids: set[uuid.UUID] = set()
    for row in agg_rows.fetchall():
        similarity_scores[row.id] = float(row.similarity)
        pets_with_agg_ids.add(row.id)
    pets_without_agg = [pid for pid in pet_ids if pid not in pets_with_agg_ids]

    if pets_without_agg:
        fallback = await _image_similarity_fallback(db, pets_without_agg, query_vec)
        similarity_scores.update(fallback)

    existing_rows = await db.execute(
        select(Match.lost_declaration_id).where(Match.sighting_id == sighting.id)
    )
    existing_decl_ids = {row.lost_declaration_id for row in existing_rows.fetchall()}
    confirmed_positions = await _get_confirmed_positions(
        db, [decl.id for decl in candidates]
    )

    matches = []
    for pet_id, image_sim in similarity_scores.items():
        decl = decl_by_pet[pet_id]
        if decl.id in existing_decl_ids:
            logger.debug(f"[Matching] Skipping duplicate candidate for declaration={decl.id}")
            continue

        if decl.id in confirmed_positions:
            ref_lat, ref_lon = confirmed_positions[decl.id]
            ref_source = "last confirmed sighting"
        else:
            ref_lat, ref_lon = decl.last_seen_lat, decl.last_seen_lon
            ref_source = "last seen"
        dist_km = haversine_km(sighting.latitude, sighting.longitude, ref_lat, ref_lon)
        dist_s = _distance_score(dist_km)
        combined = IMAGE_WEIGHT * image_sim + DISTANCE_WEIGHT * dist_s

        logger.debug(
            f"[Matching] pet={pet_id} image={image_sim:.1%} | "
            f"dist={dist_km:.2f}km from {ref_source} → dist_score={dist_s:.1%} | "
            f"combined={combined:.1%}"
        )

        if combined < SIMILARITY_THRESHOLD:
            logger.debug(f"[Matching] ✗ Below threshold {SIMILARITY_THRESHOLD:.0%} — skipped")
            continue

        match = Match(
            id=uuid.uuid4(),
            sighting_id=sighting.id,
            lost_declaration_id=decl.id,
            similarity_score=combined,
            status=MatchStatus.PENDING,
        )
        db.add(match)
        matches.append(match)
        logger.debug(
            f"[Matching] ✓ MATCH created: score={combined:.1%} "
            f"(image={image_sim:.1%}, dist={dist_km:.2f}km)"
        )

    if matches:
        try:
            await db.commit()
        except IntegrityError:
            # Another concurrent matcher may have inserted the same pair first.
            await db.rollback()
            logger.info(f"[Matching] Duplicate match insert race for sighting={sighting.id}; skipped")
            return []
        for m in matches:
            await db.refresh(m)
    else:
        logger.info(f"[Matching] No matches for sighting={sighting.id}")

    return matches
