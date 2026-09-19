from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, Optional


class StorageBackend(ABC):
    @abstractmethod
    async def save_bytes(self, data: bytes, destination_key: str, mime_type: Optional[str] = None) -> str:
        """Save raw bytes to storage and return stored_key."""
        pass

    @abstractmethod
    async def get_bytes(self, key: str) -> bytes:
        """Retrieve raw bytes from storage."""
        pass

    @abstractmethod
    async def get_local_path(self, key: str) -> Path:
        """Get local filesystem path to file, downloading if necessary."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete object from storage."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if object exists in storage."""
        pass

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get direct or signed download URL."""
        pass
