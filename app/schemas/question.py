from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class OptionItem(BaseModel):
    label: str  # e.g., "A", "B", "1", "a"
    text: str
    image_key: Optional[str] = None
    asset_ids: List[str] = Field(default_factory=list)


class AnswerInfo(BaseModel):
    value: List[str] = Field(default_factory=list)  # e.g. ["B"] or ["A", "C"]
    raw: str = ""
    source_page: Optional[int] = None
    match_status: str = "not_found"  # matched, ambiguous, unmatched, not_found
    confidence: float = 0.0


class AssetInfo(BaseModel):
    id: str
    type: str = "image"  # image, table, diagram
    page: int
    bbox: Optional[List[float]] = None
    url: Optional[str] = None
    stored_key: Optional[str] = None


class SourceInfo(BaseModel):
    document: Optional[str] = None
    pages: List[int] = Field(default_factory=list)
    bbox: Optional[List[float]] = None


class ReviewInfo(BaseModel):
    status: str = "none"  # none, pending, approved, corrected, rejected
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    original_value: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SystemIndependentQuestion(BaseModel):
    schema_version: str = "1.0"
    id: str
    document_id: str
    group_id: Optional[str] = None
    question_number: Optional[str] = None
    sequence_index: int = 0
    question_text: str
    question_type: str = "unknown"  # mcq_single, mcq_multi, true_false, fill_blank, short_answer, long_answer, match, numerical, unknown
    options: List[OptionItem] = Field(default_factory=list)
    answer: Optional[AnswerInfo] = None
    assets: List[AssetInfo] = Field(default_factory=list)
    source: SourceInfo
    confidence: float = 0.0
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict)
    status: str = "success"  # success, partial, needs_review
    warnings: List[str] = Field(default_factory=list)
    review: ReviewInfo = Field(default_factory=ReviewInfo)


class QuestionUpdateRequest(BaseModel):
    question_number: Optional[str] = None
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    options: Optional[List[OptionItem]] = None
    answer: Optional[AnswerInfo] = None
    notes: Optional[str] = None


class QuestionReviewRequest(BaseModel):
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = None
