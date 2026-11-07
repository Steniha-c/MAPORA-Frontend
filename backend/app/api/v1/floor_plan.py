"""Spatial geometry, floor plan, and 3D scene endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_authorized_project, get_current_user, get_db
from app.models.geometry import Model3D
from app.models.project import Project
from app.models.user import User
from app.schemas.floor_plan import FloorPlanModel, FloorPlanUpdate
from app.schemas.model3d import Model3DRead, SceneResponse
from app.services.floor_plan_service import FloorPlanService
from app.storage.provider import get_storage

router = APIRouter(tags=["Spatial Geometry"])


@router.get("/projects/{project_id}/floor-plan", response_model=FloorPlanModel)
def get_floor_plan(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    """
    Retrieve generated 2D floor plan for an authorized project.
    Strictly adheres to frontend FloorPlanModel schema.
    """
    plan = FloorPlanService.get_active_floor_plan(db, project)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconstructed floor plan is available for this project yet. Please process a video walkthrough.",
        )
    return plan


@router.patch("/projects/{project_id}/floor-plan", response_model=FloorPlanModel)
def update_floor_plan(
    update_in: FloorPlanUpdate,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Interactive floor plan editing endpoint.
    Updates room labels and editable boundary attributes with validation.
    """
    try:
        return FloorPlanService.update_floor_plan(db, project, current_user, update_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/scene", response_model=SceneResponse)
def get_scene(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    """
    Retrieve 3D scene geometry URL strictly conforming to frontend getScene expectations.
    """
    model = db.scalar(
        select(Model3D)
        .where(Model3D.project_id == project.id)
        .order_by(Model3D.created_at.desc())
    )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconstructed 3D model geometry exists for this project yet.",
        )

    storage = get_storage()
    url = storage.get_url(model.storage_key)

    return SceneResponse(geometryUrl=url)


@router.get("/projects/{project_id}/model", response_model=Model3DRead)
def get_model_details(
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    """Retrieve full metadata for the generated 3D architectural mesh model."""
    model = db.scalar(
        select(Model3D)
        .where(Model3D.project_id == project.id)
        .order_by(Model3D.created_at.desc())
    )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D model has not been generated for this project.",
        )

    storage = get_storage()
    url = storage.get_url(model.storage_key)

    return Model3DRead(
        id=model.id,
        projectId=project.id,
        format=model.format,
        fileSizeBytes=model.file_size_bytes,
        vertexCount=model.vertex_count,
        faceCount=model.face_count,
        downloadUrl=url,
        metadata=model.metadata_json,
    )
