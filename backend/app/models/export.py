"""Export Record model for tracking generated export files."""

from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ExportRecord(Base, TimestampMixin):
    """Stores generated export artifacts (SVG, PDF, DXF, GLB)."""

    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # svg, pdf, dxf, glb, etc.
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="exports")
    user: Mapped["User"] = relationship("User", back_populates="exports")
