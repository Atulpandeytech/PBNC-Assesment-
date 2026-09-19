from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.document import DocumentResponse
from app.schemas.question import SystemIndependentQuestion


class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class AttachDocumentRequest(BaseModel):
    document_id: str
    role: str = Field("unknown", description="question_paper, answer_key, mixed, unknown")


class DocumentGroupResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    created_at: datetime
    documents: List[DocumentResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MergedQuestionsResponse(BaseModel):
    group_id: str
    group_name: str
    question_paper_document_id: Optional[str] = None
    answer_key_document_id: Optional[str] = None
    total_questions: int
    questions: List[SystemIndependentQuestion] = Field(default_factory=list)
