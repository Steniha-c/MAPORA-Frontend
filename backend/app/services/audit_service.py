"""Audit service for logging sensitive actions."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditService:
    @staticmethod
    def log(
        db: Session,
        action: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            user_id=user_id,
            project_id=project_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(event)
        db.commit()
        return event
