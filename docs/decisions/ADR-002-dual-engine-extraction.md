# ADR-002: Dual-Engine Question Structuring — Gemini LLM & Rule-Based Heuristic Parser

## Status
Accepted

## Context
Question papers and exam materials come in highly variable layouts: single-column, multi-column, numbered lists, nested sub-questions, inline options, table-based questions, and cross-page questions.
While Large Language Models (LLMs) like Gemini with multimodal vision and structured JSON output excel at understanding context and non-standard layouts, external LLMs pose challenges:
- Network latency and third-party API availability
- Rate limits and quotas
- Cost per page for large question banks
- Offline development and testing requirements (e.g. running test suites and CI without external network access or paid API keys)

## Decision
We implement a **Dual-Engine Structuring Architecture** following the Strategy Pattern:
1. **Primary Online Engine (`GeminiExtractionProvider`)**:
   - Uses the official `google-genai` SDK.
   - Enforces strict Pydantic JSON schema output (`response_schema`), ensuring zero hallucinated structure.
   - Operates on page text, layout bounding boxes, and cropped images.
2. **Deterministic Offline Engine (`RuleBasedExtractionProvider`)**:
   - Comprehensive regex engine recognizing 10+ question numbering families (`1.`, `(1)`, `Q1`, `Q.1`, `Question 1:`, `1)`, `a)`, `A.`, `(i)`).
   - Option boundary detectors for `(A)-(D)`, `a)-d)`, `(1)-(4)`, and inline single-line options.
   - Cross-page carry-over buffer for questions split across page boundaries.
   - Answer key parser for compact keys, tables, and section-prefixed patterns.
3. **Automated Circuit-Breaker & Fallback**:
   - If `LLM_ENABLED=false`, the rule-based engine is used directly.
   - If Gemini is enabled but encounters rate limits, timeouts, or network failures, the pipeline automatically falls back to the rule-based engine and attaches a warning (`LLM_FALLBACK_TRIGGERED`).

## Consequences
- The system is 100% functional offline and passes all automated tests without external network dependencies.
- High-volume production workloads can process clean digital PDFs via the rule-based parser at zero token cost, reserving Gemini for complex, unstructured scans.
