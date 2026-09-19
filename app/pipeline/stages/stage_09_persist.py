from datetime import datetime, timezone
import io
from typing import Optional
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AnswerKey, Document, DocumentPage, ExtractionWarning, Question
from app.pipeline.context import PipelineContext
from app.storage import get_storage_backend


class PersistStage:
    @staticmethod
    async def execute(ctx: PipelineContext, session: AsyncSession) -> None:
        storage = get_storage_backend()
        now = datetime.now(timezone.utc)

        # 1. Idempotency cleanup: remove prior records for this document
        await session.execute(delete(DocumentPage).where(DocumentPage.document_id == ctx.document_id))
        await session.execute(delete(Question).where(Question.document_id == ctx.document_id))
        await session.execute(delete(AnswerKey).where(AnswerKey.document_id == ctx.document_id))
        await session.execute(delete(ExtractionWarning).where(ExtractionWarning.document_id == ctx.document_id))
        await session.flush()

        # 2. Persist Page Previews and Records
        for page in ctx.pages:
            image_key = None
            if page.image is not None:
                # Save page preview image to storage
                img_buf = io.BytesIO()
                page.image.save(img_buf, format="PNG")
                image_key = f"pages/{ctx.document_id}/page_{page.page_no}.png"
                await storage.save_bytes(img_buf.getvalue(), image_key, "image/png")
                page.image_key = image_key

            doc_page = DocumentPage(
                document_id=ctx.document_id,
                page_no=page.page_no,
                rotation_applied=page.rotation_applied,
                is_scanned=page.is_scanned,
                quality_score=page.quality_score,
                ocr_mean_confidence=page.ocr_mean_confidence,
                text_source=page.text_source,
                raw_text=page.raw_text,
                image_key=image_key,
                warnings=page.warnings,
            )
            session.add(doc_page)

        # 3. Persist Extracted Assets
        for asset in ctx.assets:
            if "bytes" in asset and asset["bytes"]:
                asset_key = f"assets/{ctx.document_id}/{asset['id']}.{asset.get('ext', 'png')}"
                await storage.save_bytes(asset["bytes"], asset_key, f"image/{asset.get('ext', 'png')}")
                asset["stored_key"] = asset_key
                asset["url"] = f"/api/v1/storage/{asset_key}"

        # 4. Persist Questions
        created_questions = []
        for q in ctx.final_questions:
            question_entity = Question(
                document_id=ctx.document_id,
                group_id=ctx.group_id,
                question_number=q.get("question_number"),
                sequence_index=q.get("sequence_index", 0),
                question_text=q.get("question_text", ""),
                question_type=q.get("question_type", "unknown"),
                options=q.get("options", []),
                answer=q.get("answer"),
                answer_match_status=q.get("answer_match_status", "not_found"),
                answer_source_page=q.get("answer_source_page"),
                source_pages=q.get("source_pages", []),
                source_bbox=q.get("source_bbox"),
                assets=q.get("assets", []),
                extraction_status=q.get("extraction_status", "success"),
                confidence=q.get("confidence", 0.0),
                confidence_breakdown=q.get("confidence_breakdown", {}),
                review_status="none",
                created_at=now,
            )
            session.add(question_entity)
            created_questions.append(question_entity)

        # 5. Persist Answer Keys
        if ctx.answer_keys:
            ak_entity = AnswerKey(
                document_id=ctx.document_id,
                group_id=ctx.group_id,
                entries=ctx.answer_keys,
                created_at=now,
            )
            session.add(ak_entity)

        # 6. Persist Warnings
        for w in ctx.warnings:
            warning_entity = ExtractionWarning(
                document_id=ctx.document_id,
                question_id=w.get("question_id"),
                page_no=w.get("page_no"),
                code=w["code"],
                severity=w.get("severity", "warning"),
                message=w["message"],
                details=w.get("details", {}),
                created_at=now,
            )
            session.add(warning_entity)

        # 7. Update Document Status
        has_warnings = any(w.get("severity") in ("warning", "error") for w in ctx.warnings)
        final_status = "completed_with_warnings" if has_warnings else "completed"

        await session.execute(
            update(Document)
            .where(Document.id == ctx.document_id)
            .values(
                status=final_status,
                progress_pct=100,
                current_stage="completed",
                page_count=ctx.page_count or len(ctx.pages),
                timings=ctx.timings,
                finished_at=now,
            )
        )
        await session.commit()
