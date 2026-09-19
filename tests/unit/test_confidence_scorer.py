from pathlib import Path
from app.pipeline.context import PageData, PipelineContext
from app.pipeline.stages.stage_08_validate import ValidateStage


def test_confidence_scoring_success():
    ctx = PipelineContext(
        document_id="doc-conf-1",
        owner_id="user-1",
        file_path=Path("dummy.pdf"),
        original_filename="exam.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        sha256="abc",
    )

    ctx.pages = [
        PageData(page_no=1, quality_score=0.95, ocr_mean_confidence=0.98)
    ]

    ctx.final_questions = [
        {
            "question_number": "1",
            "question_text": "What is the speed of sound in dry air at 20 degrees Celsius?",
            "question_type": "mcq_single",
            "options": [
                {"label": "A", "text": "343 m/s"},
                {"label": "B", "text": "300 m/s"},
                {"label": "C", "text": "1500 m/s"},
                {"label": "D", "text": "5000 m/s"},
            ],
            "answer_match_status": "matched",
            "source_pages": [1],
        }
    ]

    ValidateStage.execute(ctx)

    q = ctx.final_questions[0]
    assert q["confidence"] >= 0.85
    assert q["extraction_status"] == "success"
    assert "ocr_confidence" in q["confidence_breakdown"]
    assert "option_completeness" in q["confidence_breakdown"]


def test_confidence_scoring_needs_review():
    ctx = PipelineContext(
        document_id="doc-conf-2",
        owner_id="user-1",
        file_path=Path("dummy.pdf"),
        original_filename="exam.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        sha256="abc",
    )

    ctx.pages = [
        PageData(page_no=1, quality_score=0.40, ocr_mean_confidence=0.50)
    ]

    ctx.final_questions = [
        {
            "question_number": None,  # Missing question number
            "question_text": "##$$@@%% garbled OCR artifact ^^^&&*",
            "question_type": "mcq_single",
            "options": [{"label": "A", "text": "only one option"}],  # Incomplete options
            "answer_match_status": "not_found",
            "source_pages": [1],
        }
    ]

    ValidateStage.execute(ctx)

    q = ctx.final_questions[0]
    assert q["confidence"] < 0.60
    assert q["extraction_status"] == "needs_review"
    assert any(w["code"] == "MISSING_QUESTION_NUMBER" for w in ctx.warnings)
    assert any(w["code"] == "INCOMPLETE_OPTIONS" for w in ctx.warnings)
