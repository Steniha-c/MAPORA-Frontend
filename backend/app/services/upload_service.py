"""Video upload validation and storage service."""

import os
from pathlib import Path
import re
import uuid
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.upload import VideoUpload
from app.models.user import User
from app.storage.provider import get_storage


def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters and directory traversal elements."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return clean[:128]


class UploadService:
    """Service handling streaming video uploads, file integrity validation, and storage keys."""

    @staticmethod
    def validate_and_save_upload(
        db: Session,
        project: Project,
        user: User,
        upload_file: UploadFile,
    ) -> VideoUpload:
        original_name = upload_file.filename or "walkthrough.mp4"
        clean_name = sanitize_filename(original_name)
        ext = Path(clean_name).suffix.lower()

        # 1. Extension validation
        if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_VIDEO_EXTENSIONS)
            raise ValueError(f"Unsupported video file extension '{ext}'. Allowed: {allowed}")

        # 2. MIME type check
        content_type = (upload_file.content_type or "video/mp4").lower()
        if content_type not in settings.ALLOWED_VIDEO_MIME_TYPES:
            # Tolerant check for common browser MIME variations
            if not content_type.startswith("video/"):
                raise ValueError(f"Invalid MIME type: {content_type}. A valid video file is required.")

        # 3. Stream to storage and track size without loading entire file in memory
        storage = get_storage()
        storage_key = f"videos/{project.id}/{uuid.uuid4().hex}_{clean_name}"

        try:
            bytes_written = storage.save(
                upload_file.file,
                storage_key=storage_key,
                content_type=content_type,
            )
        except Exception as e:
            raise IOError(f"Storage backend failed while writing video: {str(e)}")

        if bytes_written > settings.MAX_UPLOAD_SIZE_BYTES:
            storage.delete(storage_key)
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise ValueError(f"Video file exceeds maximum size limit of {max_mb} MB.")

        if bytes_written == 0:
            storage.delete(storage_key)
            raise ValueError("Uploaded file is empty (0 bytes).")

        # 4. Record metadata in PostgreSQL database
        upload_record = VideoUpload(
            project_id=project.id,
            user_id=user.id,
            original_filename=clean_name,
            storage_key=storage_key,
            mime_type=content_type,
            file_size_bytes=bytes_written,
            status="uploaded",
        )
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)

        return upload_record
