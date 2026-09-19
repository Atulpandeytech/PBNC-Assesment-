from pathlib import Path
from app.pipeline.context import PageData, PipelineContext
from app.pipeline.stages.stage_05_segment import SegmentStage


def test_strip_repeated_headers_and_footers():
    ctx = PipelineContext(
        document_id="doc-seg-1",
        owner_id="user-1",
        file_path=Path("dummy.pdf"),
        original_filename="exam.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        sha256="abc",
    )

    header = "PRAGATI BHARTI PUBLIC SCHOOL - ANNUAL EXAM 2026"
    footer = "CONFIDENTIAL - DO NOT DISTRIBUTE"

    ctx.pages = [
        PageData(
            page_no=1,
            raw_text=f"{header}\n1. Question on page 1\n(A) opt1 (B) opt2\n{footer}"
        ),
        PageData(
            page_no=2,
            raw_text=f"{header}\n2. Question on page 2\n(A) opt1 (B) opt2\n{footer}"
        ),
        PageData(
            page_no=3,
            raw_text=f"{header}\n3. Question on page 3\n(A) opt1 (B) opt2\n{footer}"
        ),
    ]

    SegmentStage._strip_headers_and_footers(ctx)

    for p in ctx.pages:
        assert header not in p.raw_text
        assert footer not in p.raw_text
        assert "Question on page" in p.raw_text


def test_cross_page_carryover():
    ctx = PipelineContext(
        document_id="doc-seg-2",
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
            raw_text="1. What is the fundamental principle that governs the conservation of"
        ),
        PageData(
            page_no=2,
            raw_text="energy in an isolated thermodynamic system?\n(A) First Law\n(B) Second Law"
        ),
    ]

    SegmentStage._stitch_cross_page_carryover(ctx)

    assert any(w["code"] == "SPLIT_ACROSS_PAGES" for w in ctx.warnings)
