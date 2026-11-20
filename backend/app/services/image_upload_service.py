"""Photograph upload validation, integrity checking, and storage service."""

from io import BytesIO
import os
from pathlib import Path
import re
from typing import List
import uuid
import cv2
import numpy as np
from fastapi import UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.upload import ImageUpload
from app.models.user import User
from app.storage.provider import get_storage


def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters and directory traversal elements."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return clean[:128]


class ImageUploadService:
    """Service handling photograph uploads, image integrity validation, and storage."""

    @staticmethod
    def validate_and_save_image(
        db: Session,
        project: Project,
        user: User,
        upload_file: UploadFile,
        order_index: int = 0,
    ) -> ImageUpload:
        """Validate, store, and record a single photograph."""
        original_name = upload_file.filename or f"photo_{order_index + 1}.jpg"
        clean_name = sanitize_filename(original_name)
        ext = Path(clean_name).suffix.lower()

        # 1. Extension validation
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)
            raise ValueError(f"Unsupported image extension '{ext}' for file '{clean_name}'. Allowed: {allowed}")

        # 2. MIME type check
        content_type = (upload_file.content_type or "image/jpeg").lower()
        if content_type not in settings.ALLOWED_IMAGE_MIME_TYPES:
            if not content_type.startswith("image/"):
                raise ValueError(f"Invalid MIME type '{content_type}' for '{clean_name}'. An image is required.")

        # 3. Read content into buffer to validate image integrity and dimensions
        try:
            content = upload_file.file.read()
        except Exception as e:
            raise IOError(f"Could not read uploaded image '{clean_name}': {str(e)}")

        file_size = len(content)
        if file_size == 0:
            raise ValueError(f"Uploaded image '{clean_name}' is empty (0 bytes).")

        if file_size > settings.MAX_IMAGE_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_IMAGE_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise ValueError(f"Image '{clean_name}' ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed size of {max_mb} MB.")

        # 4. Decode with OpenCV to ensure file is an authentic, non-corrupted image
        img_array = np.frombuffer(content, dtype=np.uint8)
        decoded = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if decoded is None or decoded.size == 0:
            raise ValueError(f"Failed to decode image '{clean_name}'. The file appears corrupted or unreadable.")

        height, width = decoded.shape[:2]

        # 5. Stream to storage backend
        storage = get_storage()
        storage_key = f"images/{project.id}/{uuid.uuid4().hex}_{clean_name}"

        try:
            storage.save(
                BytesIO(content),
                storage_key=storage_key,
                content_type=content_type,
            )
        except Exception as e:
            raise IOError(f"Storage backend failed while writing image '{clean_name}': {str(e)}")

        # 6. Record metadata in DB
        image_record = ImageUpload(
            project_id=project.id,
            user_id=user.id,
            original_filename=clean_name,
            storage_key=storage_key,
            mime_type=content_type,
            file_size_bytes=file_size,
            width=width,
            height=height,
            order_index=order_index,
            status="uploaded",
        )
        db.add(image_record)
        db.commit()
        db.refresh(image_record)

        return image_record

    @staticmethod
    def validate_and_save_batch(
        db: Session,
        project: Project,
        user: User,
        upload_files: List[UploadFile],
    ) -> List[ImageUpload]:
        """Validate and persist multiple photographs in sequence."""
        if not upload_files:
            raise ValueError("No photograph files provided.")

        records: List[ImageUpload] = []
        for idx, file in enumerate(upload_files):
            rec = ImageUploadService.validate_and_save_image(
                db=db,
                project=project,
                user=user,
                upload_file=file,
                order_index=idx,
            )
            records.append(rec)

        # Update project duration label and input type
        project.input_type = "photo"
        project.duration = f"{len(project.image_uploads)} photos"
        db.commit()

        return records

    @staticmethod
    def list_images(db: Session, project: Project) -> List[ImageUpload]:
        """List all photographs uploaded for a given project ordered by order_index."""
        query = (
            select(ImageUpload)
            .where(ImageUpload.project_id == project.id)
            .order_by(ImageUpload.order_index.asc())
        )
        return list(db.scalars(query).all())

