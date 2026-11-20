"""Reconstruction job management service."""

from datetime import datetime, timezone
import socket
import threading
from typing import Optional
from urllib.parse import urlparse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import ReconstructionJob
from app.models.project import Project
from app.models.upload import VideoUpload, ImageUpload
from app.models.user import User
from app.schemas.job import ProcessingStatus
from app.workers.tasks import process_reconstruction_task, process_image_reconstruction_task
from app.core.logging import logger


def _is_celery_broker_reachable(broker_url: str, timeout: float = 0.2) -> bool:
    """Fast probe to check whether Celery broker (Redis/RabbitMQ) is actively listening."""
    try:
        parsed = urlparse(broker_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class JobService:
    """Service managing background job lifecycle, cancellation, and status polling."""

    @staticmethod
    def create_and_dispatch_job(
        db: Session,
        project: Project,
        user: User,
        upload_id: Optional[str] = None,
        job_type: str = "video",
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

        if job_type == "photo":
            images = list(db.scalars(select(ImageUpload).where(ImageUpload.project_id == project.id)).all())
            if not images:
                raise ValueError("Cannot start photograph reconstruction job without uploaded photographs.")
        else:
            # If upload_id not provided, pick latest video upload
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
            job_type=job_type,
            stage="queued",
            status="queued",
            progress=0.0,
            message=f"{'Photograph' if job_type == 'photo' else 'Video'} job queued for processing...",
            retry_count=0,
        )
        db.add(job)
        project.status = "Processing"
        db.commit()
        db.refresh(job)

        task_func = process_image_reconstruction_task if job_type == "photo" else process_reconstruction_task
        broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
        dispatched_to_celery = False

        if _is_celery_broker_reachable(broker_url, timeout=0.2):
            try:
                task = task_func.apply_async(args=[job.id], retry=False)
                job.celery_task_id = task.id
                db.commit()
                db.refresh(job)
                dispatched_to_celery = True
                logger.info(f"Dispatched {job_type} job {job.id} to Celery worker (task_id: {task.id})")
            except Exception as e:
                logger.warning(
                    f"Celery dispatch failed despite open broker port ({e}). Falling back to local thread."
                )

        if not dispatched_to_celery:
            logger.info(
                f"Celery broker not running. Running {job_type} job {job.id} in background thread for local development."
            )
            job.celery_task_id = f"local-{job.id[:8]}"
            db.commit()
            db.refresh(job)

            def run_sync():
                try:
                    task_func(job.id)
                except Exception as exc:
                    logger.exception(f"Background {job_type} reconstruction task {job.id} encountered an error: {exc}")

            t = threading.Thread(target=run_sync, daemon=True, name=f"recon-{job.id[:8]}")
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

        job_type = (
            latest_job.job_type
            if latest_job and hasattr(latest_job, "job_type") and latest_job.job_type
            else ("photo" if getattr(project, "input_type", "video") == "photo" else "video")
        )
        upload_id = latest_job.upload_id if latest_job else None
        return JobService.create_and_dispatch_job(db, project, user, upload_id=upload_id, job_type=job_type)
