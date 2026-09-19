import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.logging import document_id_ctx, logger
from app.db.models import Document, DocumentGroup
from app.db.session import AsyncSessionLocal
from app.pipeline.context import PipelineContext
from app.pipeline.stages.stage_01_ingest import IngestStage
from app.pipeline.stages.stage_02_classify import ClassifyStage
from app.pipeline.stages.stage_03_preprocess import PreprocessStage
from app.pipeline.stages.stage_04_ocr_text import OCRTextStage
from app.pipeline.stages.stage_05_segment import SegmentStage
from app.pipeline.stages.stage_06_extract import ExtractStage
from app.pipeline.stages.stage_07_answer_key import AnswerKeyStage
from app.pipeline.stages.stage_08_validate import ValidateStage
from app.pipeline.stages.stage_09_persist import PersistStage
from app.storage import get_storage_backend


class PipelineRunner:
    @staticmethod
    async def run(document_id: str, session: Optional[AsyncSession] = None) -> PipelineContext:
        """Executes the complete document processing pipeline asynchronously and idempotently."""
        document_id_ctx.set(document_id)
        owns_session = session is None
        db = session or AsyncSessionLocal()

        try:
            # 1. Fetch document record
            stmt = select(Document).where(Document.id == document_id)
            res = await db.execute(stmt)
            doc_record = res.scalars().first()
            if not doc_record:
                raise AppError("DOCUMENT_NOT_FOUND", f"Document {document_id} not found in database", 404)

            # Update status to processing
            now = datetime.now(timezone.utc)
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status="processing",
                    current_stage="ingest",
                    progress_pct=10,
                    started_at=now,
                )
            )
            await db.commit()

            # Retrieve local file path from storage
            storage = get_storage_backend()
            file_path = await storage.get_local_path(doc_record.stored_key)

            ctx = PipelineContext(
                document_id=doc_record.id,
                owner_id=doc_record.owner_id,
                file_path=file_path,
                original_filename=doc_record.original_filename,
                mime_type=doc_record.mime_type,
                size_bytes=doc_record.size_bytes,
                sha256=doc_record.sha256,
                group_id=doc_record.group_id,
                role_in_group=doc_record.role_in_group,
            )

            # Stage 1: Ingest & Validate
            t0 = time.time()
            ctx.current_stage = "ingest"
            IngestStage.execute(ctx)
            ctx.timings["ingest"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "classify", 20)

            # Stage 2: Classify
            t0 = time.time()
            ctx.current_stage = "classify"
            ClassifyStage.execute(ctx)
            ctx.timings["classify"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "preprocess", 35)

            # Stage 3: Preprocess
            t0 = time.time()
            ctx.current_stage = "preprocess"
            PreprocessStage.execute(ctx)
            ctx.timings["preprocess"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "ocr_text", 50)

            # Stage 4: OCR & Layout
            t0 = time.time()
            ctx.current_stage = "ocr_text"
            await OCRTextStage.execute(ctx)
            ctx.timings["ocr_text"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "segment", 65)

            # Stage 5: Segment
            t0 = time.time()
            ctx.current_stage = "segment"
            SegmentStage.execute(ctx)
            ctx.timings["segment"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "extract", 75)

            # Stage 6: Extract
            t0 = time.time()
            ctx.current_stage = "extract"
            await ExtractStage.execute(ctx)
            ctx.timings["extract"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "answer_key", 85)

            # Stage 7: Answer Key
            t0 = time.time()
            ctx.current_stage = "answer_key"
            AnswerKeyStage.execute(ctx)
            ctx.timings["answer_key"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "validate", 90)

            # Stage 8: Validate & Confidence
            t0 = time.time()
            ctx.current_stage = "validate"
            ValidateStage.execute(ctx)
            ctx.timings["validate"] = round(time.time() - t0, 3)
            await PipelineRunner._update_progress(db, document_id, "persist", 95)

            # Stage 9: Persist
            t0 = time.time()
            ctx.current_stage = "persist"
            await PersistStage.execute(ctx, db)
            ctx.timings["persist"] = round(time.time() - t0, 3)
            ctx.timings["total"] = round(sum(ctx.timings.values()), 3)

            logger.info(f"Document {document_id} processed successfully in {ctx.timings['total']}s")

            # Check if group re-association is needed
            if ctx.group_id:
                from app.services.group_service import reconcile_group_answers
                await reconcile_group_answers(ctx.group_id, db)

            return ctx

        except Exception as e:
            code = getattr(e, "code", "PIPELINE_ERROR")
            msg = getattr(e, "message", str(e))
            logger.error(f"Document {document_id} pipeline failed at stage: {msg}", exc_info=True)

            try:
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        status="failed",
                        error_code=code,
                        error_message=msg,
                        finished_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
            except Exception:
                pass
            raise

        finally:
            if owns_session:
                await db.close()

    @staticmethod
    async def _update_progress(db: AsyncSession, document_id: str, stage: str, pct: int) -> None:
        try:
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(current_stage=stage, progress_pct=pct)
            )
            await db.commit()
        except Exception:
            pass
