import hashlib
import os
import uuid
from typing import BinaryIO, List, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppError, NotFoundError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.db.models import Document, DocumentPage, Question, User
from app.db.repositories.document_repository import DocumentRepository
from app.storage import get_storage_backend
from app.workers.worker import enqueue_document_processing

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


class DocumentService:
    def __init__(self, session: AsyncSession):
        self.doc_repo = DocumentRepository(session)
        self.session = session
        self.storage = get_storage_backend()

    async def upload_document(
        self,
        file: UploadFile,
        user: User,
        group_id: Optional[str] = None,
        role_in_group: str = "unknown",
        metadata: Optional[str] = None,
    ) -> Tuple[Document, bool]:
        filename = file.filename or "unnamed_document"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedMediaTypeError(
                f"File extension '{ext}' is not supported. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # Parse optional metadata
        meta_dict = {}
        if metadata:
            try:
                import json
                meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
            except Exception:
                meta_dict = {"raw": str(metadata)}

        # Stream file, compute SHA-256 and enforce size limit
        hasher = hashlib.sha256()
        chunks = []
        total_bytes = 0

        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                raise PayloadTooLargeError(
                    f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes"
                )
            hasher.update(chunk)
            chunks.append(chunk)

        if total_bytes == 0:
            raise AppError("EMPTY_FILE", "Uploaded file is empty (0 bytes)", 400)

        file_bytes = b"".join(chunks)

        # Magic byte sniffing to reject disguised executables or malformed headers
        if file_bytes.startswith(b"MZ"):
            raise AppError("DISGUISED_EXECUTABLE", "Executable files disguised as documents are strictly rejected", 400)
        if ext == ".pdf" and not file_bytes.startswith(b"%PDF-"):
            raise AppError("MAGIC_BYTE_MISMATCH", "Uploaded file lacks valid PDF header (%PDF-)", 400)
        if ext == ".png" and not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AppError("MAGIC_BYTE_MISMATCH", "Uploaded file lacks valid PNG header", 400)
        if ext in (".jpg", ".jpeg") and not file_bytes.startswith(b"\xff\xd8\xff"):
            raise AppError("MAGIC_BYTE_MISMATCH", "Uploaded file lacks valid JPEG header", 400)

        sha256_hash = hasher.hexdigest()

        # Check for duplicate upload by this user
        existing = await self.doc_repo.get_by_owner_and_sha256(user.id, sha256_hash)
        if existing:
            if group_id and existing.group_id != group_id:
                from sqlalchemy import update
                await self.doc_repo.update(existing.id, group_id=group_id, role_in_group=role_in_group)
                await self.session.execute(
                    update(Question).where(Question.document_id == existing.id).values(group_id=group_id)
                )
                await self.session.commit()
            return existing, True

        # Save to storage with randomized key
        doc_uuid = str(uuid.uuid4())
        stored_key = f"documents/{user.id}/{doc_uuid}{ext}"
        await self.storage.save_bytes(file_bytes, stored_key, file.content_type)

        # Create database record
        init_timings = {"metadata": meta_dict} if meta_dict else {}
        doc = await self.doc_repo.create(
            id=doc_uuid,
            owner_id=user.id,
            group_id=group_id,
            role_in_group=role_in_group,
            original_filename=filename,
            stored_key=stored_key,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=total_bytes,
            sha256=sha256_hash,
            page_count=0,
            status="queued",
            progress_pct=0,
            current_stage="queued",
            timings=init_timings,
        )
        await self.session.commit()

        # Enqueue background task
        await enqueue_document_processing(doc.id)

        return doc, False

    async def get_document(self, document_id: str, user: User) -> Document:
        # Return 404 for other user's document to prevent IDOR info leakage
        doc = await self.doc_repo.get(document_id)
        if not doc or (doc.owner_id != user.id and user.role != "admin"):
            raise NotFoundError(f"Document '{document_id}' not found")
        return doc

    async def list_documents(
        self,
        user: User,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        return await self.doc_repo.list_by_owner(user.id, status=status, page=page, limit=limit)

    async def delete_document(self, document_id: str, user: User) -> bool:
        doc = await self.get_document(document_id, user)
        # Delete file from storage
        await self.storage.delete(doc.stored_key)
        # Delete database row
        await self.doc_repo.delete(document_id)
        await self.session.commit()
        return True

    async def reprocess_document(self, document_id: str, user: User) -> Document:
        doc = await self.get_document(document_id, user)
        await self.doc_repo.update(
            document_id,
            status="queued",
            current_stage="queued",
            progress_pct=0,
            error_code=None,
            error_message=None,
        )
        await self.session.commit()
        await enqueue_document_processing(document_id)
        return await self.get_document(document_id, user)

    async def get_pages(self, document_id: str, user: User) -> List[DocumentPage]:
        await self.get_document(document_id, user)
        return await self.doc_repo.get_pages(document_id)

    async def get_page_image(self, document_id: str, page_no: int, user: User) -> Tuple[bytes, str]:
        await self.get_document(document_id, user)
        page = await self.doc_repo.get_page_by_number(document_id, page_no)
        if not page or not page.image_key:
            raise NotFoundError(f"Page image for page {page_no} not found")
        img_bytes = await self.storage.get_bytes(page.image_key)
        return img_bytes, "image/png"
