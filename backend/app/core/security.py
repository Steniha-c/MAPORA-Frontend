"""Security, password hashing, and JWT utilities for MAPORA backend."""

from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import secrets
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User roles supported in MAPORA."""
    ADMIN = "admin"
    SURVEYOR = "surveyor"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for a plaintext password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_refresh_token_string() -> str:
    """Generate a secure, cryptographically random refresh token string."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Hash a token string using SHA-256 for secure database lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token string."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None
