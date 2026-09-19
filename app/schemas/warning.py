from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.question import SystemIndependentQuestion


class ExtractionWarningResponse(BaseModel):
    id: str
    document_id: str
    question_id: Optional[str] = None
    page_no: Optional[int] = None
    code: str
    severity: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewItemResponse(BaseModel):
    question: SystemIndependentQuestion
    reason: str
    warnings: List[ExtractionWarningResponse] = Field(default_factory=list)
