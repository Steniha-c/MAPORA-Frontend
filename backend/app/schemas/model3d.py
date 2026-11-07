"""Pydantic schemas for 3D model and scene views."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class SceneResponse(BaseModel):
    """Scene response schema matching frontend getScene expectation."""
    geometry_url: str = Field(alias="geometryUrl")

    model_config = ConfigDict(populate_by_name=True)


class Model3DRead(BaseModel):
    """Full 3D model details schema."""
    id: str
    project_id: str = Field(alias="projectId")
    format: str
    file_size_bytes: int = Field(alias="fileSizeBytes")
    vertex_count: int = Field(alias="vertexCount")
    face_count: int = Field(alias="faceCount")
    download_url: str = Field(alias="downloadUrl")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
