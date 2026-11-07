"""Pydantic schemas for file exports."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ExportCreate(BaseModel):
    """Request schema to trigger an export creation."""
    format: str = Field(description="Format to export: svg, pdf, dxf, or glb")


class ExportResponse(BaseModel):
    """Export metadata and download URL."""
    id: str
    project_id: str = Field(alias="projectId")
    format: str
    filename: str
    file_size_bytes: int = Field(alias="fileSizeBytes")
    download_url: str = Field(alias="downloadUrl")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
