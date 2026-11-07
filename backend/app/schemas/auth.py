"""Pydantic schemas for authentication and user accounts."""

import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class UserBase(BaseModel):
    """Base user fields."""
    email: str = Field(min_length=3, max_length=255, description="User email address")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format.")
        return clean


class UserCreate(UserBase):
    """User registration schema."""
    password: str = Field(min_length=8, max_length=128, description="User password (min 8 chars)")
    role: Optional[str] = Field(default="surveyor", description="Role: admin or surveyor")


class UserLogin(UserBase):
    """User login request schema."""
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""
    refresh_token: Optional[str] = Field(default=None, alias="refreshToken")

    model_config = ConfigDict(populate_by_name=True)


class UserIdentity(BaseModel):
    """Frontend-compatible UserIdentity."""
    id: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserRead(UserBase):
    """User profile response schema."""
    id: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Authentication session matching frontend AuthSession and OAuth2 standards."""
    access_token: str = Field(alias="accessToken")
    token_type: str = "bearer"
    refresh_token: Optional[str] = Field(default=None, alias="refreshToken")
    user: UserIdentity

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
