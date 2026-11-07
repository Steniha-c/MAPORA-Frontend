"""Authentication service business logic."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token_string,
    get_password_hash,
    hash_token,
    verify_password,
    UserRole,
)
from app.models.user import User
from app.models.token import RefreshToken
from app.schemas.auth import UserCreate, TokenResponse, UserIdentity


class AuthService:
    """Service handling user accounts, JWT issuance, and revocable sessions."""

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.scalar(select(User).where(User.email == email.lower().strip()))

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.scalar(select(User).where(User.id == user_id))

    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        existing = AuthService.get_by_email(db, user_in.email)
        if existing:
            raise ValueError("A user with this email address already exists.")

        role = user_in.role.lower() if user_in.role else UserRole.SURVEYOR.value
        if role not in [UserRole.ADMIN.value, UserRole.SURVEYOR.value]:
            role = UserRole.SURVEYOR.value

        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=get_password_hash(user_in.password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        user = AuthService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    def create_session(db: Session, user: User) -> TokenResponse:
        """Create access JWT and store hashed refresh token in DB."""
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
            role=user.role,
        )

        raw_refresh_token = generate_refresh_token_string()
        token_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_record = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expires_at,
            revoked=False,
        )
        db.add(refresh_record)
        db.commit()

        user_identity = UserIdentity(id=user.id, email=user.email, role=user.role)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            user=user_identity,
        )

    @staticmethod
    def refresh_session(db: Session, raw_refresh_token: str) -> Optional[TokenResponse]:
        """Validate revocable refresh token and issue new session."""
        t_hash = hash_token(raw_refresh_token)
        record = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == t_hash,
                RefreshToken.revoked.is_(False),
            )
        )

        if not record or not record.is_valid:
            return None

        user = AuthService.get_by_id(db, record.user_id)
        if not user or not user.is_active:
            return None

        # Revoke used refresh token (rotation)
        record.revoked = True
        db.commit()

        # Generate new session
        return AuthService.create_session(db, user)

    @staticmethod
    def revoke_refresh_token(db: Session, raw_refresh_token: str) -> bool:
        t_hash = hash_token(raw_refresh_token)
        record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == t_hash))
        if record:
            record.revoked = True
            db.commit()
            return True
        return False

    @staticmethod
    def seed_initial_admin(db: Session) -> Optional[User]:
        if not settings.INITIAL_ADMIN_EMAIL or not settings.INITIAL_ADMIN_PASSWORD:
            return None

        admin = AuthService.get_by_email(db, settings.INITIAL_ADMIN_EMAIL)
        if not admin:
            admin = User(
                email=settings.INITIAL_ADMIN_EMAIL.lower().strip(),
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
        return admin
