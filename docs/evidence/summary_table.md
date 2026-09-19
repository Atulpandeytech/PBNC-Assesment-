# Pragati Bharti Document Intelligence - System Demonstration & Verification Summary

All scenarios were executed against the live Pragati Bharti API and asynchronous pipeline.
All evidence files below represent genuine runs stored in `docs/evidence/` and `samples/output/`.

| Scenario | Target File / Feature | Status | Questions | Avg Conf | Time (s) | Key Verification Details |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| Scenario 1: Clean MCQ PDF | `1_clean_mcq.pdf` | **PASS** | 5 | 0.96 | 1.57s | All 5 questions extracted with answers matched from end-of-document key. |
| Scenario 2: Answer Key at Beginning | `2_answer_key_start.pdf` | **PASS** | 8 | 0.97 | 1.35s | Extracted 8 questions; answers matched from top table grid. |
| Scenario 3: Scanned Noisy PDF | `3_scanned_noisy.pdf` | **PASS** | 3 | 0.85 | 2.03s | OCR pipeline executed; image deskewed and preprocessed. |
| Scenario 4: Question Image PNG | `4_question_image.png` | **PASS** | 1 | 0.90 | 0.5s | Single image ingested; geometric diagram question identified. |
| Scenario 5: Cross-Page Question PDF | `6_cross_page.pdf` | **PASS** | 4 | 0.95 | 2.28s | Q3 stitched across page 1 and page 2; multi-page continuity preserved. |
| Scenario 6: Document Group Linking | `7_group_question_paper.pdf + 7_group_answer_key.pdf` | **PASS** | 8 | 0.95 | 3.43s | Cross-document answer key merging succeeded: 5 questions linked with external answers. |
| Scenario 7: Garbled Low-Quality Scan | `8_garbled_scan.pdf` | **PASS** | - | - | 3.63s | Low quality scan flagged with warnings and designated for human review. |
| Scenario 8: Human Review Workflow | `Review on 1_clean_mcq.pdf questions` | **PASS** | 3 | 1.00 | 0.26s | Reviewer approved Q1, edited text for Q2 (status=corrected), and rejected Q3 with notes. |
| Scenario 9: Security & IDOR Defense | `REST API Security Harness` | **PASS** | - | - | 0.07s | Verified 401 for unauth, 404 for IDOR asset enumeration, and authorized admin oversight. |
| Scenario 10: Robust Error Handling | `Invalid Files Test Suite` | **PASS** | - | - | 1.83s | Verified 400 DISGUISED_EXECUTABLE, 415 UNSUPPORTED_MEDIA_TYPE, and 413 PAYLOAD_TOO_LARGE. |
