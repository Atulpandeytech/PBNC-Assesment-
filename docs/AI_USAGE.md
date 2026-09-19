# Pragati Bharti Document Intelligence - AI & Model Transparency Report

## 1. Overview & Disclosure

The Pragati Bharti Question Extraction Service uses artificial intelligence and machine learning models to assist in converting unstructured, scanned, and digitized educational material into structured question banks.

To maintain transparency, security, and strict quality control, all AI and ML components operate under strict governance bounds:
1. **Zero Hallucination Mandate**: Temperature is locked to `0.0` for all LLM calls. Model outputs are strictly constrained by JSON schema enforcement.
2. **Dual-Engine Architecture**: AI inference is wrapped in a fail-safe fallback harness. If the AI model is unavailable, times out, or returns invalid schema, the local, air-gapped `RuleBasedExtractionProvider` takes over automatically with zero service interruption.
3. **Human-in-the-Loop (HITL)**: All questions extracted with low or moderate confidence ($< 0.85$) or generated from low-quality scans are flagged for human teacher/reviewer sign-off before being published to student examinations.
4. **No Training on Customer Data**: No user-uploaded exam papers, student answers, or proprietary materials are used to train foundation models.

---

## 2. Models & Technologies Deployed

| Component | Model / Engine | Provider / Library | Primary Purpose | Deployment Location |
|:---|:---|:---|:---|:---|
| **Primary Extraction Engine** | Gemini 2.5 Flash (`gemini-2.5-flash`) | Google Vertex AI / GenAI SDK | Multi-column understanding, mathematical formula transcription, question/option disambiguation | Cloud API (Stateless) |
| **Fallback Extraction Engine** | Rule-Based Heuristic Engine | Internal Python regex & topological line ordering | Deterministic parsing when offline, air-gapped, or under LLM rate limits | Local Worker Process |
| **Document Classification** | Laplacian Variance & Histogram Analysis | OpenCV (`cv2`) | Blur detection, image contrast calculation, page quality gating | Local Worker Process |
| **Image Preprocessing** | Deskew & Morphology Engine | OpenCV (`cv2`) | Text contour bounding, angle calculation, orientation correction | Local Worker Process |
| **Optical Character Recognition** | Native Media OCR / Tesseract-OCR v5 | Windows Native Media API / Google Tesseract | High-fidelity character recognition from raster scans | Local Container / OS Native |

---

## 3. Prompt Engineering & Schema Enforcement

When the LLM provider (`GeminiExtractionProvider`) is activated, it receives raw OCR text along with geometric bounding boxes. It does not generate free-form text; its response is strictly bound to the `ExtractionResponse` JSON schema.

### System Prompt Template

```text
You are an expert educational assessment parser and document intelligence system.
Your task is to analyze the OCR text and layout of an examination question paper and extract all questions into a clean, structured JSON format.

Input:
Text extracted from exam pages with line breaks preserved.

Extraction Rules:
1. Identify all individual questions regardless of numbering format (e.g., 1., Q1, (a), Section A Q.1).
2. For multiple-choice questions (MCQs), extract each option cleanly with its label (A, B, C, D or 1, 2, 3, 4).
3. If an answer key is present in the document, link the correct answer and explanation to each respective question.
4. If an answer is not present, leave correct_answer as null.
5. Classify each question into one of: 'mcq_single', 'mcq_multi', 'true_false', 'fill_blank', 'short_answer'.
6. Do NOT invent, hallucinate, or alter question text. Transcribe mathematical formulas, symbols, and punctuation accurately.
7. Return ONLY valid JSON adhering strictly to the provided output schema.
```

### Response Schema Enforcement (Pydantic v2)

