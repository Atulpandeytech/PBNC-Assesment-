from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str
    message: str = "Document uploaded successfully and queued for processing"
    duplicate: bool = False


class DocumentPageResponse(BaseModel):
    id: str
    document_id: str
    page_no: int
    rotation_applied: int
    is_scanned: bool
    quality_score: float
    ocr_mean_confidence: float
    text_source: str
    raw_text: Optional[str] = None
    image_url: Optional[str] = None
    warnings: List[Any] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: str
    owner_id: str
    group_id: Optional[str] = None
    role_in_group: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    page_count: int
    status: str
    progress_pct: int
    current_stage: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    current_stage: Optional[str] = None
    progress_pct: int
    timings: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
