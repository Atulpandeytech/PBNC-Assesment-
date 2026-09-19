from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image


@dataclass
class PageData:
    page_no: int
    text_source: str = "native"  # "native" or "ocr"
    is_scanned: bool = False
    rotation_applied: int = 0
    quality_score: float = 1.0
    ocr_mean_confidence: float = 1.0
    raw_text: str = ""
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    image: Optional[Image.Image] = None
    image_key: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class PipelineContext:
    document_id: str
    owner_id: str
    file_path: Path
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    group_id: Optional[str] = None
    role_in_group: str = "unknown"

    # Ingested details
    page_count: int = 0
    pages: List[PageData] = field(default_factory=list)

    # Segmentation & Extraction results
    raw_questions: List[Dict[str, Any]] = field(default_factory=list)
    final_questions: List[Dict[str, Any]] = field(default_factory=list)
    answer_keys: List[Dict[str, Any]] = field(default_factory=list)
    orphan_answers: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    assets: List[Dict[str, Any]] = field(default_factory=list)

    # Progress & Timings
    current_stage: str = "initialized"
    progress_pct: int = 0
    timings: Dict[str, float] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def add_warning(
        self,
        code: str,
        message: str,
        severity: str = "warning",
        question_id: Optional[str] = None,
        page_no: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.warnings.append({
            "code": code,
            "message": message,
            "severity": severity,
            "question_id": question_id,
            "page_no": page_no,
            "details": details or {},
        })
