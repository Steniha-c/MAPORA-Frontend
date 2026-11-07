"""MAPORA Backend FastAPI Application."""

from contextlib import asynccontextmanager
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

    # Automatically create tables if using SQLite or fresh database
    Base.metadata.create_all(bind=engine)

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
# 1. Standard versioned endpoints under /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 2. Root-level alias router for direct frontend compatibility without /api/v1 prefix
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
