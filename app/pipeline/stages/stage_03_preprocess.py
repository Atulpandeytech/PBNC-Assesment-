import cv2
import numpy as np
from PIL import Image
from app.pipeline.context import PipelineContext


class PreprocessStage:
    @staticmethod
    def execute(ctx: PipelineContext) -> None:
        for page in ctx.pages:
            if page.image is None:
                continue

            cv_img = cv2.cvtColor(np.array(page.image), cv2.COLOR_RGB2BGR)

            # Auto-deskew
            deskewed, angle = PreprocessStage._deskew(cv_img)
            if abs(angle) > 1.0:
                page.rotation_applied += int(angle)
                ctx.add_warning(
                    code="ROTATED_PAGE_CORRECTED",
                    message=f"Page {page.page_no} was rotated and corrected by {angle:.1f} degrees",
                    severity="info",
                    page_no=page.page_no,
                    details={"deskew_angle": angle},
                )

            # Check low resolution warning
            h, w = deskewed.shape[:2]
            if w < 600 or h < 800:
                ctx.add_warning(
                    code="LOW_RESOLUTION",
                    message=f"Page {page.page_no} has low resolution ({w}x{h}); OCR accuracy may be degraded",
                    severity="warning",
                    page_no=page.page_no,
                    details={"width": w, "height": h},
                )

            # Convert back to PIL Image
            clean_rgb = cv2.cvtColor(deskewed, cv2.COLOR_BGR2RGB)
            page.image = Image.fromarray(clean_rgb)

    @staticmethod
    def _deskew(cv_img: np.ndarray) -> tuple[np.ndarray, float]:
        """Detects skew angle and rotates image straight."""
        try:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            # Threshold to get dark pixels
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return cv_img, 0.0

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Only correct if skew is between -25 and 25 degrees
            if abs(angle) > 0.5 and abs(angle) < 25.0:
                (h, w) = cv_img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )
                return rotated, angle
            return cv_img, 0.0
        except Exception:
            return cv_img, 0.0
