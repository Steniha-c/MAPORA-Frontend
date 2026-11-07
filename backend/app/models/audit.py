"""Audit Event model for tracking sensitive user operations."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, generate_uuid


class AuditEvent(Base):
    """Audit log for critical operations like project deletion, version restore, and edits."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
