from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnswerKeyEntrySchema(BaseModel):
    question_number: str
    answer: str
    source_page: Optional[int] = None
    confidence: float = 1.0
    raw_snippet: Optional[str] = None


class AnswerKeyResponse(BaseModel):
    id: str
    document_id: str
    group_id: Optional[str] = None
    entries: List[AnswerKeyEntrySchema] = Field(default_factory=list)
    matched_count: int = 0
    unmatched_count: int = 0
    orphan_count: int = 0
    orphans: List[AnswerKeyEntrySchema] = Field(default_factory=list)
    created_at: datetime
