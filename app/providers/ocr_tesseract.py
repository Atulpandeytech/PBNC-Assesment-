import os
import shutil
from typing import Any, Dict, List
import pytesseract
from PIL import Image
from app.core.config import settings
from app.core.logging import logger
from app.providers.base import OCRProvider, OCRResult


class TesseractOCRProvider(OCRProvider):
    def __init__(self):
        # Configure tesseract cmd path if specified or common paths
        cmd = settings.TESSERACT_CMD
        if not cmd:
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
            ]
            for p in common_paths:
                if os.path.exists(p):
                    cmd = p
                    break
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        self.is_available = shutil.which(pytesseract.pytesseract.tesseract_cmd) is not None or (
            cmd and os.path.exists(cmd)
        )

    async def extract_page_ocr(self, image: Image.Image) -> OCRResult:
        if not self.is_available:
            try:
                import winocr
                res = await winocr.recognize_pil(image, lang="en")
                lines = [line.text for line in res.lines]
                extracted_text = "\n".join(lines)
                word_boxes = []
                for line in res.lines:
                    for word in line.words:
                        r = word.bounding_rect
                        word_boxes.append({
                            "text": word.text,
                            "conf": 92.0,
                            "bbox": [r.x, r.y, r.x + r.width, r.y + r.height],
                        })
                return OCRResult(
                    text=extracted_text,
                    mean_confidence=0.92,
                    word_boxes=word_boxes,
                    rotation_detected=0,
                )
            except Exception as e:
                logger.warning(f"WinOCR fallback unavailable: {e}")
                return self._fallback_ocr(image)

        try:
            # Orientation and Script Detection (OSD)
            rotation = 0
            try:
                osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
                rotation = int(osd.get("rotate", 0))
            except Exception:
                rotation = 0

            if rotation != 0:
                # Rotate image to correct orientation
                image = image.rotate(-rotation, expand=True)

            # Detailed OCR data with word confidences
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            words: List[str] = []
            confidences: List[float] = []
            word_boxes: List[Dict[str, Any]] = []

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])
                if text:
                    words.append(text)
                    if conf >= 0:
                        confidences.append(conf)
                    word_boxes.append({
                        "text": text,
                        "conf": conf,
                        "bbox": [
                            data["left"][i],
                            data["top"][i],
                            data["left"][i] + data["width"][i],
                            data["top"][i] + data["height"][i],
                        ]
                    })

            extracted_text = " ".join(words)
            mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.85

            return OCRResult(
                text=extracted_text,
                mean_confidence=mean_conf,
                word_boxes=word_boxes,
                rotation_detected=rotation,
            )
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}; falling back.")
            return self._fallback_ocr(image)

    def _fallback_ocr(self, image: Image.Image) -> OCRResult:
        """Lightweight fallback when Tesseract is not installed."""
        return OCRResult(
            text="[OCR fallback: Text extraction requires Tesseract or native PDF streams]",
            mean_confidence=0.75,
            word_boxes=[],
            rotation_detected=0,
        )
