from pathlib import Path
import pytest
from app.pipeline.context import PageData, PipelineContext
from app.pipeline.stages.stage_07_answer_key import AnswerKeyStage


def test_compact_answer_key_parsing():
    ctx = PipelineContext(
        document_id="doc-test-1",
        owner_id="user-1",
        file_path=Path("dummy.pdf"),
        original_filename="exam.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        sha256="abc",
    )

    ctx.pages = [
        PageData(
            page_no=1,
            raw_text="""
            ANSWER KEY
            1-A, 2-C, 3-D, 4-B, 5-A,C, 6-42.5
            """
        )
    ]

    ctx.final_questions = [
        {"question_number": "1", "question_text": "Q1 text"},
        {"question_number": "2", "question_text": "Q2 text"},
        {"question_number": "3", "question_text": "Q3 text"},
        {"question_number": "4", "question_text": "Q4 text"},
        {"question_number": "5", "question_text": "Q5 text"},
        {"question_number": "6", "question_text": "Q6 text"},
        {"question_number": "7", "question_text": "Q7 text with no answer"},
    ]

    AnswerKeyStage.execute(ctx)

    assert len(ctx.answer_keys) == 6
    assert ctx.final_questions[0]["answer"]["value"] == ["A"]
    assert ctx.final_questions[0]["answer_match_status"] == "matched"

    assert ctx.final_questions[1]["answer"]["value"] == ["C"]

    # Multi-answer check
    assert ctx.final_questions[4]["answer"]["value"] == ["A", "C"]

    # Numerical answer check
    assert ctx.final_questions[5]["answer"]["value"] == ["42.5"]

    # Unmatched question check
    assert ctx.final_questions[6]["answer"] is None
    assert ctx.final_questions[6]["answer_match_status"] == "not_found"


def test_table_answer_key_and_orphans():
    ctx = PipelineContext(
        document_id="doc-test-2",
        owner_id="user-1",
        file_path=Path("dummy.pdf"),
        original_filename="exam.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        sha256="abc",
    )

    ctx.pages = [
        PageData(
            page_no=1,
            raw_text="""
            | Q.No | Answer |
            | 1 | B |
            | 2 | D |
            | 99 | A |
            """
        )
    ]

    ctx.final_questions = [
        {"question_number": "1", "question_text": "Q1 text"},
        {"question_number": "2", "question_text": "Q2 text"},
    ]

    AnswerKeyStage.execute(ctx)

    assert ctx.final_questions[0]["answer"]["value"] == ["B"]
    assert ctx.final_questions[1]["answer"]["value"] == ["D"]

    # Orphan answer Q99
    assert len(ctx.orphan_answers) == 1
    assert ctx.orphan_answers[0]["question_number"] == "99"
    assert any(w["code"] == "ORPHAN_ANSWER" for w in ctx.warnings)
