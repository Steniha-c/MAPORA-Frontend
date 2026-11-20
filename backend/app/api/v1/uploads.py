"""Video and photograph upload endpoints."""

from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_authorized_project, get_current_user, get_db
from app.models.project import Project
from app.models.upload import VideoUpload, ImageUpload
from app.models.user import User
from app.schemas.upload import UploadResponse, VideoUploadRead, ImageUploadRead, BatchImageUploadResponse
from app.schemas.job import ProcessingStatus
from app.services.upload_service import UploadService
from app.services.image_upload_service import ImageUploadService
from app.services.job_service import JobService
from app.services.audit_service import AuditService
from app.storage.provider import get_storage

router = APIRouter(tags=["Uploads"])


@router.post(
    "/projects/{project_id}/uploads",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_video(
    project_id: str,
    file: UploadFile = File(...),
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload an indoor walkthrough video to project storage."""
    try:
        upload = UploadService.validate_and_save_upload(db, project, current_user, file)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    AuditService.log(
        db,
        action="video_upload",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Uploaded {upload.original_filename} ({upload.file_size_bytes} bytes)",
    )

    return UploadResponse(
        id=upload.id,
        status=upload.status,
        projectId=project.id,
    )


@router.get("/uploads/{upload_id}", response_model=VideoUploadRead)
def get_upload_metadata(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata for an uploaded video file."""
    upload = db.scalar(select(VideoUpload).where(VideoUpload.id == upload_id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload record not found.")

    # Ownership check
    project = db.scalar(select(Project).where(Project.id == upload.project_id))
    if not project or (current_user.role != "admin" and project.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return upload


@router.post(
    "/projects/{project_id}/images",
    response_model=BatchImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_images(
    project_id: str,
    files: List[UploadFile] = File(...),
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload one or multiple photographs for indoor spatial reconstruction."""
    try:
        saved_records = ImageUploadService.validate_and_save_batch(
            db=db,
            project=project,
            user=current_user,
            upload_files=files,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    AuditService.log(
        db,
        action="image_upload_batch",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Uploaded {len(saved_records)} photographs",
    )

    return BatchImageUploadResponse(
        uploaded=len(saved_records),
        images=saved_records,
        projectId=project.id,
    )


@router.get("/projects/{project_id}/images", response_model=List[ImageUploadRead])
def list_project_images(
    project_id: str,
    project: Project = Depends(get_authorized_project),
    db: Session = Depends(get_db),
):
    """List all photographs uploaded for an authorized project."""
    return ImageUploadService.list_images(db, project)


@router.post("/projects/{project_id}/reconstruct/images", response_model=ProcessingStatus)
def trigger_image_reconstruction(
    project_id: str,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger background spatial reconstruction using uploaded photographs."""
    try:
        job = JobService.create_and_dispatch_job(
            db=db,
            project=project,
            user=current_user,
            job_type="photo",
        )
        return JobService.get_latest_job_status(db, project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/storage/{file_path:path}")
def stream_storage_file(file_path: str):
    """Secure local file streaming proxy."""
    storage = get_storage()
    if not storage.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage.")

    media_type = "application/octet-stream"
    if file_path.endswith(".glb"):
        media_type = "model/gltf-binary"
    elif file_path.endswith(".svg"):
        media_type = "image/svg+xml"
    elif file_path.endswith(".pdf"):
        media_type = "application/pdf"
    elif file_path.endswith(".mp4"):
        media_type = "video/mp4"
    elif file_path.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif file_path.endswith(".png"):
        media_type = "image/png"
    elif file_path.endswith(".webp"):
        media_type = "image/webp"

    return StreamingResponse(storage.open(file_path), media_type=media_type)
