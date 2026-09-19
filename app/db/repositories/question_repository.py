from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Question
from app.db.repositories.base_repository import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, session: AsyncSession):
        super().__init__(Question, session)

    async def get_with_details(self, question_id: str) -> Optional[Question]:
        stmt = (
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.warnings), selectinload(Question.document))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_document(
        self,
        document_id: str,
        status: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        question_type: Optional[str] = None,
        has_answer: Optional[bool] = None,
        needs_review: Optional[bool] = None,
        sort_by: str = "sequence_index",
        sort_order: str = "asc",
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[Question], int]:
        query = select(Question).where(Question.document_id == document_id)
        count_query = select(func.count(Question.id)).where(Question.document_id == document_id)

        if status:
            query = query.where(Question.extraction_status == status)
            count_query = count_query.where(Question.extraction_status == status)

        if min_confidence is not None:
            query = query.where(Question.confidence >= min_confidence)
            count_query = count_query.where(Question.confidence >= min_confidence)

        if max_confidence is not None:
            query = query.where(Question.confidence <= max_confidence)
            count_query = count_query.where(Question.confidence <= max_confidence)

        if question_type:
            query = query.where(Question.question_type == question_type)
            count_query = count_query.where(Question.question_type == question_type)

        if has_answer is True:
            query = query.where(Question.answer.isnot(None))
            count_query = count_query.where(Question.answer.isnot(None))
        elif has_answer is False:
            query = query.where(Question.answer.is_(None))
            count_query = count_query.where(Question.answer.is_(None))

        if needs_review is True:
            query = query.where(Question.extraction_status == "needs_review")
            count_query = count_query.where(Question.extraction_status == "needs_review")

        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one()

        # Sorting
        sort_col = getattr(Question, sort_by, Question.sequence_index)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def list_by_group(self, group_id: str) -> List[Question]:
        stmt = (
            select(Question)
            .where(Question.group_id == group_id)
            .order_by(Question.sequence_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: str) -> int:
        stmt = delete(Question).where(Question.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.rowcount
