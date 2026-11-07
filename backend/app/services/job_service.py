"""Reconstruction job management service."""

from datetime import datetime, timezone
import threading
from typing import Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.job import ReconstructionJob
from app.models.project import Project
from app.models.upload import VideoUpload
from app.models.user import User
from app.schemas.job import ProcessingStatus
from app.workers.tasks import process_reconstruction_task
from app.core.logging import logger


class JobService:
    """Service managing background job lifecycle, cancellation, and status polling."""

    @staticmethod
    def create_and_dispatch_job(
        db: Session,
        project: Project,
        user: User,
        upload_id: Optional[str] = None,
    ) -> ReconstructionJob:
        # Check if an existing job is actively processing
        existing = db.scalar(
            select(ReconstructionJob).where(
                ReconstructionJob.project_id == project.id,
                ReconstructionJob.status.in_(["queued", "processing"]),
            )
        )
        if existing:
            return existing

        # If upload_id not provided, pick latest upload
        if not upload_id:
            latest_upload = db.scalar(
                select(VideoUpload)
                .where(VideoUpload.project_id == project.id)
                .order_by(desc(VideoUpload.created_at))
            )
            if not latest_upload:
                raise ValueError("Cannot start reconstruction job without an uploaded video.")
            upload_id = latest_upload.id

        job = ReconstructionJob(
            project_id=project.id,
            user_id=user.id,
            upload_id=upload_id,
            stage="queued",
            status="queued",
            progress=0.0,
            message="Job queued for processing...",
            retry_count=0,
        )
        db.add(job)
        project.status = "Processing"
        db.commit()
        db.refresh(job)

        # Dispatch to Celery background worker
        try:
            task = process_reconstruction_task.delay(job.id)
            job.celery_task_id = task.id
            db.commit()
            db.refresh(job)
        except Exception as e:
            logger.warning(
                f"Celery broker unreachable ({e}). Running processing task in background thread for local development."
            )
            # Resilient background thread fallback for local dev when Redis is not started
            def run_sync():
                process_reconstruction_task(job.id)

            t = threading.Thread(target=run_sync, daemon=True)
            t.start()

        return job

    @staticmethod
    def get_latest_job_status(db: Session, project: Project) -> ProcessingStatus:
        """Return the latest ProcessingStatus for polling by frontend."""
        job = db.scalar(
            select(ReconstructionJob)
            .where(ReconstructionJob.project_id == project.id)
            .order_by(desc(ReconstructionJob.created_at))
        )

        if not job:
            return ProcessingStatus(
                projectId=project.id,
                stage="unknown",
                status="unknown",
                progress=0.0,
                message="No processing job found for this project.",
                updatedAt=project.updated_at,
            )

        return ProcessingStatus(
            projectId=project.id,
            stage=job.stage,
            status=job.status,
            progress=job.progress,
            message=job.message or job.error_message,
            updatedAt=job.updated_at,
        )

    @staticmethod
    def cancel_job(db: Session, job: ReconstructionJob) -> ReconstructionJob:
        if job.status in ["completed", "failed", "cancelled"]:
            return job

        job.status = "cancelled"
        job.message = "Job cancelled by user."
        job.completed_at = datetime.now(timezone.utc)

        project = db.scalar(select(Project).where(Project.id == job.project_id))
        if project:
            project.status = "Needs attention"

        if job.celery_task_id:
            try:
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
            except Exception as e:
                logger.warning(f"Failed to revoke celery task {job.celery_task_id}: {e}")

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def retry_job(db: Session, project: Project, user: User) -> ReconstructionJob:
        """Retry a failed or stalled processing job."""
        latest_job = db.scalar(
            select(ReconstructionJob)
            .where(ReconstructionJob.project_id == project.id)
            .order_by(desc(ReconstructionJob.created_at))
        )

        upload_id = latest_job.upload_id if latest_job else None
        return JobService.create_and_dispatch_job(db, project, user, upload_id=upload_id)
