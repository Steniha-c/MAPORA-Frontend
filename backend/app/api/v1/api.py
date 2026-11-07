"""Version 1 API router aggregator."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, exports, floor_plan, jobs, projects, uploads

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(uploads.router)
api_router.include_router(jobs.router)
api_router.include_router(floor_plan.router)
api_router.include_router(exports.router)
api_router.include_router(admin.router)
