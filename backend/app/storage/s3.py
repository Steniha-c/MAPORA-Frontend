"""S3 and MinIO compatible object storage backend."""

import os
import tempfile
from typing import BinaryIO, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger
from app.storage.base import BaseStorage


class S3StorageBackend(BaseStorage):
    """S3-compatible object storage provider."""

    def __init__(self):
        client_kwargs = {
            "service_name": "s3",
            "region_name": settings.S3_REGION_NAME,
            "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
            "config": Config(signature_version="s3v4"),
        }
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
            client_kwargs["use_ssl"] = settings.S3_SECURE

        self.s3_client = boto3.client(**client_kwargs)
        self.bucket_name = settings.S3_BUCKET_NAME
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            except Exception as e:
                logger.warning(f"Could not automatically create S3 bucket {self.bucket_name}: {e}")

    def save(self, file_obj: BinaryIO, storage_key: str, content_type: Optional[str] = None) -> int:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        # Seek to end to measure size if possible, then rewind
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(0)

        self.s3_client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=self.bucket_name,
            Key=storage_key,
            ExtraArgs=extra_args,
        )
        return size

    def open(self, storage_key: str) -> BinaryIO:
        temp = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
        self.s3_client.download_fileobj(self.bucket_name, storage_key, temp)
        temp.seek(0)
        return temp

    def delete(self, storage_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except ClientError:
            return False

    def exists(self, storage_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except ClientError:
            return False

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate a short-lived presigned download URL."""
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": storage_key},
            ExpiresIn=expires_in,
        )

    def get_file_path(self, storage_key: str) -> Optional[str]:
        # Remote S3 storage does not have a local filesystem path
        return None
