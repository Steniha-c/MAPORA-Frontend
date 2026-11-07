"""Pydantic schemas for Projects and Project Versions."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """Base fields for project."""
    name: str = Field(min_length=1, max_length=255)
    location: Optional[str] = Field(default="Indoor Survey Site", max_length=255)
    color: Optional[str] = Field(default="blue", max_length=50)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for renaming or updating project metadata."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = None


class MapProject(BaseModel):
    """Project schema matching frontend MapProject interface."""
    id: str
    name: str
    location: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    status: str  # 'Ready' | 'Processing' | 'Needs attention'
    rooms: int = Field(alias="roomsCount", default=0)
    duration: str = "00:00"
    color: str = "blue"
    version_count: Optional[int] = Field(default=1, alias="versionCount")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ProjectVersionRead(BaseModel):
    """Project version matching frontend ProjectVersion."""
    id: str
    version: int
    created_at: datetime = Field(alias="createdAt")
    description: Optional[str] = None
    status: str = "active"

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )



class VersionCreate(BaseModel):
    """Schema for creating a project version snapshot."""
    description: Optional[str] = None
