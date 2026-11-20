"""Project management and versioning endpoints."""

from typing import List, Optional, Union
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_authorized_project, get_current_user, get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import MapProject, ProjectCreate, ProjectUpdate, ProjectVersionRead, VersionCreate
from app.schemas.job import ProcessingStatus
from app.services.project_service import ProjectService
from app.services.upload_service import UploadService
from app.services.image_upload_service import ImageUploadService
from app.services.job_service import JobService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[MapProject])
def list_projects(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List projects accessible to the current user (surveyor isolation enforced)."""
    return ProjectService.list_projects(
        db, current_user, skip=skip, limit=limit, search=search, status=status_filter
    )


@router.post("", response_model=Union[MapProject, dict], status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    video: Optional[UploadFile] = File(default=None),
    images: Optional[List[UploadFile]] = File(default=None),
    photos: Optional[List[UploadFile]] = File(default=None),
    name: Optional[str] = Form(default=None),
    location: Optional[str] = Form(default="Indoor Survey Site"),
    color: Optional[str] = Form(default="blue"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new project.
    Supports JSON payload, multipart video upload, and multipart photograph uploads.
    """
    content_type = request.headers.get("content-type", "")

    # Multipart photograph mapping creation
    uploaded_images = images or photos
    if "multipart/form-data" in content_type and uploaded_images:
        first_fname = getattr(uploaded_images[0], "filename", "") or ""
        proj_name = str(name or (first_fname.rsplit(".", 1)[0].replace("_", " ").title() if first_fname else "Indoor Photo Survey"))
        proj_in = ProjectCreate(name=proj_name, location=location or "Indoor Survey Site", color=color or "blue", input_type="photo")
        project = ProjectService.create_project(db, current_user, proj_in)

        try:
            saved = ImageUploadService.validate_and_save_batch(db, project, current_user, uploaded_images)
            job = JobService.create_and_dispatch_job(db, project, current_user, job_type="photo")
        except ValueError as e:
            db.delete(project)
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            db.delete(project)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process photograph upload: {str(e)}",
            )

        AuditService.log(
            db,
            action="create_mapping_with_photos",
            user_id=current_user.id,
            project_id=project.id,
            details=f"Uploaded {len(saved)} photos and queued job {job.id}",
        )
        return {"id": project.id, "status": project.status}

    # Multipart video mapping creation (as used by frontend createMapping)
    if "multipart/form-data" in content_type and video is not None:
        filename = getattr(video, "filename", "") or ""
        proj_name = str(name or (filename.rsplit(".", 1)[0].replace("_", " ").title() if filename else "Indoor Mapping"))
        proj_in = ProjectCreate(name=proj_name, location=location or "Indoor Survey Site", color=color or "blue", input_type="video")
        project = ProjectService.create_project(db, current_user, proj_in)

        # Process upload and queue job
        try:
            upload = UploadService.validate_and_save_upload(db, project, current_user, video)
            job = JobService.create_and_dispatch_job(db, project, current_user, upload.id, job_type="video")
        except ValueError as e:
            db.delete(project)
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            db.delete(project)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process video upload: {str(e)}",
            )

        AuditService.log(
            db,
            action="create_mapping_with_video",
            user_id=current_user.id,
            project_id=project.id,
            details=f"Uploaded {filename} and queued job {job.id}",
        )
        return {"id": project.id, "status": project.status}

    # Standard JSON body request
    try:
        body = await request.json()
        proj_in = ProjectCreate(**body)
    except Exception:
        proj_in = ProjectCreate(name=name or "New Indoor Project", location=location, color=color)

    project = ProjectService.create_project(db, current_user, proj_in)
    AuditService.log(
        db,
        action="create_project",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Created project {project.name}",
    )
    return project
    AuditService.log(
        db,
        action="create_project",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Created project {project.name}",
    )
    return project


@router.get("/{project_id}", response_model=MapProject)
def get_project(project: Project = Depends(get_authorized_project)):
    """Retrieve details for a single authorized project."""
    return project


@router.patch("/{project_id}", response_model=MapProject)
def update_project(
    project_in: ProjectUpdate,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename or update project metadata."""
    updated = ProjectService.update_project(db, project, project_in)
    AuditService.log(
        db,
        action="update_project",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Updated project metadata: {project_in.model_dump(exclude_unset=True)}",
    )
    return updated


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project and all associated files/geometry."""
    project_id = project.id
    project_name = project.name
    ProjectService.delete_project(db, project)
    AuditService.log(
        db,
        action="delete_project",
        user_id=current_user.id,
        project_id=project_id,
        details=f"Deleted project '{project_name}'",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/versions", response_model=List[ProjectVersionRead])
def get_project_versions(project: Project = Depends(get_authorized_project), db: Session = Depends(get_db)):
    """Retrieve version history for a project."""
    return ProjectService.list_versions(db, project)


@router.post("/{project_id}/versions", response_model=ProjectVersionRead, status_code=status.HTTP_201_CREATED)
def create_project_version(
    payload: Optional[VersionCreate] = None,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new manual version snapshot of the project."""
    desc = payload.description if payload else None
    return ProjectService.create_version_snapshot(db, project, current_user, description=desc)


@router.post("/{project_id}/versions/{version_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_project_version(
    version_id: str,
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rollback floor plan and project state to a prior version."""
    success = ProjectService.restore_version(db, project, version_id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not restore version. Snapshot data is invalid or missing.",
        )
    AuditService.log(
        db,
        action="restore_version",
        user_id=current_user.id,
        project_id=project.id,
        details=f"Restored to version {version_id}",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/status", response_model=ProcessingStatus)
def get_processing_status(project: Project = Depends(get_authorized_project), db: Session = Depends(get_db)):
    """Poll real-time processing status of the project's reconstruction job."""
    return JobService.get_latest_job_status(db, project)


@router.post("/{project_id}/retry", response_model=ProcessingStatus)
def retry_processing(
    project: Project = Depends(get_authorized_project),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed reconstruction job."""
    try:
        JobService.retry_job(db, project, current_user)
        return JobService.get_latest_job_status(db, project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
