import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AnswerKey, Document, Question, User


@pytest.mark.asyncio
async def test_group_linking_and_answer_reconciliation(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    user_token: str,
):
    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Create a logical group
    grp_res = await client.post("/api/v1/groups", json={"name": "CBSE Grade 10 Science 2026"}, headers=headers)
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    # 2. Create Question Paper document
    qp_doc = Document(
        owner_id=test_user.id,
        group_id=group_id,
        role_in_group="question_paper",
        original_filename="Science_Question_Paper.pdf",
        stored_key="documents/qp.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
        sha256="sha_qp_123",
        status="completed",
        page_count=5,
    )
    db_session.add(qp_doc)
    await db_session.flush()

    # Add questions to question paper
    q1 = Question(
        document_id=qp_doc.id,
        group_id=group_id,
        question_number="1",
        sequence_index=1,
        question_text="What is the chemical formula of ozone?",
        question_type="mcq_single",
        options=[{"label": "A", "text": "O2"}, {"label": "B", "text": "O3"}],
        answer=None,
        answer_match_status="not_found",
        confidence=0.80,
    )
    q2 = Question(
        document_id=qp_doc.id,
        group_id=group_id,
        question_number="2",
        sequence_index=2,
        question_text="Name the powerhouse of the cell.",
        question_type="mcq_single",
        options=[{"label": "A", "text": "Mitochondria"}, {"label": "B", "text": "Ribosome"}],
        answer=None,
        answer_match_status="not_found",
        confidence=0.80,
    )
    db_session.add_all([q1, q2])

    # 3. Create separate Answer Key document
    ak_doc = Document(
        owner_id=test_user.id,
        group_id=group_id,
        role_in_group="answer_key",
        original_filename="Science_Answer_Key.pdf",
        stored_key="documents/ak.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="sha_ak_456",
        status="completed",
        page_count=1,
    )
    db_session.add(ak_doc)
    await db_session.flush()

    ak_entry = AnswerKey(
        document_id=ak_doc.id,
        group_id=group_id,
        entries=[
            {"question_number": "1", "answer": "B", "source_page": 1, "confidence": 0.98},
            {"question_number": "2", "answer": "A", "source_page": 1, "confidence": 0.98},
        ],
    )
    db_session.add(ak_entry)
    await db_session.commit()

    # 4. Request merged questions view from API
    res = await client.get(f"/api/v1/groups/{group_id}/questions", headers=headers)
    assert res.status_code == 200
    merged_data = res.json()
    assert merged_data["group_id"] == group_id
    assert merged_data["total_questions"] == 2

    # Verify answers from Answer Key document were reconciled into Question Paper questions
    q1_data = next(q for q in merged_data["questions"] if q["question_number"] == "1")
    assert q1_data["answer"]["value"] == ["B"]
    assert q1_data["answer"]["match_status"] == "matched"

    q2_data = next(q for q in merged_data["questions"] if q["question_number"] == "2")
    assert q2_data["answer"]["value"] == ["A"]
    assert q2_data["answer"]["match_status"] == "matched"
