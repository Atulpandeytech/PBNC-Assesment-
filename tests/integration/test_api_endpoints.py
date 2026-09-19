import io
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.pipeline.runner import PipelineRunner


def create_minimal_pdf() -> bytes:
    # Minimal valid 1-page PDF
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n185\n%%EOF"


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    res_root = await client.get("/health")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "ok"

    res_live = await client.get("/api/v1/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] in ("ok", "live")

    res_ready = await client.get("/api/v1/health/ready")
    assert res_ready.status_code in (200, 503)

    res_metrics = await client.get("/api/v1/metrics")
    assert res_metrics.status_code == 200
    assert "pragati_documents_total" in res_metrics.text


@pytest.mark.asyncio
async def test_document_and_question_lifecycle(
    client: AsyncClient, test_user: User, user_token: str, reviewer_token: str, admin_token: str, db_session: AsyncSession
):
    headers = {"Authorization": f"Bearer {user_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    pdf_bytes = create_minimal_pdf()
    files = {"file": ("lifecycle_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res_up = await client.post("/api/v1/documents", files=files, headers=headers)
    assert res_up.status_code == 202
    doc_id = res_up.json()["document_id"]

    # Process pipeline
    await PipelineRunner.run(doc_id, session=db_session)

    # 1. Document details and listing
    res_get = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == doc_id

    res_list = await client.get("/api/v1/documents", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()["items"]) >= 1

    # 2. Pages endpoint
    res_pages = await client.get(f"/api/v1/documents/{doc_id}/pages", headers=headers)
    assert res_pages.status_code == 200
    assert len(res_pages.json()) >= 1

    # 3. Warnings endpoint
    res_warn = await client.get(f"/api/v1/documents/{doc_id}/warnings", headers=headers)
    assert res_warn.status_code == 200

    # 4. Answer key endpoint
    res_ak = await client.get(f"/api/v1/documents/{doc_id}/answer-key", headers=headers)
    assert res_ak.status_code in (200, 404)

    # 5. Reprocess document
    res_re = await client.post(f"/api/v1/documents/{doc_id}/reprocess", headers=headers)
    assert res_re.status_code == 200
    assert res_re.json()["status"] == "queued"

    # 6. Delete document
    res_del = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert res_del.status_code == 204

    # Confirm 404 after deletion
    res_del_get = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert res_del_get.status_code == 404


@pytest.mark.asyncio
async def test_group_lifecycle(client: AsyncClient, test_user: User, user_token: str):
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create Group
    res_create = await client.post("/api/v1/groups", json={"name": "Lifecycle Group"}, headers=headers)
    assert res_create.status_code == 201
    grp_id = res_create.json()["id"]

    # List Groups
    res_list = await client.get("/api/v1/groups", headers=headers)
    assert res_list.status_code == 200
    assert any(g["id"] == grp_id for g in res_list.json())

    # Get Group
    res_get = await client.get(f"/api/v1/groups/{grp_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Lifecycle Group"


@pytest.mark.asyncio
async def test_batch_upload(client: AsyncClient, test_user: User, user_token: str):
    headers = {"Authorization": f"Bearer {user_token}"}
    pdf1 = create_minimal_pdf()
    pdf2 = create_minimal_pdf() + b"\n%extra"

    files = [
        ("files", ("batch_1.pdf", io.BytesIO(pdf1), "application/pdf")),
        ("files", ("batch_2.pdf", io.BytesIO(pdf2), "application/pdf")),
    ]
    data = {"group_name": "Batch Upload Group"}

    res = await client.post("/api/v1/documents/batch", files=files, data=data, headers=headers)
    assert res.status_code == 202
    res_data = res.json()
    assert res_data["total_files"] == 2
    assert len(res_data["documents"]) == 2
    assert res_data["group_id"] is not None


@pytest.mark.asyncio
async def test_storage_and_question_review(
    client: AsyncClient, test_user: User, user_token: str, reviewer_token: str, db_session: AsyncSession
):
    headers = {"Authorization": f"Bearer {user_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, "1. What is 2 + 2?")
    c.drawString(100, 680, "(A) 3  (B) 4  (C) 5  (D) 6")
    c.save()

    files = {"file": ("math_test.pdf", io.BytesIO(buf.getvalue()), "application/pdf")}
    res_up = await client.post("/api/v1/documents", files=files, headers=headers)
    assert res_up.status_code == 202
    doc_id = res_up.json()["document_id"]
    await PipelineRunner.run(doc_id, session=db_session)

    # Questions list
    q_res = await client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers)
    assert q_res.status_code == 200
    qs = q_res.json()["items"]
    assert len(qs) >= 1
    q_id = qs[0]["id"]

    # Question detail
    det_res = await client.get(f"/api/v1/questions/{q_id}", headers=headers)
    assert det_res.status_code == 200

    # Question source preview
    src_res = await client.get(f"/api/v1/questions/{q_id}/source", headers=headers)
    assert src_res.status_code == 200

    # Review question
    rev_res = await client.post(
        f"/api/v1/questions/{q_id}/review",
        json={"action": "approve", "notes": "Verified"},
        headers=reviewer_headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["review"]["status"] == "approved"
