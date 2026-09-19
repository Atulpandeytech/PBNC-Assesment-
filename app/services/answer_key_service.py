from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import NotFoundError
from app.db.models import User
from app.db.repositories.answer_key_repository import AnswerKeyRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.question_repository import QuestionRepository
from app.schemas.answer_key import AnswerKeyEntrySchema, AnswerKeyResponse
from app.schemas.question import AnswerInfo


class AnswerKeyService:
    def __init__(self, session: AsyncSession):
        self.ak_repo = AnswerKeyRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.q_repo = QuestionRepository(session)
        self.session = session

    async def get_document_answer_key(self, document_id: str, user: User) -> AnswerKeyResponse:
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        ak = await self.ak_repo.get_by_document(document_id)
        if not ak:
            raise NotFoundError(f"No answer key found for document '{document_id}'")

        entries = [
            AnswerKeyEntrySchema(
                question_number=e["question_number"],
                answer=e["answer"],
                source_page=e.get("source_page"),
                confidence=e.get("confidence", 1.0),
                raw_snippet=e.get("raw_snippet"),
            )
            for e in (ak.entries or [])
        ]

        # Calculate matches
        questions, _ = await self.q_repo.list_by_document(document_id, limit=1000)
        q_nums = {q.question_number for q in questions if q.question_number}

        matched = sum(1 for e in entries if e.question_number in q_nums)
        orphans = [e for e in entries if e.question_number not in q_nums]

        return AnswerKeyResponse(
            id=ak.id,
            document_id=ak.document_id,
            group_id=ak.group_id,
            entries=entries,
            matched_count=matched,
            unmatched_count=len(q_nums) - matched,
            orphan_count=len(orphans),
            orphans=orphans,
            created_at=ak.created_at,
        )

    async def get_question_answer(self, question_id: str, user: User) -> AnswerInfo:
        q = await self.q_repo.get_with_details(question_id)
        if not q or not q.document or (q.document.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Question '{question_id}' not found")

        if not q.answer:
            raise NotFoundError(f"No answer available for question '{question_id}'")

        return AnswerInfo(
            value=q.answer.get("value", []),
            raw=q.answer.get("raw", ""),
            source_page=q.answer.get("source_page"),
            match_status=q.answer_match_status,
            confidence=q.answer.get("confidence", 0.0),
        )
