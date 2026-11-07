"""User model."""

from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid
from app.core.security import UserRole

if TYPE_CHECKING:
    from app.models.token import RefreshToken
    from app.models.project import Project
    from app.models.upload import VideoUpload
    from app.models.job import ReconstructionJob
    from app.models.export import ExportRecord


class User(Base, TimestampMixin):
    """User accounts table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.SURVEYOR.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    uploads: Mapped[List["VideoUpload"]] = relationship(
        "VideoUpload", back_populates="user", cascade="all, delete-orphan"
    )
    jobs: Mapped[List["ReconstructionJob"]] = relationship(
        "ReconstructionJob", back_populates="user", cascade="all, delete-orphan"
    )
    exports: Mapped[List["ExportRecord"]] = relationship(
        "ExportRecord", back_populates="user", cascade="all, delete-orphan"
    )
