import io
import pytest
from httpx import AsyncClient
from app.db.models import Document, Question, User
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_idor_protection_across_all_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    other_user: User,
    user_token: str,
    other_user_token: str,
):
    """
    CRITICAL SECURITY TEST:
    Proves User B (other_user) cannot read, inspect, modify, or delete User A's resources.
    Must return 404 Not Found (not 403 Forbidden) to eliminate IDOR resource enumeration.
    """
    # 1. Create a document owned by User A (test_user)
    doc_a = Document(
        owner_id=test_user.id,
        original_filename="user_a_exam.pdf",
        stored_key="documents/test/sample.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="sha256_user_a_doc",
        status="completed",
        progress_pct=100,
    )
    db_session.add(doc_a)
    await db_session.commit()
    await db_session.refresh(doc_a)

    # Add a question to doc_a
    q_a = Question(
        document_id=doc_a.id,
        question_number="1",
        question_text="Confidential Question of User A",
        question_type="short_answer",
        confidence=0.95,
        confidence_breakdown={},
    )
    db_session.add(q_a)
    await db_session.commit()
    await db_session.refresh(q_a)

    headers_b = {"Authorization": f"Bearer {other_user_token}"}

    # User B attempts to GET doc_a -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"

    # User B attempts to GET doc_a status -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}/status", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to GET doc_a pages -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}/pages", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to GET doc_a questions -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}/questions", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to GET doc_a warnings -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}/warnings", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to GET doc_a review items -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}/review-items", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to GET doc_a export -> 404
    res = await client.get(f"/api/v1/documents/{doc_a.id}/export", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to GET question q_a -> 404
    res = await client.get(f"/api/v1/questions/{q_a.id}", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to PATCH question q_a -> 404
    res = await client.patch(
        f"/api/v1/questions/{q_a.id}",
        json={"question_text": "Hacked Question"},
        headers=headers_b,
    )
    assert res.status_code == 404

    # User B attempts to DELETE doc_a -> 404
    res = await client.delete(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
    assert res.status_code == 404

    # User B attempts to reprocess doc_a -> 404
    res = await client.post(f"/api/v1/documents/{doc_a.id}/reprocess", headers=headers_b)
    assert res.status_code == 404

    # Verify User A CAN still access their own document
    headers_a = {"Authorization": f"Bearer {user_token}"}
    res_a = await client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == doc_a.id
