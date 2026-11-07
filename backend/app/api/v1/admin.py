"""Admin monitoring, metrics, and analytics endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.models.geometry import FloorPlan
from app.models.job import ReconstructionJob
from app.models.project import Project
from app.models.user import User
from app.schemas.admin import AdminAnalytics, AdminJob, AdminJobListResponse

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/analytics", response_model=AdminAnalytics)
def get_admin_analytics(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Retrieve real database-backed system metrics matching frontend AdminAnalytics schema.
    Strictly calculates real data without simulated values.
    """
    user_count = db.scalar(select(func.count(User.id))) or 0
    project_count = db.scalar(select(func.count(Project.id)).where(Project.is_archived.is_(False))) or 0

    jobs_running = db.scalar(
        select(func.count(ReconstructionJob.id)).where(
            ReconstructionJob.status.in_(["queued", "processing"])
        )
    ) or 0

    jobs_failed = db.scalar(
        select(func.count(ReconstructionJob.id)).where(ReconstructionJob.status == "failed")
    ) or 0

    jobs_completed = db.scalar(
        select(func.count(ReconstructionJob.id)).where(ReconstructionJob.status == "completed")
    ) or 0

    avg_duration = db.scalar(
        select(func.avg(ReconstructionJob.duration_seconds)).where(
            ReconstructionJob.status == "completed"
        )
    ) or 0.0

    rooms_detected = db.scalar(select(func.sum(Project.rooms_count))) or 0

    avg_confidence = db.scalar(select(func.avg(FloorPlan.quality_confidence))) or 0.0

    # Recent 10 jobs with project name
    recent_query = (
        select(ReconstructionJob, Project.name.label("project_name"))
        .join(Project, ReconstructionJob.project_id == Project.id)
        .order_by(desc(ReconstructionJob.created_at))
        .limit(10)
    )
    job_rows = db.execute(recent_query).all()

    recent_jobs = [
        AdminJob(
            id=job.id,
            projectId=job.project_id,
            projectName=proj_name,
            stage=job.stage,
            status=job.status,
            updatedAt=job.updated_at,
            durationSeconds=job.duration_seconds,
            message=job.message or job.error_message,
        )
        for job, proj_name in job_rows
    ]

    return AdminAnalytics(
        projectCount=project_count,
        userCount=user_count,
        jobsRunning=jobs_running,
        jobsFailed=jobs_failed,
        jobsCompleted=jobs_completed,
        averageProcessingSeconds=round(float(avg_duration), 2),
        reconstructionsCompleted=jobs_completed,
        roomsDetected=int(rooms_detected),
        averageGeometryConfidence=round(float(avg_confidence), 2),
        updatedAt=datetime.now(timezone.utc),
        recentJobs=recent_jobs,
    )


@router.get("/metrics")
def get_admin_metrics(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Aggregate high-level system and storage metrics."""
    from app.models.upload import VideoUpload

    total_storage_bytes = db.scalar(select(func.sum(VideoUpload.file_size_bytes))) or 0
    total_uploads = db.scalar(select(func.count(VideoUpload.id))) or 0

    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "projects": db.scalar(select(func.count(Project.id))) or 0,
        "jobs": {
            "total": db.scalar(select(func.count(ReconstructionJob.id))) or 0,
            "running": db.scalar(select(func.count(ReconstructionJob.id)).where(ReconstructionJob.status.in_(["queued", "processing"]))) or 0,
            "completed": db.scalar(select(func.count(ReconstructionJob.id)).where(ReconstructionJob.status == "completed")) or 0,
            "failed": db.scalar(select(func.count(ReconstructionJob.id)).where(ReconstructionJob.status == "failed")) or 0,
        },
        "storage": {
            "totalUploads": total_uploads,
            "totalVolumeBytes": total_storage_bytes,
        },
    }


@router.get("/jobs", response_model=AdminJobListResponse)
def get_all_jobs(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Paginated list of all background reconstruction jobs with status filters."""
    query = (
        select(ReconstructionJob, Project.name.label("project_name"))
        .join(Project, ReconstructionJob.project_id == Project.id)
    )

    if status_filter:
        query = query.where(ReconstructionJob.status == status_filter)

    total = db.scalar(select(func.count(ReconstructionJob.id))) or 0
    rows = db.execute(query.order_by(desc(ReconstructionJob.created_at)).offset(skip).limit(limit)).all()

    items = [
        AdminJob(
            id=job.id,
            projectId=job.project_id,
            projectName=proj_name,
            stage=job.stage,
            status=job.status,
            updatedAt=job.updated_at,
            durationSeconds=job.duration_seconds,
            message=job.message or job.error_message,
        )
        for job, proj_name in rows
    ]

    return AdminJobListResponse(total=total, items=items)
