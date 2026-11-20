import os

import pytest

os.environ["API_SECRET_KEY"] = "test_super_secret_key"
# Outside Lambda the rate limiter uses Redis; tests use in-memory storage instead.
os.environ.setdefault("REDIS_URL", "memory://")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from core.security import limiter

    limiter.reset()
    yield
