import io
import cv2
import numpy as np
from PIL import Image
import pymupdf
from app.pipeline.context import PageData, PipelineContext


class ClassifyStage:
    @staticmethod
    def execute(ctx: PipelineContext) -> None:
        if ctx.mime_type == "application/pdf":
            doc = pymupdf.open(ctx.file_path)
            try:
                for i in range(len(doc)):
                    page = doc[i]
                    text = page.get_text()
                    char_count = len(text.strip())

                    # Rasterize page at 300 DPI for quality scoring and fallback OCR
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

                    # Compute blur & contrast quality
                    quality_score = ClassifyStage._compute_image_quality(pil_img)

                    # Text density heuristic
                    is_scanned = char_count < 50
                    text_source = "ocr" if is_scanned else "native"

                    ctx.pages.append(PageData(
                        page_no=i + 1,
                        text_source=text_source,
                        is_scanned=is_scanned,
                        quality_score=quality_score,
                        raw_text=text if not is_scanned else "",
                        image=pil_img,
                    ))
            finally:
                doc.close()
        else:
            # Single image file
            pil_img = Image.open(ctx.file_path).convert("RGB")
            quality_score = ClassifyStage._compute_image_quality(pil_img)

            ctx.pages.append(PageData(
                page_no=1,
                text_source="ocr",
                is_scanned=True,
                quality_score=quality_score,
                raw_text="",
                image=pil_img,
            ))

    @staticmethod
    def _compute_image_quality(img: Image.Image) -> float:
        """Calculates normalized quality score based on Laplacian variance (blur) and contrast."""
        try:
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

            # Laplacian blur variance
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Standard sharp image has lap_var > 100, blur < 50
            blur_score = min(1.0, max(0.2, lap_var / 300.0))

            # Contrast score (standard deviation of gray pixel values)
            contrast = gray.std()
            contrast_score = min(1.0, max(0.3, contrast / 60.0))

            return round(0.6 * blur_score + 0.4 * contrast_score, 3)
        except Exception:
            return 0.85
