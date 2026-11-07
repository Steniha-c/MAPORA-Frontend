"""Revocable refresh token model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, TimestampMixin):
    """Stores hashed refresh tokens to enable secure revocation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        """Check if token is not revoked and not expired."""
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return not self.revoked and expires > now

