import asyncio
from typing import Optional
from arq.connections import RedisSettings, create_pool
from app.core.config import settings
from app.core.logging import logger
from app.workers.tasks import process_document_task

# ARQ Worker Settings
class WorkerSettings:
    functions = [process_document_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = settings.WORKER_CONCURRENCY
    job_timeout = 600  # 10 minutes max per document


_arq_pool = None
_arq_checked = False


async def get_arq_pool():
    global _arq_pool, _arq_checked
    if _arq_checked:
        return _arq_pool
    if settings.REDIS_URL:
        try:
            _arq_pool = await asyncio.wait_for(create_pool(WorkerSettings.redis_settings), timeout=0.8)
        except Exception as e:
            logger.warning(f"Could not connect to Redis for ARQ pool: {e}")
            _arq_pool = None
    _arq_checked = True
    return _arq_pool


async def enqueue_document_processing(document_id: str) -> None:
    """Enqueues document to ARQ Redis worker, or spawns async background task if Redis is unavailable."""
    if settings.APP_ENV == "test":
        logger.info(f"Test environment: skipping auto-enqueue for document {document_id}")
        return

    pool = await get_arq_pool()
    if pool:
        try:
            await pool.enqueue_job("process_document_task", document_id)
            logger.info(f"Enqueued document {document_id} to ARQ worker queue")
            return
        except Exception as e:
            logger.warning(f"Failed to enqueue to ARQ queue: {e}; falling back to in-process background execution")

    # Fallback to in-process asyncio task for local/test environments
    logger.info(f"Spawning in-process background task for document {document_id}")
    asyncio.create_task(process_document_task({}, document_id))
