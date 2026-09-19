from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend

_storage_instance: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND == "local":
            _storage_instance = LocalStorageBackend()
        else:
            # Fallback to local if S3 credentials not provided
            _storage_instance = LocalStorageBackend()
    return _storage_instance
