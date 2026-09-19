import time
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.rate_limit import get_redis_client
from app.db.session import get_db

router = APIRouter(tags=["Health & Monitoring"])


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Kubernetes / Docker liveness probe: verifies process is alive and responsive."""
    return {"status": "ok", "timestamp": time.time()}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(
    session: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """Readiness probe: verifies active database and Redis connectivity."""
    checks = {}

    # Check DB
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Check Redis
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "disabled_or_local"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    is_ready = checks.get("database") == "healthy"
    if not is_ready and response:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "timestamp": time.time(),
    }


@router.get("/metrics")
async def prometheus_metrics(
    session: AsyncSession = Depends(get_db),
):
    """Prometheus-compatible plain text metrics endpoint."""
    total_docs = 0
    completed_docs = 0
    failed_docs = 0

    try:
        res = await session.execute(text("SELECT status, count(*) FROM documents GROUP BY status"))
        for row in res.fetchall():
            st, cnt = row[0], row[1]
            total_docs += cnt
            if st in ("completed", "completed_with_warnings"):
                completed_docs += cnt
            elif st == "failed":
                failed_docs += cnt
    except Exception:
        pass

    lines = [
        "# HELP pragati_documents_total Total documents uploaded",
        "# TYPE pragati_documents_total counter",
        f"pragati_documents_total {total_docs}",
        "# HELP pragati_documents_completed Total documents completed successfully",
        "# TYPE pragati_documents_completed counter",
        f"pragati_documents_completed {completed_docs}",
        "# HELP pragati_documents_failed Total documents failed",
        "# TYPE pragati_documents_failed counter",
        f"pragati_documents_failed {failed_docs}",
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
