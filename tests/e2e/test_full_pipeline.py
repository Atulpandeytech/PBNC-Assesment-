import io
from pathlib import Path
import pytest
from httpx import AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.pipeline.runner import PipelineRunner


def create_sample_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, "PRAGATI BHARTI PUBLIC SCHOOL")
    c.drawString(100, 720, "1. What is the chemical formula for water?")
    c.drawString(120, 700, "(A) H2O  (B) CO2  (C) NaCl  (D) CH4")
    c.drawString(100, 660, "2. Which gas do plants absorb during photosynthesis?")
    c.drawString(120, 640, "(A) Oxygen  (B) Nitrogen  (C) Carbon Dioxide  (D) Hydrogen")
    c.drawString(100, 600, "ANSWER KEY")
    c.drawString(100, 580, "1-A, 2-C")
    c.save()
    return buf.getvalue()


@pytest.mark.asyncio
async def test_full_pipeline_e2e(client: AsyncClient, test_user: User, user_token: str, db_session: AsyncSession):
    headers = {"Authorization": f"Bearer {user_token}"}
    pdf_bytes = create_sample_pdf_bytes()

    # 1. Upload via REST API
    files = {"file": ("test_exam_e2e.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = await client.post("/api/v1/documents", files=files, headers=headers)
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["document_id"]

    # 2. Run pipeline directly on document
    await PipelineRunner.run(doc_id, session=db_session)

    # 3. Retrieve status
    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["status"] in ("completed", "completed_with_warnings")
    assert st_data["progress_pct"] == 100

    # 4. Retrieve extracted questions
    q_res = await client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers)
    assert q_res.status_code == 200
    questions = q_res.json()["items"]
    assert len(questions) == 2

    # Verify Question 1
    q1 = next(q for q in questions if q["question_number"] == "1")
    assert "chemical formula for water" in q1["question_text"]
    assert len(q1["options"]) == 4
    assert q1["answer"]["value"] == ["A"]
    assert q1["confidence"] >= 0.80

    # Verify Question 2
    q2 = next(q for q in questions if q["question_number"] == "2")
    assert "photosynthesis" in q2["question_text"]
    assert q2["answer"]["value"] == ["C"]

    # 5. Export structured JSON
    export_res = await client.get(f"/api/v1/documents/{doc_id}/export", headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["schema_version"] == "1.0"
    assert export_data["total_questions"] == 2
