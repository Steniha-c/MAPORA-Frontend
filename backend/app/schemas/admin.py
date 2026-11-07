"""Pydantic schemas for admin analytics and monitoring."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AdminJob(BaseModel):
    """Admin job monitoring item matching frontend AdminJob."""
    id: str
    project_id: str = Field(alias="projectId")
    project_name: str = Field(alias="projectName")
    stage: str
    status: str
    updated_at: datetime = Field(alias="updatedAt")
    duration_seconds: Optional[float] = Field(default=None, alias="durationSeconds")
    message: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AdminAnalytics(BaseModel):
    """Database-backed analytics strictly matching frontend AdminAnalytics."""
    project_count: int = Field(alias="projectCount")
    user_count: int = Field(alias="userCount")
    jobs_running: int = Field(alias="jobsRunning")
    jobs_failed: int = Field(alias="jobsFailed")
    jobs_completed: Optional[int] = Field(default=0, alias="jobsCompleted")
    average_processing_seconds: Optional[float] = Field(default=0.0, alias="averageProcessingSeconds")
    reconstructions_completed: Optional[int] = Field(default=0, alias="reconstructionsCompleted")
    rooms_detected: Optional[int] = Field(default=0, alias="roomsDetected")
    average_geometry_confidence: Optional[float] = Field(default=0.0, alias="averageGeometryConfidence")
    updated_at: datetime = Field(alias="updatedAt")
    recent_jobs: Optional[List[AdminJob]] = Field(default=None, alias="recentJobs")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AdminJobListResponse(BaseModel):
    """Paginated admin job list."""
    total: int
    items: List[AdminJob]
