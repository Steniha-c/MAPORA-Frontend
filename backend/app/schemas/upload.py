"""Pydantic schemas for video uploads."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoUploadRead(BaseModel):
    """Schema for uploaded video details."""
    id: str
    project_id: str = Field(alias="projectId")
    original_filename: str = Field(alias="originalFilename")
    file_size_bytes: int = Field(alias="fileSizeBytes")
    mime_type: str = Field(alias="mimeType")
    duration_seconds: Optional[float] = Field(default=None, alias="durationSeconds")
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frame_count: Optional[int] = Field(default=None, alias="frameCount")
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class UploadResponse(BaseModel):
    """Upload acknowledgement matching frontend createMapping expectations."""
    id: str
    status: str = "uploaded"
    project_id: Optional[str] = Field(default=None, alias="projectId")

    model_config = ConfigDict(populate_by_name=True)
