"""FastAPI dependency injection utilities."""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token, UserRole
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer JWT access token and return authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token credentials.",
        )

    user = AuthService.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
        )

    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user if token present, else return None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce admin-only access."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required for this operation.",
        )
    return current_user


def get_authorized_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """Verify project exists and current user has ownership or admin authorization."""
    project = ProjectService.get_project_with_auth(db, project_id, user)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you lack permission to access it.",
        )
    return project
