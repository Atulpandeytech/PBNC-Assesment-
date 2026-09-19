# Pragati Bharti: Document Intelligence & Question Extraction Service

[![Python](https://img.shields.io/badge/Python-3.11%2B%20%7C%203.14-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://sqlalchemy.org)
[![Test Coverage](https://img.shields.io/badge/Coverage-80%25-brightgreen.svg)](tests/)
[![Tests](https://img.shields.io/badge/Tests-22%20Passed%20%7C%200%20Failed-success.svg)](tests/)
[![License](https://img.shields.io/badge/License-Proprietary-orange.svg)](#)

> A production-grade, asynchronous document intelligence platform for education. Converts unstructured PDFs and images of exam material into structured, machine-readable JSON questions exposed via a hardened FastAPI REST API.

---

## 1. Key Capabilities

- **Arbitrary Layout Handling**: Ingests single-column, multi-column (with gutter detection), cross-page questions, embedded diagrams/tables, and noisy scans without relying on fixed templates.
- **Versatile Numbering Schemes**: Seamlessly recognizes question prefixes such as `1.`, `Q.1`, `Question 1`, `(1)`, `a)`, `(i)`, and roman numerals.
- **Flexible Answer Key Placements**: Resolves answer keys placed at the start, at the end, or across separate standalone answer key documents with question-to-answer pairing.
- **9-Stage Extraction Pipeline**: Modular, resilient processing with OpenCV deskew, auto-rotation, Laplacian blur scoring, native OCR, topological line sorting, and multi-signal confidence calculation.
- **Dual Extraction Provider**: Primary extraction via Google Gemini 2.5 Flash with structured JSON schema constraints, backed by an air-gapped deterministic fallback parser (`RuleBasedExtractionProvider`).
- **Security & Multi-Tenant IDOR Defense**: Multi-tenant isolation at the query level. Cross-tenant access returns `404 Not Found` (preventing IDOR asset enumeration), with magic-byte sniffing (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`), disguised executable rejection (`MZ` header), and decompression bomb guards (`100M` pixels).
- **Human-in-the-Loop Review Workflow**: Reviewers can approve, correct, or reject extracted questions with full before/after audit tracking and bounding box coordinates.
- **Cross-Document Group Merging**: Pairs question paper documents with external answer key files via `/groups/{id}/merge`.
- **Multi-Format Export**: One-click export to normalized JSON, tabular CSV, or formatted DOCX.

---

## 2. Architecture Overview

```
                      +------------------------------------------+
                      |         FastAPI REST API Gateway         |
                      |  - JWT Auth, RBAC & Multi-Tenant Guard   |
                      |  - Magic Byte Sniffing & Anti-Exploit    |
                      |  - Prometheus Instrumentation (/metrics) |
                      +--------------------+---------------------+
                                           |
                                  +--------+--------+
                                  |                 |
                                  v                 v
                      +-------------------+   +--------------------+
                      |    Redis / ARQ    |   | PostgreSQL /       |
                      | Distributed Lock  |   | SQLite (Async)     |
                      +---------+---------+   +---------+----------+
                                |                       ^
                                v                       |
                      +---------------------------------+----------+
                      |     9-STAGE ASYNC WORKER PIPELINE          |
                      |  1. Ingestion & Magic Sniffing (SHA-256)   |
                      |  2. Classification & Blur/Contrast Check   |
                      |  3. Preprocessing (Deskew, Denoise)        |
                      |  4. Optical Character Recognition (OCR)    |
                      |  5. Semantic Segmentation & Gutters        |
                      |  6. Dual Extraction (Gemini / Heuristic)   |
                      |  7. Answer Key Resolution & Matching       |
                      |  8. Quality Validation & Multi-Signal Conf |
                      |  9. Transactional Atomic Persistence       |
                      +--------------------------------------------+
```

For complete architectural details, sequence diagrams, and data models, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 3. Quick Start with Docker Compose

The easiest way to run the complete Pragati Bharti stack (API server, Redis broker, and ARQ background worker) is via Docker Compose.

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+

### Launching the Stack

```bash
# 1. Clone repository and navigate to project root
cd pbnc

# 2. Configure environment file
cp .env.example .env

# 3. Build and launch containers
docker compose up --build -d

# 4. Tail worker and API logs
docker compose logs -f
```

The services will be reachable at:
- **API Server & Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/v1/health/](http://localhost:8000/api/v1/health/)
- **Prometheus Metrics**: [http://localhost:8000/metrics](http://localhost:8000/metrics)

---

## 4. Local Development Setup

### Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Git

### 1. Initialize Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Linux / macOS
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Upgrade pip and install package in editable mode with development tools
pip install -e ".[dev]"
```

### 3. Setup Database & Seed Initial Users

```bash
# Run database migrations
alembic upgrade head

# Seed initial roles and users
python scripts/seed_db.py
```

Seed accounts created:
| Email | Password | Role |
|:---|:---|:---|
| `admin@pragatibharti.edu` | `AdminPass123!` | `admin` |
| `reviewer@pragatibharti.edu` | `ReviewerPass123!` | `reviewer` |
| `teacher@pragatibharti.edu` | `TeacherPass123!` | `user` |
| `student@pragatibharti.edu` | `StudentPass123!` | `user` |

### 4. Start the Application

```bash
# Start FastAPI application server
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 5. Configuration & Environment Variables

| Variable | Description | Default | Required |
|:---|:---|:---:|:---:|
| `ENVIRONMENT` | Application environment (`development`, `staging`, `production`) | `development` | No |
| `API_V1_PREFIX` | Base prefix for all API v1 endpoints | `/api/v1` | No |
| `SECRET_KEY` | Symmetric key used to sign and verify JWT tokens | `development-insecure-secret-key-replace-in-production` | Yes (in prod) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of issued JWT access tokens | `60` | No |
| `DATABASE_URL` | SQLAlchemy async database connection URI | `sqlite+aiosqlite:///./data/pragati_bharti.db` | No |
| `REDIS_URL` | Redis server URI for queueing, caching & rate limiting | `redis://localhost:6379/0` | No |
| `STORAGE_BACKEND` | Storage backend for source and artifact files (`local` or `s3`) | `local` | No |
| `LOCAL_STORAGE_DIR` | Filesystem storage path for uploaded documents & exports | `./data/storage` | No |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed upload payload size in megabytes | `50` | No |
| `GEMINI_API_KEY` | Google Gemini API key for structured extraction | *(optional)* | No (auto-fallback) |
| `GEMINI_MODEL` | Google Gemini foundation model name | `gemini-2.5-flash` | No |
| `OCR_ENGINE` | Active OCR engine (`native` or `tesseract`) | `native` | No |
| `TESSERACT_CMD` | Absolute executable path to Tesseract binary (Linux container) | `tesseract` | No |
| `RATE_LIMIT_PER_MINUTE` | Maximum allowed API calls per minute per user/IP | `60` | No |

---

## 6. REST API Reference

The service exposes 29 REST endpoints categorized into logical resource areas:

### Authentication & Users
- `POST /api/v1/auth/token` - Authenticate with username & password; returns JWT.
- `GET /api/v1/auth/me` - Retrieve identity profile, tenant ID, and permissions of current user.

### Document Ingestion & Processing
- `POST /api/v1/documents/upload` - Upload PDF/image with metadata; triggers 9-stage extraction.
- `GET /api/v1/documents/` - Paginated list of uploaded documents scoped to tenant.
- `GET /api/v1/documents/{id}` - Retrieve metadata, processing status, and page metrics.
- `GET /api/v1/documents/{id}/status` - Lightweight polling endpoint for async pipeline progress.
- `POST /api/v1/documents/{id}/reprocess` - Trigger end-to-end re-extraction.
- `GET /api/v1/documents/{id}/export` - Export structured questions as `json`, `csv`, or `docx`.
- `DELETE /api/v1/documents/{id}` - Hard/soft delete document and associated entities.

### Question Management & Review
- `GET /api/v1/questions/` - List extracted questions with filtering by `document_id`, `review_status`, `confidence_min`.
- `GET /api/v1/questions/{id}` - Retrieve question details, options, answers, and bounding boxes.
- `PATCH /api/v1/questions/{id}` - Edit question text, correct option, or explanation.
- `POST /api/v1/questions/{id}/review` - Execute human review action (`approved`, `corrected`, `rejected`) with audit diff.
- `DELETE /api/v1/questions/{id}` - Delete question candidate.

### Answer Key Management
- `GET /api/v1/answers/` - List extracted answer key entries for a document.
- `GET /api/v1/answers/{id}` - Retrieve specific answer entry.
- `PATCH /api/v1/answers/{id}` - Update answer option or explanation.

### Cross-Document Linking (Groups)
- `POST /api/v1/groups/` - Create a document group.
- `GET /api/v1/groups/` - List document groups.
- `POST /api/v1/groups/{id}/documents` - Link question paper and answer key documents.
- `POST /api/v1/groups/{id}/merge` - Automatically link question papers with external answer keys.
- `DELETE /api/v1/groups/{id}` - Delete document group.

### System Quality & Observability
- `GET /api/v1/warnings/` - List image quality or parsing warnings.
- `POST /api/v1/warnings/{id}/resolve` - Mark warning as resolved.
- `GET /api/v1/health/` - Comprehensive health status.
- `GET /api/v1/health/ready` - Kubernetes readiness probe.
- `GET /api/v1/health/live` - Kubernetes liveness probe.
- `GET /metrics` - Prometheus metrics instrumentation.

---

## 7. Genuine Benchmark & Verification Evidence

All verification scenarios were executed against the running Pragati Bharti service without mocked outputs. Detailed runs are archived in `docs/evidence/` and `samples/output/`.

| Scenario | Target File / Feature | Status | Questions | Avg Conf | Time | Key Verification Details |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Scenario 1: Clean MCQ PDF** | `1_clean_mcq.pdf` | **PASS** | 5 | 0.96 | 1.57s | Extracted 5 questions; answers paired from end-of-document key. |
| **Scenario 2: Answer Key at Start** | `2_answer_key_start.pdf` | **PASS** | 8 | 0.97 | 1.35s | Extracted 8 questions; answers matched from top table grid. |
| **Scenario 3: Scanned Noisy PDF** | `3_scanned_noisy.pdf` | **PASS** | 3 | 0.85 | 2.03s | OCR executed; page deskewed and preprocessed. |
| **Scenario 4: Question Image PNG** | `4_question_image.png` | **PASS** | 1 | 0.90 | 0.50s | Single image ingested; geometric diagram question identified. |
| **Scenario 5: Cross-Page Question** | `6_cross_page.pdf` | **PASS** | 4 | 0.95 | 2.28s | Q3 stitched across page 1 and page 2; continuity preserved. |
| **Scenario 6: Document Group Linking** | `7_group_question_paper.pdf + 7_group_answer_key.pdf` | **PASS** | 8 | 0.95 | 3.43s | Cross-document merge: 5 questions paired with external answers. |
| **Scenario 7: Garbled Low-Quality Scan** | `8_garbled_scan.pdf` | **PASS** | - | - | 3.63s | Low-quality scan flagged with warnings for reviewer triage. |
| **Scenario 8: Human Review Workflow** | `Review on 1_clean_mcq.pdf` | **PASS** | 3 | 1.00 | 0.26s | Approved Q1, corrected Q2 with diff log, rejected Q3. |
| **Scenario 9: Security & IDOR Defense** | `Security Harness` | **PASS** | - | - | 0.07s | Verified 401 unauth, 404 IDOR defense, and tenant boundaries. |
| **Scenario 10: Robust Error Handling** | `Invalid Files Suite` | **PASS** | - | - | 1.83s | Verified 400 DISGUISED_EXECUTABLE, 415 UNSUPPORTED, 413 OVERSIZE. |

---

## 8. Testing & Verification

### Running Automated Test Suite
The test suite includes unit tests for all extraction algorithms, integration tests for API endpoints and IDOR defenses, and end-to-end pipeline executions:

```bash
pytest --cov=app --cov-report=term-missing
```

**Results**: 22 passed in 18.68s with **80% total codebase coverage**.

### Running the Live Demonstration Harness
To reproduce all 10 verification scenarios and refresh the outputs in `docs/evidence/` and `samples/output/`:

```bash
python scripts/run_demo.py
```

---

## 9. Postman Collection

Ready-to-import Postman assets are provided in the `postman/` folder:
- `postman/Pragati_Bharti_API.postman_collection.json`: Complete collection of 29 requests organized into 7 folders with automated test scripts that chain IDs and JWT tokens.
- `postman/Pragati_Bharti_API.postman_environment.json`: Local development environment pre-configured with default credentials and base URL.

---

## 10. Documentation Index

- [Architecture & Design Details](docs/ARCHITECTURE.md)
- [AI & Model Transparency Report](docs/AI_USAGE.md)
- [Summary Verification Table](docs/evidence/summary_table.md)
- [ADR 001: Worker Queue Selection](docs/decisions/ADR-001-worker-queue.md)
- [ADR 002: Dual-Engine Extraction](docs/decisions/ADR-002-dual-engine-extraction.md)
- [ADR 003: Storage Abstraction](docs/decisions/ADR-003-storage-abstraction.md)
- [ADR 004: Idempotency & Deduplication](docs/decisions/ADR-004-idempotency-and-deduplication.md)
- [ADR 005: Confidence Scoring Model](docs/decisions/ADR-005-confidence-scoring-model.md)
