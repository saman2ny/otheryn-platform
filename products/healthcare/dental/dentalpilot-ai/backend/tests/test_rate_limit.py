from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware, SlidingWindowRateLimiter


def test_sliding_window_allows_limit_then_blocks():
    limiter = SlidingWindowRateLimiter(limit=3, window_seconds=60)
    assert limiter.allow("k", now=0)
    assert limiter.allow("k", now=1)
    assert limiter.allow("k", now=2)
    assert not limiter.allow("k", now=3)
    assert limiter.allow("k", now=61)  # window has expired


def test_rate_limit_middleware_blocks_auth_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "production")
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    async def login():
        return JSONResponse({"ok": True})

    app.add_middleware(RateLimitMiddleware)
    client = TestClient(app)
    for _ in range(10):
        assert client.post("/api/v1/auth/login").status_code == 200
    assert client.post("/api/v1/auth/login").status_code == 429


def test_rate_limit_middleware_disabled_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "development")
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    async def login():
        return JSONResponse({"ok": True})

    app.add_middleware(RateLimitMiddleware)
    client = TestClient(app)
    for _ in range(50):
        assert client.post("/api/v1/auth/login").status_code == 200