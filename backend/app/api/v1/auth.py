from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account and obtain access tokens."""
    try:
        user = AuthService.register_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db,
        action="user_registered",
        user_id=user.id,
        details=f"User {user.email} registered with role {user.role}.",
        ip_address=request.client.host if request.client else None,
    )

    return AuthService.create_session(db, user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email and password."""
    user = AuthService.authenticate(db, credentials.email, credentials.password)
    if not user:
        # Safe generic error message to prevent account enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    AuditService.log(
        db,
        action="user_login",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return AuthService.create_session(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access session."""
    token_str = payload.refresh_token
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token must be provided in request body.",
        )

    session = AuthService.refresh_session(db, token_str)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please log in again.",
        )

    return session


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    payload: Optional[RefreshTokenRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke user refresh token session."""
    if payload and payload.refresh_token:
        AuthService.revoke_refresh_token(db, payload.refresh_token)

    AuditService.log(db, action="user_logout", user_id=current_user.id)
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserRead)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return profile for the currently authenticated user."""
    return current_user
