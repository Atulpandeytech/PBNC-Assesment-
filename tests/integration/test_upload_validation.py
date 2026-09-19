import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_empty_file_rejected(client: AsyncClient, user_token: str):
    headers = {"Authorization": f"Bearer {user_token}"}
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    res = await client.post("/api/v1/documents", files=files, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_upload_unsupported_extension_rejected(client: AsyncClient, user_token: str):
    headers = {"Authorization": f"Bearer {user_token}"}
    files = {"file": ("notes.docx", io.BytesIO(b"fake word document content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = await client.post("/api/v1/documents", files=files, headers=headers)
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.asyncio
async def test_upload_valid_file_and_duplicate_detection(client: AsyncClient, user_token: str):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Minimal valid PDF
    pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n185\n%%EOF"

    # First upload
    files1 = {"file": ("test_exam.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res1 = await client.post("/api/v1/documents", files=files1, headers=headers)
    assert res1.status_code == 202
    data1 = res1.json()
    assert data1["duplicate"] is False
    doc_id = data1["document_id"]

    # Second upload of exact same bytes (idempotency check)
    files2 = {"file": ("test_exam.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res2 = await client.post("/api/v1/documents", files=files2, headers=headers)
    assert res2.status_code == 202
    data2 = res2.json()
    assert data2["duplicate"] is True
    assert data2["document_id"] == doc_id
    assert res2.headers.get("X-Document-Duplicate") == "true"
