import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.document import (
    DocumentPageResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.services.group_service import GroupService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/upload/", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    group_id: Optional[str] = Form(None),
    role_in_group: str = Form("unknown"),
    metadata: Optional[str] = Form(None),
    group_id_query: Optional[str] = Query(None, alias="group_id"),
    role_in_group_query: Optional[str] = Query(None, alias="role_in_group"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Upload an exam PDF or image (JPG/PNG).
    Returns immediately with HTTP 202 Accepted and a document ID for asynchronous background processing.
    """
    effective_group_id = group_id or group_id_query
    effective_role = role_in_group if role_in_group != "unknown" else (role_in_group_query or "unknown")

    doc_service = DocumentService(session)
    doc, is_duplicate = await doc_service.upload_document(
        file=file,
        user=current_user,
        group_id=effective_group_id,
        role_in_group=effective_role,
        metadata=metadata,
    )

    response = DocumentUploadResponse(
        document_id=doc.id,
        status=doc.status,
        message="Document uploaded and queued for processing" if not is_duplicate else "Duplicate document identified",
        duplicate=is_duplicate,
    )
    headers = {"X-Document-Duplicate": "true"} if is_duplicate else {}
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response.model_dump(), headers=headers)


@router.get("/upload")
@router.get("/upload/")
async def upload_document_help():
    """Friendly information endpoint for browser navigation to /upload."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ready",
            "message": "Document upload accepts multipart/form-data via HTTP POST.",
            "accepted_formats": [".pdf", ".png", ".jpg", ".jpeg"],
        },
    )


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    group_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Upload multiple files simultaneously and optionally auto-group them."""
    group_service = GroupService(session)
    doc_service = DocumentService(session)

    created_group = None
    group_id = None
    if group_name:
        created_group = await group_service.create_group(group_name, current_user)
        group_id = created_group.id

    uploaded_docs = []
    for f in files:
        fname = f.filename.lower() if f.filename else ""
        role = "unknown"
        if "answer" in fname or "key" in fname:
            role = "answer_key"
        elif "question" in fname or "paper" in fname:
            role = "question_paper"

        doc, is_dup = await doc_service.upload_document(
            file=f,
            user=current_user,
            group_id=group_id,
            role_in_group=role,
        )
        uploaded_docs.append({
            "document_id": doc.id,
            "filename": doc.original_filename,
            "role": role,
            "status": doc.status,
            "duplicate": is_dup,
        })

    return {
        "group_id": group_id,
        "group_name": group_name,
        "total_files": len(uploaded_docs),
        "documents": uploaded_docs,
    }


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve a paginated list of uploaded documents for the current user."""
    doc_service = DocumentService(session)
    items, total = await doc_service.list_documents(
        user=current_user, status=status_filter, page=page, limit=limit
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=[DocumentResponse.model_validate(doc) for doc in items],
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve metadata, current status, and stage timings for a specific document."""
    doc_service = DocumentService(session)
    doc = await doc_service.get_document(document_id, current_user)
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a document, its extracted pages, questions, and storage objects."""
    doc_service = DocumentService(session)
    await doc_service.delete_document(document_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Lightweight polling endpoint returning real-time progress percentage and current stage."""
    doc_service = DocumentService(session)
    doc = await doc_service.get_document(document_id, current_user)
    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status,
        current_stage=doc.current_stage,
        progress_pct=doc.progress_pct,
        timings=doc.timings or {},
        error_code=doc.error_code,
        error_message=doc.error_message,
    )


@router.post("/{document_id}/reprocess", response_model=DocumentStatusResponse)
async def reprocess_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Re-trigger the processing pipeline for an existing document."""
    doc_service = DocumentService(session)
    doc = await doc_service.reprocess_document(document_id, current_user)
    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status,
        current_stage=doc.current_stage,
        progress_pct=doc.progress_pct,
        timings=doc.timings or {},
        error_code=doc.error_code,
        error_message=doc.error_message,
    )


@router.get("/{document_id}/pages", response_model=List[DocumentPageResponse])
async def get_document_pages(
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve details, quality scores, and OCR confidence for all pages in the document."""
    doc_service = DocumentService(session)
    pages = await doc_service.get_pages(document_id, current_user)
    return [
        DocumentPageResponse(
            id=p.id,
            document_id=p.document_id,
            page_no=p.page_no,
            rotation_applied=p.rotation_applied,
            is_scanned=p.is_scanned,
            quality_score=p.quality_score,
            ocr_mean_confidence=p.ocr_mean_confidence,
            text_source=p.text_source,
            raw_text=p.raw_text,
            image_url=f"/api/v1/documents/{document_id}/pages/{p.page_no}/image" if p.image_key else None,
            warnings=p.warnings or [],
        )
        for p in pages
    ]


@router.get("/{document_id}/pages/{page_no}/image")
async def get_page_image(
    document_id: str,
    page_no: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Stream authorized page preview image for verification and review."""
    doc_service = DocumentService(session)
    img_bytes, mime_type = await doc_service.get_page_image(document_id, page_no, current_user)
    return Response(content=img_bytes, media_type=mime_type)
