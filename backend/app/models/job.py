"""Reconstruction Job model."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.upload import VideoUpload


class ReconstructionJob(Base, TimestampMixin):
    """Asynchronous background processing job for single-camera spatial mapping."""

    __tablename__ = "reconstruction_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    upload_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("video_uploads.id", ondelete="SET NULL"), nullable=True
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)

    # Observable stages:
    # queued -> validating -> extracting_keyframes -> estimating_geometry ->
    # generating_floor_plan -> generating_3d_model -> completed
    stage: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)

    # High level statuses: queued | processing | completed | failed | cancelled
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)

    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")
    user: Mapped["User"] = relationship("User", back_populates="jobs")
    upload: Mapped[Optional["VideoUpload"]] = relationship("VideoUpload", back_populates="jobs")
