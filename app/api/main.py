from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.exception_handlers import (
    app_error_handler,
    generic_exception_handler,
    validation_error_handler,
)
from app.api.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.api.v1.answers import router as answers_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.groups import router as groups_router
from app.api.v1.health import router as health_router
from app.api.v1.questions import router as questions_router
from app.api.v1.storage import router as storage_router
from app.api.v1.warnings import router as warnings_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging
    setup_logging(settings.DEBUG)

    # In local SQLite development, ensure tables are created
    if "sqlite" in settings.DATABASE_URL:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup engine on shutdown
    await async_engine.dispose()


app = FastAPI(
    title="Pragati Bharti Document Intelligence API",
    version="1.0.0",
    description=(
        "Production-grade, scalable document intelligence and question extraction service for exam "
        "and question-bank material. Converts arbitrary PDF and image layouts into structured, "
        "machine-readable question banks with answers, bounding boxes, and confidence metrics."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

# Include v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(documents_router, prefix=api_v1_prefix)
app.include_router(questions_router, prefix=api_v1_prefix)
app.include_router(answers_router, prefix=api_v1_prefix)
app.include_router(warnings_router, prefix=api_v1_prefix)
app.include_router(groups_router, prefix=api_v1_prefix)
app.include_router(storage_router, prefix=api_v1_prefix)

# Mount Static UI Directory
static_dir = Path(__file__).resolve().parents[2] / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health", tags=["Health"])
async def root_health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["Root"])
async def root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "version": "1.0.0",
        "api_v1": "/api/v1",
    }
