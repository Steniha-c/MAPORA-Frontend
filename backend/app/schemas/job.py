"""Pydantic schemas for reconstruction background jobs."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    """Payload to initiate a reconstruction job."""
    upload_id: Optional[str] = Field(default=None, alias="uploadId")

    model_config = ConfigDict(populate_by_name=True)


class ProcessingStatus(BaseModel):
    """Processing status schema strictly matching frontend ProcessingStatus."""
    project_id: str = Field(alias="projectId")
    stage: str
    status: str  # 'queued' | 'processing' | 'completed' | 'failed' | 'unknown'
    progress: Optional[float] = 0.0
    message: Optional[str] = None
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class JobRead(BaseModel):
    """Full reconstruction job detail schema."""
    id: str
    project_id: str = Field(alias="projectId")
    upload_id: Optional[str] = Field(default=None, alias="uploadId")
    stage: str
    status: str
    progress: float
    message: Optional[str] = None
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    retry_count: int = Field(alias="retryCount")
    duration_seconds: Optional[float] = Field(default=None, alias="durationSeconds")
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
