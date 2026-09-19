from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError, NotFoundError
from app.db.models import AnswerKey, Document, DocumentGroup, Question, User
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.group_repository import GroupRepository
from app.db.repositories.question_repository import QuestionRepository
from app.schemas.group import DocumentGroupResponse, MergedQuestionsResponse
from app.schemas.question import SystemIndependentQuestion
from app.services.question_service import QuestionService


async def reconcile_group_answers(group_id: str, session: AsyncSession) -> None:
    """Reconciles answer keys across documents within the same group, regardless of upload order."""
    # Find all documents in group
    stmt = select(Document).where(Document.group_id == group_id)
    res = await session.execute(stmt)
    docs = list(res.scalars().all())
    if len(docs) < 2:
        return

    # Find answer key document or any document with answer key entries
    ak_doc = next((d for d in docs if d.role_in_group == "answer_key" or "answer" in d.original_filename.lower()), None)
    qp_doc = next((d for d in docs if d.role_in_group == "question_paper" or "question" in d.original_filename.lower()), None)

    if not ak_doc:
        # Check any doc that has answer keys
        stmt = select(AnswerKey).where(AnswerKey.group_id == group_id)
        res = await session.execute(stmt)
        ak = res.scalars().first()
        if ak:
            ak_doc = next((d for d in docs if d.id == ak.document_id), None)

    if not qp_doc and docs:
        # Default to first non-answer-key doc as question paper
        qp_doc = next((d for d in docs if d != ak_doc), None)

    if not ak_doc or not qp_doc:
        return

    # Fetch answer keys
    stmt = select(AnswerKey).where(AnswerKey.document_id == ak_doc.id)
    res = await session.execute(stmt)
    ak_record = res.scalars().first()
    if not ak_record or not ak_record.entries:
        return

    key_map = {e["question_number"]: e for e in ak_record.entries}

    # Fetch questions for question paper document
    stmt = select(Question).where(Question.document_id == qp_doc.id)
    res = await session.execute(stmt)
    questions = list(res.scalars().all())

    for q in questions:
        q_num = q.question_number
        if q_num and q_num in key_map:
            entry = key_map[q_num]
            ans_str = entry["answer"]
            values = [v.strip() for v in ans_str.split(",") if v.strip()]
            q.answer = {
                "value": values,
                "raw": entry.get("raw_snippet", ans_str),
                "source_page": entry.get("source_page"),
                "match_status": "matched",
                "confidence": entry.get("confidence", 0.95),
            }
            q.answer_match_status = "matched"
            q.answer_source_page = entry.get("source_page")
            # Boost confidence since answer is now verified
            q.confidence = min(1.0, round(q.confidence + 0.10, 3))
            if q.confidence >= 0.85:
                q.extraction_status = "success"

    await session.commit()


class GroupService:
    def __init__(self, session: AsyncSession):
        self.group_repo = GroupRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.q_repo = QuestionRepository(session)
        self.session = session

    async def create_group(self, name: str, user: User) -> DocumentGroup:
        group = await self.group_repo.create(owner_id=user.id, name=name)
        await self.session.commit()
        return group

    async def list_groups(self, user: User) -> List[DocumentGroup]:
        return await self.group_repo.list_by_owner(user.id)

    async def get_group(self, group_id: str, user: User) -> DocumentGroup:
        group = await self.group_repo.get_with_documents(group_id)
        if not group or (group.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Group '{group_id}' not found")
        return group

    async def attach_document(
        self,
        group_id: str,
        document_id: str,
        role: str,
        user: User,
    ) -> Document:
        await self.get_group(group_id, user)
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        await self.doc_repo.update(document_id, group_id=group_id, role_in_group=role)
        # Also update group_id on all questions belonging to this doc
        await self.session.execute(
            update(Question).where(Question.document_id == document_id).values(group_id=group_id)
        )
        await self.session.commit()

        # Reconcile answers across group
        await reconcile_group_answers(group_id, self.session)

        return await self.doc_repo.get(document_id)

    async def detach_document(self, group_id: str, document_id: str, user: User) -> bool:
        await self.get_group(group_id, user)
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        await self.doc_repo.update(document_id, group_id=None, role_in_group="unknown")
        await self.session.execute(
            update(Question).where(Question.document_id == document_id).values(group_id=None)
        )
        await self.session.commit()
        return True

    async def get_merged_questions(self, group_id: str, user: User) -> MergedQuestionsResponse:
        group = await self.get_group(group_id, user)

        # Trigger reconciliation to guarantee latest answer mappings
        await reconcile_group_answers(group_id, self.session)

        q_service = QuestionService(self.session)
        questions = await self.q_repo.list_by_group(group_id)

        qp_doc = next((d for d in group.documents if d.role_in_group == "question_paper"), None)
        ak_doc = next((d for d in group.documents if d.role_in_group == "answer_key"), None)

        doc_name_map = {d.id: d.original_filename for d in group.documents}
        q_schemas = [
            q_service._to_schema(q, doc_name_map.get(q.document_id, "unknown.pdf"))
            for q in questions
        ]

        return MergedQuestionsResponse(
            group_id=group.id,
            group_name=group.name,
            question_paper_document_id=qp_doc.id if qp_doc else None,
            answer_key_document_id=ak_doc.id if ak_doc else None,
            total_questions=len(q_schemas),
            questions=q_schemas,
        )
