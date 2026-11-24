import logging
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.deps import DbSession
from app.core.rate_limit import RateLimitMiddleware
from app.routers import (
    admin,
    auth,
    billing,
    calendar,
    clinic,
    content,
    dashboard,
    export,
    financial_analytics,
    growth,
    healthcare,
    integrations,
    operations,
    organizations,
    patient_billing,
    patient_portal,
)

logger = logging.getLogger("app")

app = FastAPI(title="DentalPilot AI API", version="1.2.0")


class CatchAllExceptionMiddleware(BaseHTTPMiddleware):
    """Turns an unhandled exception into a normal JSON response instead of a bare 500.

    A handler registered via @app.exception_handler(Exception) is routed by Starlette to
    ServerErrorMiddleware, which sits *outside* CORSMiddleware — its response never gets
    CORS headers added. In a real browser that means any backend bug (anywhere in the app,
    not just Razorpay) surfaces as a CORS failure rather than a proper error response, and
    the frontend shows a misleading "Unable to reach the server" instead of the real error.
    Catching the exception here, *inside* CORSMiddleware (registered before it below), keeps
    the response in the normal middleware flow so CORS headers still apply.
    """

    async def dispatch(self, request: Request, call_next):
        requested_id = request.headers.get("X-Request-ID", "")
        request_id = (
            requested_id
            if 1 <= len(requested_id) <= 128
            and all(char.isalnum() or char in "-_." for char in requested_id)
            else uuid4().hex
        )
        request.state.request_id = request_id
        started_at = time.perf_counter()
        route_name = "/<unmatched>"
        try:
            response = await call_next(request)
            route_name = getattr(request.scope.get("route"), "path", route_name)
        except Exception:
            route_name = getattr(request.scope.get("route"), "path", route_name)
            logger.exception(
                "Unhandled exception request_id=%s method=%s route=%s",
                request_id,
                request.method,
                route_name,
            )
            response = JSONResponse(
                status_code=500,
                content={"statusCode": 500, "message": "An unexpected error occurred. Please try again."},
            )
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "http_request request_id=%s method=%s route=%s status_code=%s duration_ms=%.2f",
            request_id,
            request.method,
            route_name,
            response.status_code,
            duration_ms,
        )
        return response


app.add_middleware(CatchAllExceptionMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition isn't in the browser's default CORS-exposed header safelist —
    # without this, the frontend can't read the download filename from export responses.
    expose_headers=["Content-Disposition"],
)

for router in (
    auth.router,
    clinic.router,
    content.router,
    calendar.router,
    export.router,
    billing.router,
    patient_billing.router,
    dashboard.router,
    admin.router,
    healthcare.router,
    growth.router,
    integrations.router,
    operations.router,
    organizations.router,
    patient_portal.router,
    financial_analytics.router,
):
    app.include_router(router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Reshape errors to match the frontend's ApiErrorResponse contract ({statusCode, message})."""
    return JSONResponse(status_code=exc.status_code, content={"statusCode": exc.status_code, "message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors: dict[str, list[str]] = {}
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"][1:]) or "_"
        errors.setdefault(field, []).append(error["msg"])
    return JSONResponse(
        status_code=422,
        content={"statusCode": 422, "message": "Validation failed.", "errors": errors},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Database readiness check failed.", exc_info=exc)
        raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
    return {"status": "ready", "database": "ok"}
