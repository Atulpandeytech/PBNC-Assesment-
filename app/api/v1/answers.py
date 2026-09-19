from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.answer_key import AnswerKeyResponse
from app.schemas.question import AnswerInfo
from app.services.answer_key_service import AnswerKeyService

router = APIRouter(tags=["Answers"])


@router.get("/documents/{document_id}/answer-key", response_model=AnswerKeyResponse)
async def get_document_answer_key(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve parsed answer key entries, match statistics, and orphan entries."""
    service = AnswerKeyService(session)
    return await service.get_document_answer_key(document_id, current_user)


@router.get("/questions/{question_id}/answer", response_model=AnswerInfo)
async def get_question_answer(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve the matched answer for a specific question."""
    service = AnswerKeyService(session)
    return await service.get_question_answer(question_id, current_user)
