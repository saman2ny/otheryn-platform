import threading
import time
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import settings

_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/patient-portal/login",
    "/api/v1/patient-portal/invitations/accept",
}


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        auth_limit: int = 10,
        global_limit: int = 100,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.auth_limiter = SlidingWindowRateLimiter(auth_limit, window_seconds)
        self.global_limiter = SlidingWindowRateLimiter(global_limit, window_seconds)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only enforce in production; development/test keep zero-friction local use.
        if settings.app_environment == "production":
            path = request.url.path
            forwarded = request.headers.get("x-forwarded-for")
            client = request.client.host if request.client else "unknown"
            ip = forwarded.split(",")[0].strip() if forwarded else client
            limiter = self.auth_limiter if path in _AUTH_PATHS else self.global_limiter
            if not limiter.allow(f"{ip}:{path}"):
                return JSONResponse(
                    status_code=429,
                    content={
                        "statusCode": 429,
                        "message": "Too many requests. Please try again later.",
                    },
                )
        return await call_next(request)