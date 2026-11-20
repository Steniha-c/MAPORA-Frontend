"""MAPORA Backend FastAPI Application."""

from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} in [{settings.ENVIRONMENT}] mode.")

    is_testing = os.environ.get("ENVIRONMENT") == "testing" or settings.ENVIRONMENT == "testing"

    if not is_testing:
        # Automatically create tables if using SQLite or fresh database
        Base.metadata.create_all(bind=engine)

        # Ensure added columns exist on existing SQLite databases
        with engine.begin() as conn:
            try:
                cursor = conn.exec_driver_sql("PRAGMA table_info(projects)")
                cols = [row[1] for row in cursor.fetchall()]
                if cols and "input_type" not in cols:
                    conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN input_type VARCHAR(50) DEFAULT 'video'")
            except Exception:
                pass

            try:
                cursor = conn.exec_driver_sql("PRAGMA table_info(reconstruction_jobs)")
                cols = [row[1] for row in cursor.fetchall()]
                if cols and "job_type" not in cols:
                    conn.exec_driver_sql("ALTER TABLE reconstruction_jobs ADD COLUMN job_type VARCHAR(50) DEFAULT 'video'")
            except Exception:
                pass

        # Seed initial administrator account if configured
        db = SessionLocal()
        try:
            admin = AuthService.seed_initial_admin(db)
            if admin:
                logger.info(f"Initial administrator account seeded: {admin.email}")
        finally:
            db.close()

    yield

    logger.info("Shutting down MAPORA backend...")
    if not is_testing:
        engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="MAPORA — AI-Based Indoor Map Generation from a Single Camera. Backend REST API.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# SlowAPI Rate Limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware configured strictly by environment
cors_origin_regex = (
    r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$" if settings.DEBUG else None
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount API routers
# 1. Standard versioned endpoints under /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 2. Mount under /api prefix for proxy compatibility
app.include_router(api_router, prefix="/api")

# 3. Root-level alias router for direct frontend compatibility without /api/v1 prefix
app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "storageBackend": settings.STORAGE_BACKEND,
        "device": settings.DEVICE,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global uncaught exception handler returning structured error JSON."""
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An internal server error occurred. Please contact the administrator."},
    )
