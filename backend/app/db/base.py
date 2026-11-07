"""SQLAlchemy Base and common model mixins."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base model class for all SQLAlchemy entities."""
    pass


class TimestampMixin:
    """Reusable mixin providing created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


def generate_uuid() -> str:
    """Generate a clean string UUID."""
    return str(uuid.uuid4())
