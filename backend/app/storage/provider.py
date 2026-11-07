"""Storage provider factory."""

from functools import lru_cache

from app.core.config import settings
from app.storage.base import BaseStorage
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend


@lru_cache()
def get_storage() -> BaseStorage:
    """Return the configured storage backend singleton."""
    if settings.STORAGE_BACKEND.lower() == "s3" and settings.S3_ACCESS_KEY_ID:
        return S3StorageBackend()
    return LocalStorageBackend()
