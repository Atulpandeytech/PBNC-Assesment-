# ADR-001: Asynchronous Worker Architecture — ARQ with Redis

## Status
Accepted

## Context
The Document Intelligence & Question Extraction Service requires asynchronous, decoupled processing for CPU- and I/O-intensive document pipelines. When an exam PDF or image is uploaded, the API must respond immediately with HTTP 202 Accepted and a document ID, delegating processing to background worker processes.

The tech stack comprises Python 3.11+, FastAPI (asynchronous ASGI framework), SQLAlchemy 2.0 (asyncio with asyncpg and aiosqlite), and Redis. We needed to choose between **Celery** and **ARQ** for task queuing and worker execution.

## Decision
We select **ARQ** (asyncio-native job queue backed by Redis) as our primary worker system, while exposing an abstraction layer for task queuing.

### Rationale
1. **Native Async Integration**: ARQ functions are native coroutines (`async def`). In our stack, database queries, file storage I/O, external LLM calls (via httpx / google-genai), and Redis operations are 100% asynchronous. Celery is historically built around synchronous workers (prefork / eventlet / gevent / threads). Running async SQLAlchemy 2.0 code in Celery requires wrapping every task in `asyncio.run()`, risking event loop teardown issues, thread contention, and connection pool leaks.
2. **Cross-Platform Reliability**: Celery's default `prefork` pool is unsupported on Windows (`fork()` does not exist). Windows Celery workers must use `--pool=solo` or `--pool=threads`, introducing execution caveats. ARQ uses standard Python `asyncio` which executes uniformly across Linux containers and Windows host environments.
3. **Operational Simplicity**: ARQ relies directly on Redis streams / lists without requiring extra AMQP brokers (like RabbitMQ) or complex result-backend configurations.
4. **Resilience & Progress Reporting**: ARQ provides native job retry policies, exponential backoff, health checks, and task cancellation hooks that map cleanly to our document pipeline's stages and progress percentage tracking.

## Consequences
- Workers must be spawned using `arq app.workers.worker.WorkerSettings`.
- Tasks have bounded concurrency managed via ARQ's `max_jobs` setting, preventing memory exhaustion when multiple 100-page PDFs are processed in parallel.
- Celery compatibility is documented for enterprise deployments requiring AMQP brokers.
