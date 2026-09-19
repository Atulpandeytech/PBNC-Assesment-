import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import correlation_id_ctx
from app.core.rate_limit import check_rate_limit


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id_ctx.set(req_id)

        start_time = time.time()
        response: Response = await call_next(request)
        process_time = round(time.time() - start_time, 4)

        # Standard headers
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude docs and health checks from rate limiting
        path = request.url.path
        if path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/api/v1/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        await check_rate_limit(f"ip:{client_ip}")

        return await call_next(request)
