from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from PIL import Image


class OCRResult:
    def __init__(
        self,
        text: str,
        mean_confidence: float = 1.0,
        word_boxes: Optional[List[Dict[str, Any]]] = None,
        rotation_detected: int = 0
    ):
        self.text = text
        self.mean_confidence = mean_confidence
        self.word_boxes = word_boxes or []
        self.rotation_detected = rotation_detected


class OCRProvider(ABC):
    @abstractmethod
    async def extract_page_ocr(self, image: Image.Image) -> OCRResult:
        """Run OCR on a PIL Image and return text with word confidences and rotation."""
        pass


class LLMStructuringProvider(ABC):
    @abstractmethod
    async def structure_questions(
        self,
        raw_text: str,
        page_numbers: List[int],
        images: Optional[List[Image.Image]] = None,
    ) -> List[Dict[str, Any]]:
        """Structure questions from page text and optional images."""
        pass
