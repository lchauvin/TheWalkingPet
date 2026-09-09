"""Contract checks for rate-limited routes.

slowapi's decorator injects its ``X-RateLimit-*`` headers into a ``response``
parameter whenever the endpoint returns something other than a ``Response``.
When that parameter is missing it raises *after* the handler has already done
its work, turning every successful call into a 500 — and because the suite runs
with ``RATE_LIMIT_ENABLED=false`` (see conftest), the injection path is skipped
and normal tests stay green. These checks run against the route table instead.
"""
import inspect

import pytest


def _limited_endpoints():
    """Every route whose handler carries a @limiter.limit decorator."""
    from src.main import app
    from src.utils.rate_limit import limiter

    found = []
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        name = f"{endpoint.__module__}.{endpoint.__name__}"
        if name in limiter._route_limits or name in limiter._dynamic_route_limits:
            found.append((name, endpoint))
    return found


def test_there_are_rate_limited_routes():
    # Guards the checks below against silently passing on an empty list.
    assert _limited_endpoints(), "expected at least one @limiter.limit route"


@pytest.mark.parametrize("name,endpoint", _limited_endpoints(), ids=lambda v: v if isinstance(v, str) else "")
def test_limited_endpoint_accepts_request_and_response(name, endpoint):
    params = inspect.signature(endpoint).parameters
    assert "request" in params, f"{name} needs a `request` parameter for slowapi"
    assert "response" in params, (
        f"{name} needs a `response: Response` parameter — without it slowapi "
        f"raises while injecting rate-limit headers and the call returns 500"
    )

    from fastapi import Response

    assert params["response"].annotation is Response, (
        f"{name}'s `response` parameter must be annotated `fastapi.Response`"
    )
