import asyncio
import io
import time
import httpx
from app.pipeline.runner import PipelineRunner
from app.db.session import AsyncSessionLocal

BASE_URL = "http://127.0.0.1:8000"

async def run_verification():
    print("=== STARTING FULL FEATURE VERIFICATION ===")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Verify Static Files and UI Serving
        ui_res = await client.get("/")
        assert ui_res.status_code == 200, f"Root UI failed: {ui_res.status_code}"
        assert "Pragati Bharti" in ui_res.text, "Root UI missing Pragati Bharti"
        print(" [PASS] 1. Root UI static file served correctly.")

        js_api = await client.get("/static/js/api.js")
        assert js_api.status_code == 200, f"api.js failed: {js_api.status_code}"
        assert "getApiBase" in js_api.text, "api.js missing getApiBase"
        print(" [PASS] 2. Static js/api.js served correctly with dynamic getApiBase.")

        js_app = await client.get("/static/js/app.js")
        assert js_app.status_code == 200, f"app.js failed: {js_app.status_code}"
        assert "original_filename" in js_app.text, "app.js missing original_filename"
        print(" [PASS] 3. Static js/app.js served correctly with schema alignment.")

        # 2. Verify Health Probe
        health_res = await client.get("/api/v1/health/ready")
        assert health_res.status_code == 200, f"Health check failed: {health_res.status_code}"
        print(" [PASS] 4. Health readiness probe operational:", health_res.json()["status"])

        # 3. Verify /upload GET endpoint doesn't return 405 Method Not Allowed
        upload_get = await client.get("/api/v1/documents/upload")
        assert upload_get.status_code == 200, f"GET /upload failed: {upload_get.status_code}"
        print(" [PASS] 5. GET /documents/upload returns friendly 200 helper (No 405 Method Not Allowed).")

        # 4. Authentication (Login)
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "admin@pragatibharti.edu",
            "password": "AdminPass123!"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(" [PASS] 6. Authentication succeeded, JWT token obtained.")

        # 5. Document Upload via POST /api/v1/documents/upload
        with open("samples/input/1_clean_mcq.pdf", "rb") as f:
            pdf_bytes = f.read()

        files = {"file": ("test_exam_paper.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"metadata": '{"exam_name": "Class 10 Board Mock", "subject": "Science", "year": 2026}'}
        up_res = await client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
        assert up_res.status_code == 202, f"Upload failed: {up_res.text}"
        up_data = up_res.json()
        doc_id = up_data["document_id"]
        assert doc_id, "Missing document_id in upload response"
        print(f" [PASS] 7. POST /documents/upload succeeded with HTTP 202 Accepted. Doc ID: {doc_id}")

        # Wait a moment for pipeline background processing or run manually
        async with AsyncSessionLocal() as session:
            await PipelineRunner.run(doc_id, session=session)
        print(" [PASS] 8. Pipeline processing executed successfully.")

        # 6. Document Listing (verify original_filename and pagination)
        list_res = await client.get("/api/v1/documents?page=1&limit=20", headers=headers)
        assert list_res.status_code == 200, f"List documents failed: {list_res.status_code}"
        items = list_res.json()["items"]
        assert len(items) > 0, "No documents returned"
        match_doc = next((d for d in items if d["id"] == doc_id), None)
        assert match_doc, "Uploaded document not found in list"
        assert match_doc["original_filename"] in ("test_exam_paper.pdf", "1_clean_mcq.pdf"), f"Bad filename: {match_doc['original_filename']}"
        print(f" [PASS] 9. GET /documents returned original_filename: '{match_doc['original_filename']}' (Status: {match_doc['status']}).")

        # 7. Question Extraction Listing
        q_res = await client.get(f"/api/v1/documents/{doc_id}/questions?page=1&limit=50", headers=headers)
        assert q_res.status_code == 200, f"List questions failed: {q_res.status_code}"
        q_items = q_res.json()["items"]
        assert len(q_items) > 0, "No questions extracted from test PDF"
        q0 = q_items[0]
        q_id = q0["id"]
        assert "options" in q0, "Missing options in question"
        assert "answer" in q0, "Missing answer in question"
        assert "confidence" in q0, "Missing confidence in question"
        print(f" [PASS] 10. GET /documents/{{id}}/questions returned {len(q_items)} questions. First question ID: {q_id}")
        if q0["options"]:
            assert hasattr(q0["options"][0], "__getitem__") and "label" in q0["options"][0], "Option missing label"
            print(f"         First option label: {q0['options'][0]['label']}, Text: {q0['options'][0]['text']}")

        # 8. Question Update / Edit
        update_res = await client.patch(f"/api/v1/questions/{q_id}", json={
            "question_text": "Updated Question Text by Reviewer",
            "answer": {"value": ["B"], "raw": "B", "match_status": "matched", "confidence": 1.0},
            "notes": "Correction applied during review"
        }, headers=headers)
        assert update_res.status_code == 200, f"Question update failed: {update_res.text}"
        updated_q = update_res.json()
        assert updated_q["question_text"] == "Updated Question Text by Reviewer"
        assert updated_q["answer"]["value"] == ["B"]
        print(" [PASS] 11. PATCH /questions/{id} updated question and answer successfully.")

        # 9. Question Review Action (approve)
        review_res = await client.post(f"/api/v1/questions/{q_id}/review", json={
            "action": "approve",
            "notes": "Verified against physical question paper"
        }, headers=headers)
        assert review_res.status_code == 200, f"Review failed: {review_res.text}"
        assert review_res.json()["review"]["status"] == "approved"
        print(" [PASS] 12. POST /questions/{id}/review marked question as 'approved'.")

        # 10. Document Groups & Keys
        group_res = await client.post("/api/v1/groups", json={
            "name": "CBSE Science 2026 Set A Group",
            "description": "Question paper and standalone answer key pairing"
        }, headers=headers)
        assert group_res.status_code == 201, f"Create group failed: {group_res.text}"
        group_id = group_res.json()["id"]
        print(f" [PASS] 13. POST /groups created group '{group_id}'.")

        groups_list_res = await client.get("/api/v1/groups", headers=headers)
        assert groups_list_res.status_code == 200, f"List groups failed: {groups_list_res.status_code}"
        assert any(g["id"] == group_id for g in groups_list_res.json()), "Created group not in list"
        print(" [PASS] 14. GET /groups returned group list.")

        # 11. Group Merge Alias
        merge_res = await client.post(f"/api/v1/groups/{group_id}/merge", headers=headers)
        assert merge_res.status_code == 200, f"Merge group failed: {merge_res.text}"
        print(" [PASS] 15. POST /groups/{id}/merge alias executed successfully.")

        # 12. Quality Warnings
        warn_res = await client.get(f"/api/v1/documents/{doc_id}/warnings", headers=headers)
        assert warn_res.status_code == 200, f"Warnings failed: {warn_res.status_code}"
        print(f" [PASS] 16. GET /documents/{{id}}/warnings retrieved warnings ({len(warn_res.json())} items).")

        print("\n=== ALL 16 INTEGRATION VERIFICATIONS PASSED PERFECTLY ===")

if __name__ == "__main__":
    asyncio.run(run_verification())
