"""Background radius expansion for lost declarations.

Search radius grows automatically as time passes without the pet being found:
  Day 0–1:  0.5 km  (initial)
  Day 1–3:  1.0 km
  Day 3–7:  2.0 km
  Day 7+:   5.0 km
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from src.db.models import LostDeclaration, LostStatus

logger = logging.getLogger(__name__)

RADIUS_SCHEDULE = [
    (7, 5.0),
    (3, 2.0),
    (1, 1.0),
    (0, 0.5),
]


def _target_radius(days_elapsed: float) -> float:
    for min_days, radius in RADIUS_SCHEDULE:
        if days_elapsed >= min_days:
            return radius
    return 0.5


async def expand_radii() -> None:
    """Check all ACTIVE declarations and expand search radius if due."""
    from src.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LostDeclaration).where(LostDeclaration.status == LostStatus.ACTIVE)
        )
        declarations = list(result.scalars().all())

        updated = 0
        now = datetime.now(timezone.utc)
        for decl in declarations:
            created = decl.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days_elapsed = (now - created).total_seconds() / 86400
            target = _target_radius(days_elapsed)

            if target > decl.search_radius_km:
                logger.info(
                    f"[RadiusExpansion] declaration={decl.id} "
                    f"{decl.search_radius_km}km → {target}km (day {days_elapsed:.1f})"
                )
                decl.search_radius_km = target
                updated += 1

        if updated:
            await db.commit()
            logger.info(f"[RadiusExpansion] updated {updated} declaration(s)")
