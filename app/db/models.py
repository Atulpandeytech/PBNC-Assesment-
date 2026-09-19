import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)  # admin, reviewer, user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    document_groups: Mapped[List["DocumentGroup"]] = relationship("DocumentGroup", back_populates="owner", cascade="all, delete-orphan")


class DocumentGroup(Base):
    __tablename__ = "document_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="document_groups")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="group", lazy="selectin")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="group", lazy="selectin")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    group_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    role_in_group: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)  # question_paper, answer_key, mixed, unknown
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", index=True, nullable=False)  # uploaded, queued, processing, completed, completed_with_warnings, failed
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("owner_id", "sha256", name="uq_documents_owner_sha256"),
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")
    group: Mapped[Optional["DocumentGroup"]] = relationship("DocumentGroup", back_populates="documents")
    pages: Mapped[List["DocumentPage"]] = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan", lazy="selectin")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="document", cascade="all, delete-orphan", lazy="selectin")
    answer_keys: Mapped[List["AnswerKey"]] = relationship("AnswerKey", back_populates="document", cascade="all, delete-orphan", lazy="selectin")
    warnings: Mapped[List["ExtractionWarning"]] = relationship("ExtractionWarning", back_populates="document", cascade="all, delete-orphan", lazy="selectin")
    jobs: Mapped[List["ProcessingJob"]] = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan", lazy="selectin")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    rotation_applied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ocr_mean_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    text_source: Mapped[str] = mapped_column(String(50), default="native", nullable=False)  # native, ocr
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    warnings: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    group_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    question_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    sequence_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)  # mcq_single, mcq_multi, true_false, fill_blank, short_answer, long_answer, match, numerical, unknown
    options: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)  # [{label, text, image_key}]
    answer: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # {value: [...], raw: "...", source_page: ..., match_status: ..., confidence: ...}
    answer_match_status: Mapped[str] = mapped_column(String(50), default="not_found", nullable=False)  # matched, ambiguous, unmatched, not_found
    answer_source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_pages: Mapped[List[int]] = mapped_column(JSON, default=list, nullable=False)
    source_bbox: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    assets: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(50), default="success", index=True, nullable=False)  # success, partial, needs_review
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default="none", index=True, nullable=False)  # none, pending, approved, corrected, rejected
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="questions", lazy="selectin")
    group: Mapped[Optional["DocumentGroup"]] = relationship("DocumentGroup", back_populates="questions", lazy="selectin")
    warnings: Mapped[List["ExtractionWarning"]] = relationship("ExtractionWarning", back_populates="question", cascade="all, delete-orphan", lazy="selectin")


class AnswerKey(Base):
    __tablename__ = "answer_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    group_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    entries: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)  # [{question_number, answer, source_page, confidence, raw_snippet}]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="answer_keys")


class ExtractionWarning(Base):
    __tablename__ = "extraction_warnings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    question_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=True, index=True)
    page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="warning", nullable=False)  # info, warning, error
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="warnings")
    question: Mapped[Optional["Question"]] = relationship("Question", back_populates="warnings")


class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    stage_timings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="jobs")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
