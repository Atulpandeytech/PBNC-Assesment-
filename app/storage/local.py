import os
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = Path(root_dir or settings.STORAGE_LOCAL_ROOT).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, key: str) -> Path:
        """Sanitize key and ensure it resolves inside root_dir (anti-path-traversal)."""
        clean_key = key.replace("\\", "/").lstrip("/")
        safe_path = (self.root_dir / clean_key).resolve()
        if not str(safe_path).startswith(str(self.root_dir)):
            raise AppError("PATH_TRAVERSAL_DETECTED", "Invalid storage key", 400)
        return safe_path

    async def save_bytes(self, data: bytes, destination_key: str, mime_type: Optional[str] = None) -> str:
        safe_path = self._resolve_safe_path(destination_key)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_bytes(data)
        return destination_key

    async def get_bytes(self, key: str) -> bytes:
        safe_path = self._resolve_safe_path(key)
        if not safe_path.exists() or not safe_path.is_file():
            raise NotFoundError(f"File '{key}' not found in storage")
        return safe_path.read_bytes()

    async def get_local_path(self, key: str) -> Path:
        safe_path = self._resolve_safe_path(key)
        if not safe_path.exists():
            raise NotFoundError(f"File '{key}' not found in storage")
        return safe_path

    async def delete(self, key: str) -> bool:
        safe_path = self._resolve_safe_path(key)
        if safe_path.exists() and safe_path.is_file():
            safe_path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        try:
            safe_path = self._resolve_safe_path(key)
            return safe_path.exists() and safe_path.is_file()
        except Exception:
            return False

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        # In local storage, return internal relative resource URL
        clean_key = key.replace("\\", "/").lstrip("/")
        return f"/api/v1/storage/{clean_key}"
