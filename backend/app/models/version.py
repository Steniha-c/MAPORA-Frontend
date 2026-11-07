"""Project Version model for historical snapshotting and rollback."""

from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project


class ProjectVersion(Base, TimestampMixin):
    """Project version snapshot matching frontend ProjectVersion."""

    __tablename__ = "project_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Serialized floor plan and room data snapshot for rollback
    floor_plan_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    @property
    def version(self) -> int:
        return self.version_number

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="versions")

