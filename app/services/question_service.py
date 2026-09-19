from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError, NotFoundError
from app.db.models import AuditLog, Question, User
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.question_repository import QuestionRepository
from app.schemas.question import (
    AnswerInfo,
    AssetInfo,
    OptionItem,
    QuestionReviewRequest,
    QuestionUpdateRequest,
    ReviewInfo,
    SourceInfo,
    SystemIndependentQuestion,
)
from app.storage import get_storage_backend


class QuestionService:
    def __init__(self, session: AsyncSession):
        self.q_repo = QuestionRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.session = session
        self.storage = get_storage_backend()

    async def list_questions(
        self,
        document_id: str,
        user: User,
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
    ) -> Tuple[List[SystemIndependentQuestion], int]:
        # Ownership check
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        entities, total = await self.q_repo.list_by_document(
            document_id=document_id,
            status=status,
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

        items = [self._to_schema(e, doc.original_filename) for e in entities]
        return items, total

    async def get_question(self, question_id: str, user: User) -> SystemIndependentQuestion:
        entity = await self.q_repo.get_with_details(question_id)
        if not entity:
            raise NotFoundError(f"Question '{question_id}' not found")

        doc = entity.document
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Question '{question_id}' not found")

        return self._to_schema(entity, doc.original_filename)

    async def update_question(
        self,
        question_id: str,
        req: QuestionUpdateRequest,
        user: User,
    ) -> SystemIndependentQuestion:
        entity = await self.q_repo.get_with_details(question_id)
        if not entity:
            raise NotFoundError(f"Question '{question_id}' not found")

        doc = entity.document
        if not doc or (doc.owner_id != user.id and user.role not in ("admin", "reviewer")):
            raise NotFoundError(f"Question '{question_id}' not found")

        # Record original value for audit trail
        original_value = {
            "question_number": entity.question_number,
            "question_text": entity.question_text,
            "question_type": entity.question_type,
            "options": entity.options,
            "answer": entity.answer,
        }

        now = datetime.now(timezone.utc)
        update_fields: Dict[str, Any] = {
            "review_status": "corrected",
            "reviewed_by": user.id,
            "reviewed_at": now,
        }

        if req.question_number is not None:
            update_fields["question_number"] = req.question_number
        if req.question_text is not None:
            update_fields["question_text"] = req.question_text
        if req.question_type is not None:
            update_fields["question_type"] = req.question_type
        if req.options is not None:
            update_fields["options"] = [opt.model_dump() for opt in req.options]
        if req.answer is not None:
            update_fields["answer"] = req.answer.model_dump()
            update_fields["answer_match_status"] = req.answer.match_status

        # Create audit log with JSON-safe dictionary
        audit_updates = {
            k: (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in update_fields.items()
        }
        audit = AuditLog(
            user_id=user.id,
            action="QUESTION_CORRECTION",
            resource=f"questions/{question_id}",
            details={"original": original_value, "updates": audit_updates, "notes": req.notes},
            at=now,
        )
        self.session.add(audit)

        await self.q_repo.update(question_id, **update_fields)
        await self.session.commit()

        updated_entity = await self.q_repo.get_with_details(question_id)
        schema = self._to_schema(updated_entity, doc.original_filename)
        schema.review.original_value = original_value
        schema.review.notes = req.notes
        return schema

    async def review_question(
        self,
        question_id: str,
        req: QuestionReviewRequest,
        user: User,
    ) -> SystemIndependentQuestion:
        entity = await self.q_repo.get_with_details(question_id)
        if not entity:
            raise NotFoundError(f"Question '{question_id}' not found")

        doc = entity.document
        if not doc or (doc.owner_id != user.id and user.role not in ("admin", "reviewer")):
            raise NotFoundError(f"Question '{question_id}' not found")

        action = req.action.lower()
        if action not in ("approve", "reject"):
            raise AppError("INVALID_ACTION", "Review action must be 'approve' or 'reject'", 400)

        review_status = "approved" if action == "approve" else "rejected"
        await self.q_repo.update(
            question_id,
            review_status=review_status,
            reviewed_by=user.id,
            reviewed_at=datetime.now(timezone.utc),
        )

        audit = AuditLog(
            user_id=user.id,
            action=f"QUESTION_{action.upper()}",
            resource=f"questions/{question_id}",
            details={"notes": req.notes},
            at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        await self.session.commit()

        updated_entity = await self.q_repo.get_with_details(question_id)
        return self._to_schema(updated_entity, doc.original_filename)

    async def export_questions(
        self,
        document_id: str,
        user: User,
        format_type: str = "json",
    ) -> Dict[str, Any]:
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")

        questions, _ = await self.q_repo.list_by_document(
            document_id=document_id,
            page=1,
            limit=1000,
        )

        q_schemas = [self._to_schema(q, doc.original_filename).model_dump() for q in questions]

        return {
            "schema_version": "1.0",
            "document_id": doc.id,
            "original_filename": doc.original_filename,
            "page_count": doc.page_count,
            "total_questions": len(q_schemas),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "questions": q_schemas,
        }

    def _to_schema(self, entity: Question, doc_name: str) -> SystemIndependentQuestion:
        # Options
        options = [
            OptionItem(
                label=opt.get("label", ""),
                text=opt.get("text", ""),
                image_key=opt.get("image_key"),
                asset_ids=opt.get("asset_ids", []),
            )
            for opt in (entity.options or [])
        ]

        # Answer
        answer = None
        if entity.answer:
            answer = AnswerInfo(
                value=entity.answer.get("value", []),
                raw=entity.answer.get("raw", ""),
                source_page=entity.answer.get("source_page"),
                match_status=entity.answer_match_status,
                confidence=entity.answer.get("confidence", 0.0),
            )

        # Assets
        assets = [
            AssetInfo(
                id=a.get("id", ""),
                type=a.get("type", "image"),
                page=a.get("page", 1),
                bbox=a.get("bbox"),
                url=a.get("url"),
                stored_key=a.get("stored_key"),
            )
            for a in (entity.assets or [])
        ]

        # Source
        source = SourceInfo(
            document=doc_name,
            pages=entity.source_pages or [1],
            bbox=entity.source_bbox,
        )

        # Review
        review = ReviewInfo(
            status=entity.review_status,
            reviewed_by=entity.reviewed_by,
            reviewed_at=entity.reviewed_at,
        )

        return SystemIndependentQuestion(
            id=entity.id,
            document_id=entity.document_id,
            group_id=entity.group_id,
            question_number=entity.question_number,
            sequence_index=entity.sequence_index,
            question_text=entity.question_text,
            question_type=entity.question_type,
            options=options,
            answer=answer,
            assets=assets,
            source=source,
            confidence=entity.confidence,
            confidence_breakdown=entity.confidence_breakdown or {},
            status=entity.extraction_status,
            warnings=[w.message for w in (entity.warnings or [])],
            review=review,
        )
