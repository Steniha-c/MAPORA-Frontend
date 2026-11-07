"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class BaseStorage(ABC):
    """Abstract storage provider interface."""

    @abstractmethod
    def save(self, file_obj: BinaryIO, storage_key: str, content_type: Optional[str] = None) -> int:
        """Save stream to storage and return bytes written."""
        pass

    @abstractmethod
    def open(self, storage_key: str) -> BinaryIO:
        """Open a file stream for reading."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete file from storage."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if file exists in storage."""
        pass

    @abstractmethod
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get accessible download URL or signed URL."""
        pass

    @abstractmethod
    def get_file_path(self, storage_key: str) -> Optional[str]:
        """Get absolute local filesystem path if available, or None if remote."""
        pass
