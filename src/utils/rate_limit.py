"""Rate limiting.

Counters live in-process by default, which is correct for a single worker. Set
``RATE_LIMIT_STORAGE_URI`` to a Redis URL to share them across workers — without
it, N workers means N times the configured allowance.
"""
from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from src.config import settings

logger = logging.getLogger(__name__)


def _identify(request: Request) -> str:
    """Key on the authenticated user where possible, else the client address.

    Behind a proxy, ``get_remote_address`` reads the socket peer, so the app must
    be run with ``--proxy-headers`` and a trusted forwarded-for list for the
    address to mean anything.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        # The raw token is a stable per-session key without decoding or trusting it.
        return f"tok:{hash(auth[7:])}"
    return get_remote_address(request) or "anonymous"


_kwargs: dict = {
    "key_func": _identify,
    "enabled": settings.rate_limit_enabled,
    "headers_enabled": True,
}
if settings.rate_limit_storage_uri:
    _kwargs["storage_uri"] = settings.rate_limit_storage_uri

limiter = Limiter(**_kwargs)

if settings.rate_limit_enabled and not settings.rate_limit_storage_uri:
    logger.info(
        "[RateLimit] Using in-process counters. Set RATE_LIMIT_STORAGE_URI "
        "to share limits across workers."
    )
