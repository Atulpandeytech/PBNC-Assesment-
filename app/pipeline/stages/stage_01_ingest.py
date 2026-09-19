import os
from pathlib import Path
from PIL import Image
import pymupdf
from app.core.config import settings
from app.core.errors import AppError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.pipeline.context import PipelineContext

# Defend against decompression bombs
Image.MAX_IMAGE_PIXELS = 100_000_000

MAGIC_BYTES = {
    b"%PDF-": ("application/pdf", ".pdf"),
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
}


class IngestStage:
    @staticmethod
    def execute(ctx: PipelineContext) -> None:
        file_path = ctx.file_path
        if not file_path.exists() or not file_path.is_file():
            raise AppError("FILE_NOT_FOUND", "Uploaded file not found on disk", 404)

        size_bytes = file_path.stat().st_size
        if size_bytes == 0:
            raise AppError("EMPTY_FILE", "Uploaded file is empty (0 bytes)", 400)
        if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            raise PayloadTooLargeError(
                f"File size {size_bytes} exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes"
            )

        # Magic byte sniffing
        with open(file_path, "rb") as f:
            header = f.read(16)

        detected_mime = None
        for magic, (mime, ext) in MAGIC_BYTES.items():
            if header.startswith(magic):
                detected_mime = mime
                break

        if not detected_mime:
            # Check for disguised executables
            if header.startswith(b"MZ"):
                raise AppError("DISGUISED_EXECUTABLE", "Executable files are strictly rejected", 400)
            raise UnsupportedMediaTypeError(
                f"Unsupported file format. Supported formats: PDF, PNG, JPG/JPEG"
            )

        ctx.mime_type = detected_mime

        # PDF specific validation
        if detected_mime == "application/pdf":
            try:
                doc = pymupdf.open(file_path)
            except Exception as e:
                raise AppError("CORRUPT_FILE", f"Cannot parse PDF file: {e}", 400)

            try:
                if doc.is_encrypted:
                    raise AppError("PASSWORD_PROTECTED_PDF", "PDF is encrypted or password protected", 400)
                page_count = len(doc)
                if page_count == 0:
                    raise AppError("CORRUPT_FILE", "PDF contains 0 pages", 400)
                if page_count > settings.MAX_PAGE_COUNT:
                    raise AppError(
                        "MAX_PAGES_EXCEEDED",
                        f"PDF has {page_count} pages, exceeding maximum limit of {settings.MAX_PAGE_COUNT}",
                        400
                    )
                ctx.page_count = page_count
            finally:
                doc.close()
        else:
            # Image validation
            try:
                with Image.open(file_path) as img:
                    img.verify()
                    width, height = img.size
                    if width * height > Image.MAX_IMAGE_PIXELS:
                        raise AppError("DECOMPRESSION_BOMB", "Image dimensions exceed safety limits", 400)
                ctx.page_count = 1
            except AppError:
                raise
            except Exception as e:
                raise AppError("CORRUPT_FILE", f"Cannot parse image file: {e}", 400)
