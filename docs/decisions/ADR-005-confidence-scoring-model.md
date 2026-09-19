# ADR-005: Multi-Signal Confidence Scoring Model & Review Architecture

## Status
Accepted

## Context
OCR and document extraction models produce varying levels of quality depending on scan resolution, skew, noise, font complexity, and document formatting. Downstream education systems cannot blindly trust unverified automated extractions. An automated extraction service must compute an objective, transparent confidence score for each question and automatically flag questionable items for human review.

## Decision
We establish a weighted multi-signal confidence model that computes an overall score between 0.0 and 1.0, accompanied by a structured `confidence_breakdown` JSON object:

### Scoring Components:
1. **OCR Mean Confidence ($W_1 = 0.25$)**: Average word-level confidence reported by Tesseract / PyMuPDF OCR on the source pages.
2. **Page Quality Score ($W_2 = 0.15$)**: Laplacian blur variance, contrast ratio, and image DPI.
3. **Numbering Continuity ($W_3 = 0.15$)**: Checks whether question numbers form a monotonic sequence ($Q_1, Q_2, Q_3...$) without unexpected gaps or duplicates.
4. **Option Completeness ($W_4 = 0.15$)**: For MCQ questions, validates presence of at least 2 (and ideally 4) options with non-empty text.
5. **Answer Key Match Certainty ($W_5 = 0.15$)**: Validates whether an answer was successfully resolved and matched from the answer key.
6. **Text Sanity & Cleanliness ($W_6 = 0.15$)**: Measures the ratio of non-printable / garbled characters and checks that question text is not truncated.

### Status Thresholds:
- **`success`**: $Confidence \ge 0.85$ (Ready for production delivery).
- **`partial`**: $0.60 \le Confidence < 0.85$ (Acceptable with minor caveats).
- **`needs_review`**: $Confidence < 0.60$ (Automatically routed to `/review-items` queue).

### Typed Warnings:
The system automatically generates structured warnings attached to questions or documents:
- `LOW_OCR_CONFIDENCE`, `MISSING_QUESTION_NUMBER`, `SPLIT_ACROSS_PAGES`
- `INCOMPLETE_OPTIONS`, `ANSWER_NOT_FOUND`, `ANSWER_AMBIGUOUS`
- `ORPHAN_ANSWER`, `ROTATED_PAGE_CORRECTED`, `LOW_RESOLUTION`
- `FIGURE_DETECTED`, `DUPLICATE_QUESTION`

## Consequences
- Every question clearly indicates its reliability.
- Human reviewers can query `GET /api/v1/documents/{id}/review-items` to focus only on items requiring attention.
- Reviewer corrections preserve an audit trail with original extracted values.
