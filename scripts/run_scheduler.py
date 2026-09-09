"""Standalone background-job process.

Runs exactly one instance per deployment. Kept out of the API containers so the
API can scale horizontally without every extra worker re-expanding the same
search radii — and so this process never loads the ML models it does not use.
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.logging_config import configure_logging  # noqa: E402

configure_logging()

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: E402

from src.services.maintenance import purge_expired_refresh_tokens  # noqa: E402
from src.services.radius_expansion import expand_radii  # noqa: E402

logger = logging.getLogger("scheduler")


async def main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(expand_radii, "interval", hours=1, id="radius_expansion")
    scheduler.add_job(
        purge_expired_refresh_tokens, "interval", hours=24, id="purge_refresh_tokens"
    )
    scheduler.start()
    logger.info("[Scheduler] Started: radius_expansion (1h), purge_refresh_tokens (24h)")

    stop = asyncio.Event()
    try:
        await stop.wait()
    finally:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
