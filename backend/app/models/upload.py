"""Video Upload model."""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.job import ReconstructionJob


class VideoUpload(Base, TimestampMixin):
    """Uploaded video metadata and storage mapping."""

    __tablename__ = "video_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Video properties decoded during preprocessing
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frame_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="uploads")
    user: Mapped["User"] = relationship("User", back_populates="uploads")
    jobs: Mapped[list["ReconstructionJob"]] = relationship(
        "ReconstructionJob", back_populates="upload"
    )
