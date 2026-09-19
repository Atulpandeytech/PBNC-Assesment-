from typing import Any, Dict
from app.core.logging import logger
from app.pipeline.runner import PipelineRunner
from app.workers.locks import RedisLock


async def process_document_task(ctx: Dict[str, Any], document_id: str) -> bool:
    """Worker task executing the document processing pipeline under a distributed lock."""
    logger.info(f"Worker picked up document task: {document_id}")

    async with RedisLock(f"doc:{document_id}", ttl_seconds=600) as lock:
        if not lock.acquired:
            logger.warning(f"Document {document_id} is already locked by another worker. Skipping.")
            return False

        try:
            await PipelineRunner.run(document_id)
            return True
        except Exception as e:
            logger.error(f"Failed processing document {document_id} in worker: {e}")
            raise
