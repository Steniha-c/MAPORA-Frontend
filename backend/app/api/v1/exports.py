"""Export endpoints supporting SVG, PDF, DXF, and 3D GLB formats."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_authorized_project, get_current_user, get_db
from app.models.export import ExportRecord
from app.models.project import Project
from app.models.user import User
from app.schemas.export import ExportCreate, ExportResponse
from app.services.export_service import ExportService
from app.services.audit_service import AuditService
from app.storage.provider import get_storage

router = APIRouter(tags=["Exports"])


@router.get("/projects/{project_id}/export")
def download_export_direct(
    project_id: str,
    format: str = Query(..., description="Format: svg, pdf, dxf, or glb"),
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Direct export download endpoint matching frontend maporaApi.downloadExport.
    Streams requested format file blob with proper content disposition.
    """
    try:
        record, file_bytes = ExportService.generate_and_save_export(
            db, project, current_user, format
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db,
        action="download_export",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Exported format {format}",
    )

    media_types = {
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
        "dxf": "application/dxf",
        "glb": "model/gltf-binary",
        "gltf": "model/gltf-binary",
    }
    media_type = media_types.get(format.lower(), "application/octet-stream")

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_export(
    export_in: ExportCreate,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and persist an export artifact (SVG, PDF, DXF, GLB)."""
    try:
        record, _ = ExportService.generate_and_save_export(
            db, project, current_user, export_in.format
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    storage = get_storage()
    url = storage.get_url(record.storage_key)

    return ExportResponse(
        id=record.id,
        projectId=project.id,
        format=record.format,
        filename=record.filename,
        fileSizeBytes=record.file_size_bytes,
        downloadUrl=url,
        createdAt=record.created_at,
    )


@router.get("/exports/{export_id}", response_model=ExportResponse)
def get_export_record(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata and download link for a generated export."""
    record = db.scalar(select(ExportRecord).where(ExportRecord.id == export_id))
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export record not found.")

    project = db.scalar(select(Project).where(Project.id == record.project_id))
    if not project or (current_user.role != "admin" and project.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    storage = get_storage()
    url = storage.get_url(record.storage_key)

    return ExportResponse(
        id=record.id,
        projectId=record.project_id,
        format=record.format,
        filename=record.filename,
        fileSizeBytes=record.file_size_bytes,
        downloadUrl=url,
        createdAt=record.created_at,
    )
