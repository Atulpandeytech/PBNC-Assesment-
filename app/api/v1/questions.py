from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user, require_roles
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.question import (
    QuestionReviewRequest,
    QuestionUpdateRequest,
    SystemIndependentQuestion,
)
from app.services.document_service import DocumentService
from app.services.question_service import QuestionService

router = APIRouter(tags=["Questions"])


@router.get("/questions", response_model=PaginatedResponse[SystemIndependentQuestion])
@router.get("/documents/{document_id}/questions", response_model=PaginatedResponse[SystemIndependentQuestion])
async def list_questions(
    document_id: Optional[str] = None,
    document_id_query: Optional[str] = Query(None, alias="document_id"),
    status_filter: Optional[str] = Query(None, alias="status"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    question_type: Optional[str] = Query(None),
    has_answer: Optional[bool] = Query(None),
    needs_review: Optional[bool] = Query(None),
    sort_by: str = Query("sequence_index"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve structured questions extracted from a document with rich filtering and pagination."""
    target_doc_id = document_id or document_id_query or ""
    q_service = QuestionService(session)
    items, total = await q_service.list_questions(
        document_id=target_doc_id,
        user=current_user,
        status=status_filter,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        question_type=question_type,
        has_answer=has_answer,
        needs_review=needs_review,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get("/questions/{question_id}", response_model=SystemIndependentQuestion)
async def get_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve complete question details including options, answer, source coordinates, and confidence breakdown."""
    q_service = QuestionService(session)
    return await q_service.get_question(question_id, current_user)


@router.get("/questions/{question_id}/source")
async def get_question_source(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve source page preview image for visual verification of extracted question."""
    q_service = QuestionService(session)
    q = await q_service.get_question(question_id, current_user)
    first_page = q.source.pages[0] if q.source.pages else 1

    doc_service = DocumentService(session)
    img_bytes, mime = await doc_service.get_page_image(q.document_id, first_page, current_user)
    return Response(content=img_bytes, media_type=mime)


@router.patch("/questions/{question_id}", response_model=SystemIndependentQuestion)
async def update_question_review(
    question_id: str,
    req: QuestionUpdateRequest,
    current_user: User = Depends(require_roles(["admin", "reviewer", "user"])),
    session: AsyncSession = Depends(get_db),
):
    """Submit reviewer correction for a question, preserving the original extracted value in an audit trail."""
    q_service = QuestionService(session)
    return await q_service.update_question(question_id, req, current_user)


@router.post("/questions/{question_id}/review", response_model=SystemIndependentQuestion)
async def review_question_action(
    question_id: str,
    req: QuestionReviewRequest,
    current_user: User = Depends(require_roles(["admin", "reviewer", "user"])),
    session: AsyncSession = Depends(get_db),
):
    """Approve or reject an extracted question."""
    q_service = QuestionService(session)
    return await q_service.review_question(question_id, req, current_user)


@router.get("/documents/{document_id}/export")
async def export_questions(
    document_id: str,
    format_type: str = Query("json", alias="format"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Export document questions in a system-independent schema."""
    q_service = QuestionService(session)
    return await q_service.export_questions(document_id, current_user, format_type)
