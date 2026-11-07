"""Project model."""

from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.version import ProjectVersion
    from app.models.upload import VideoUpload
    from app.models.job import ReconstructionJob
    from app.models.geometry import FloorPlan, Model3D
    from app.models.export import ExportRecord


class Project(Base, TimestampMixin):
    """Indoor mapping project representation matching frontend MapProject structure."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="Indoor Survey Site", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Needs attention", nullable=False)
    rooms_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration: Mapped[str] = mapped_column(String(50), default="00:00", nullable=False)
    color: Mapped[str] = mapped_column(String(50), default="blue", nullable=False)
    version_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    versions: Mapped[List["ProjectVersion"]] = relationship(
        "ProjectVersion", back_populates="project", cascade="all, delete-orphan", order_by="ProjectVersion.version_number.desc()"
    )
    uploads: Mapped[List["VideoUpload"]] = relationship(
        "VideoUpload", back_populates="project", cascade="all, delete-orphan"
    )
    jobs: Mapped[List["ReconstructionJob"]] = relationship(
        "ReconstructionJob", back_populates="project", cascade="all, delete-orphan", order_by="ReconstructionJob.created_at.desc()"
    )
    floor_plans: Mapped[List["FloorPlan"]] = relationship(
        "FloorPlan", back_populates="project", cascade="all, delete-orphan"
    )
    models3d: Mapped[List["Model3D"]] = relationship(
        "Model3D", back_populates="project", cascade="all, delete-orphan"
    )
    exports: Mapped[List["ExportRecord"]] = relationship(
        "ExportRecord", back_populates="project", cascade="all, delete-orphan"
    )