The LLM is invoked using structured output mode (`response_mime_type="application/json"` and `response_schema=ExtractionResponse`). 

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ExtractionResponse",
  "type": "object",
  "properties": {
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "question_number": { "type": "integer" },
          "raw_label": { "type": "string" },
          "question_type": { "type": "string", "enum": ["mcq_single", "mcq_multi", "true_false", "fill_blank", "short_answer"] },
          "question_text": { "type": "string" },
          "options": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "key": { "type": "string" },
                "text": { "type": "string" }
              },
              "required": ["key", "text"]
            }
          },
          "correct_answer": { "type": ["string", "null"] },
          "explanation": { "type": ["string", "null"] }
        },
        "required": ["question_number", "question_type", "question_text", "options"]
      }
    },
    "answer_key_entries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "question_number": { "type": "integer" },
          "correct_option": { "type": "string" },
          "explanation": { "type": ["string", "null"] }
        },
        "required": ["question_number", "correct_option"]
      }
    }
  },
  "required": ["questions"]
}
```

---

## 4. Resilience & Circuit Breaker Design

To guarantee 99.9% pipeline availability, the extraction service implements an automated circuit breaker around external AI API calls.

```
       [ Stage 05: Preprocessed OCR Text ]
                       |
                       v
         [ Check GEMINI_API_KEY Configured? ]
                 /              \
        YES     /                \  NO
               v                  v
     [ Invoke Gemini 2.5 Flash ]   |
          |               |       |
      SUCCESS          TIMEOUT /  |
          |           429 / ERROR |
          |               |       |
          v               v       v
      [ JSON Schema ]  [ Automatic Fallback to ]
      [ Validation  ]  [ RuleBasedExtractionProvider ]
          |                       |
          +----------->+<---------+
                       |
                       v
         [ Stage 07: Answer Key Resolution ]
```

1. **Config Gating**: If `GEMINI_API_KEY` is empty, missing, or set to placeholder values, the pipeline skips network calls entirely and uses `RuleBasedExtractionProvider`.
2. **Timeout Bounds**: Network requests to LLM APIs have a strict 30-second timeout.
3. **Retry with Exponential Backoff**: Transient errors (HTTP 429 rate limits, 503 service unavailable) are retried up to 2 times with jittered exponential backoff.
4. **Silent Degradation**: If all retries fail, the exception is caught, logged with warning severity, and the fallback engine parses the document immediately without failing the pipeline.

---

## 5. Confidence Scoring & Hallucination Mitigation

The service does not blindly trust model outputs. Every extracted question is evaluated by a mathematical multi-signal confidence scorer in Stage 8:

$$\text{Confidence Score} = w_1 C_{\text{ocr}} + w_2 C_{\text{num}} + w_3 C_{\text{opts}} + w_4 C_{\text{ans}}$$

Where:
- $C_{\text{ocr}}$ ($w_1 = 0.35$): Mean OCR character confidence from native extraction.
- $C_{\text{num}}$ ($w_2 = 0.25$): Sequential question numbering continuity (penalizes skipped or duplicate question numbers).
- $C_{\text{opts}}$ ($w_3 = 0.20$): Option structure consistency (requires clean A, B, C, D or 1, 2, 3, 4 labels).
- $C_{\text{ans}}$ ($w_4 = 0.20$): Answer key alignment and confirmation.

### Confidence Tiers & Review Actions:
- **$\ge 0.85$ (High Confidence)**: Clean, high-fidelity extraction. Eligible for automated publishing.
- **$0.70 - 0.84$ (Moderate Confidence)**: Minor OCR noise or formatting anomaly. Enters review queue with status `pending`.
- **$< 0.70$ (Low Confidence)**: High noise, missing options, or numbering gaps. System automatically attaches a `QUALITY_WARNING` record, flagging specific fields requiring teacher intervention.

---

## 6. Human Review & Auditability

All modifications to AI-extracted questions are permanently tracked in the immutable `AuditLog` table.
- **Review Actions**: Reviewers can execute `approve`, `correct`, or `reject` on question candidates via the `/questions/{id}/review` endpoint.
- **Diff Tracking**: When a question is corrected, the pre-correction and post-correction values are serialized into `AuditLog.changes`, attributing the change to the reviewer's User ID and timestamp.
- **Explainability**: Bounding box coordinates (`[ymin, xmin, ymax, xmax]`) are attached to each question and option, allowing reviewers to click any field in the frontend UI and highlight the source snippet in the original document image.

---

## 7. Data Privacy & Security Guardrails

- **Zero Data Retention for Training**: The platform's agreements with cloud providers ensure that no data submitted via API endpoints is used to train, retrain, or improve machine learning models.
- **Multi-Tenant Data Scoping**: All questions, document metadata, and review logs are scoped strictly to the authenticated `tenant_id`. AI requests do not leak data across tenant boundaries.
- **Input Sanitization**: File uploads are screened for malicious payloads (disguised executables, decompression bombs) before any text is submitted to OCR or AI models.
