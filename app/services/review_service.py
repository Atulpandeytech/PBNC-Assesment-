from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import NotFoundError
from app.db.models import ExtractionWarning, User
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.question_repository import QuestionRepository
from app.db.repositories.warning_repository import WarningRepository
from app.schemas.warning import ExtractionWarningResponse, ReviewItemResponse
from app.services.question_service import QuestionService


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.doc_repo = DocumentRepository(session)
        self.q_repo = QuestionRepository(session)
        self.warn_repo = WarningRepository(session)
        self.session = session

    async def list_document_warnings(
        self,
        document_id: str,
        user: User,
    ) -> List[ExtractionWarningResponse]:
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        warnings = await self.warn_repo.list_by_document(document_id)
        return [
            ExtractionWarningResponse(
                id=w.id,
                document_id=w.document_id,
                question_id=w.question_id,
                page_no=w.page_no,
                code=w.code,
                severity=w.severity,
                message=w.message,
                details=w.details or {},
                created_at=w.created_at,
            )
            for w in warnings
        ]

    async def list_review_items(
        self,
        document_id: str,
        user: User,
    ) -> List[ReviewItemResponse]:
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        q_service = QuestionService(self.session)
        questions, _ = await self.q_repo.list_by_document(
            document_id=document_id,
            needs_review=True,
            limit=500,
        )

        all_warnings = await self.warn_repo.list_by_document(document_id)
        warn_map = {}
        for w in all_warnings:
            if w.question_id:
                warn_map.setdefault(w.question_id, []).append(
                    ExtractionWarningResponse(
                        id=w.id,
                        document_id=w.document_id,
                        question_id=w.question_id,
                        page_no=w.page_no,
                        code=w.code,
                        severity=w.severity,
                        message=w.message,
                        details=w.details or {},
                        created_at=w.created_at,
                    )
                )

        review_items = []
        for q in questions:
            schema = q_service._to_schema(q, doc.original_filename)
            reason = "Low confidence score" if q.confidence < 0.60 else "Unmatched/ambiguous answer or missing options"
            review_items.append(
                ReviewItemResponse(
                    question=schema,
                    reason=reason,
                    warnings=warn_map.get(q.id, []),
                )
            )

        return review_items
