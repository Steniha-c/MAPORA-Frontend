from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_authorized_project, get_current_user, get_db
from app.models.job import ReconstructionJob
from app.models.project import Project
from app.models.user import User
from app.schemas.job import JobCreate, JobRead
from app.services.job_service import JobService
from app.services.audit_service import AuditService

router = APIRouter(tags=["Reconstruction Jobs"])


@router.post(
    "/projects/{project_id}/jobs",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    project_id: str,
    payload: Optional[JobCreate] = None,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start an asynchronous AI spatial reconstruction job on a project's uploaded video."""
    upload_id = payload.upload_id if payload else None
    try:
        job = JobService.create_and_dispatch_job(db, project, current_user, upload_id=upload_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db,
        action="start_reconstruction_job",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Started job {job.id}",
    )
    return job


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details, stage, and duration of a processing job."""
    job = db.scalar(select(ReconstructionJob).where(ReconstructionJob.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    # Authorization
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an ongoing reconstruction job."""
    job = db.scalar(select(ReconstructionJob).where(ReconstructionJob.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    cancelled = JobService.cancel_job(db, job)
    AuditService.log(
        db,
        action="cancel_reconstruction_job",
        user_id=current_user.id,
        project_id=job.project_id,
        details=f"Cancelled job {job.id}",
    )
    return cancelled


@router.post("/jobs/{job_id}/retry", response_model=JobRead)
def retry_job_by_id(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed reconstruction job."""
    job = db.scalar(select(ReconstructionJob).where(ReconstructionJob.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    project = db.scalar(select(Project).where(Project.id == job.project_id))
    if not project or (current_user.role != "admin" and project.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return JobService.retry_job(db, project, current_user)
