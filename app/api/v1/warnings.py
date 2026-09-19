from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.warning import ExtractionWarningResponse, ReviewItemResponse
from app.services.review_service import ReviewService

router = APIRouter(tags=["Warnings & Review"])


@router.get("/documents/{document_id}/warnings", response_model=List[ExtractionWarningResponse])
async def list_document_warnings(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all warnings (OCR quality, missing numbers, carry-overs) for a document."""
    service = ReviewService(session)
    return await service.list_document_warnings(document_id, current_user)


@router.get("/documents/{document_id}/review-items", response_model=List[ReviewItemResponse])
async def list_document_review_items(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve prioritized queue of low-confidence and flagged questions requiring reviewer action."""
    service = ReviewService(session)
    return await service.list_review_items(document_id, current_user)
