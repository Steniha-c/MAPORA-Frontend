"""Local filesystem storage backend."""

import os
from pathlib import Path
import shutil
from typing import BinaryIO, Optional

from app.storage.base import BaseStorage
from app.core.config import settings


class LocalStorageBackend(BaseStorage):
    """Secure local disk storage backend."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> Path:
        """Resolve path and guard strictly against directory traversal."""
        clean_key = storage_key.strip().lstrip("/\\")
        target_path = (self.base_dir / clean_key).resolve()
        # Security check: Ensure target_path starts with base_dir
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError(f"Directory traversal attack detected: {storage_key}")
        return target_path

    def save(self, file_obj: BinaryIO, storage_key: str, content_type: Optional[str] = None) -> int:
        target_path = self._resolve_safe_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB buffer
        with open(target_path, "wb") as f_out:
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                f_out.write(chunk)
                total_bytes += len(chunk)

        return total_bytes

    def open(self, storage_key: str) -> BinaryIO:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found in storage: {storage_key}")
        return open(target_path, "rb")

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_safe_path(storage_key)
        if target_path.exists():
            if target_path.is_file():
                target_path.unlink()
                return True
            elif target_path.is_dir():
                shutil.rmtree(target_path)
                return True
        return False

    def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_safe_path(storage_key)
        return target_path.exists()

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        # For local backend, point to internal download proxy endpoint
        clean_key = storage_key.strip().lstrip("/\\")
        return f"{settings.API_V1_PREFIX}/storage/{clean_key}"

    def get_file_path(self, storage_key: str) -> Optional[str]:
        target_path = self._resolve_safe_path(storage_key)
        return str(target_path)
