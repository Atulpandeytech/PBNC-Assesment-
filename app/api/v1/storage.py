from fastapi import APIRouter, HTTPException, Response
from app.core.errors import NotFoundError
from app.storage import get_storage_backend

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/{file_path:path}")
async def get_storage_asset(file_path: str):
    """Retrieve stored document images, figures, or diagrams."""
    storage = get_storage_backend()
    try:
        data = await storage.get_bytes(file_path)
        mime = "image/png" if file_path.endswith(".png") else "application/octet-stream"
        if file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
            mime = "image/jpeg"
        elif file_path.endswith(".pdf"):
            mime = "application/pdf"
        return Response(content=data, media_type=mime)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Asset not found")
