"""Test session defaults: the API's per-IP rate limit would otherwise trip on the hundreds of requests the suite sends."""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _relax_rate_limit():
    from fortune.api.main import app
    app.state.limiter.per_minute, app.state.limiter.llm_per_minute = 100000, 100000
    yield
