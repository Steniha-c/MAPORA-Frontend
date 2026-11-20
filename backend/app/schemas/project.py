"""Pydantic schemas for Projects and Project Versions."""

from datetime import datetime
from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """Base fields for project."""
    name: str = Field(min_length=1, max_length=255)
    location: Optional[str] = Field(default="Indoor Survey Site", max_length=255)
    color: Optional[str] = Field(default="blue", max_length=50)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    input_type: Optional[str] = "video"


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
    rooms: int = Field(default=0, validation_alias=AliasChoices("rooms_count", "roomsCount", "rooms"))
    rooms_count: Optional[int] = Field(default=None, alias="roomsCount", validation_alias=AliasChoices("rooms_count", "roomsCount", "rooms"))
    duration: str = "00:00"
    color: str = "blue"
    version_count: Optional[int] = Field(default=1, alias="versionCount", validation_alias=AliasChoices("version_count", "versionCount"))
    input_type: Optional[str] = Field(default="video", alias="inputType", validation_alias=AliasChoices("input_type", "inputType"))
    image_count: Optional[int] = Field(default=0, alias="imageCount", validation_alias=AliasChoices("image_count", "imageCount"))

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
