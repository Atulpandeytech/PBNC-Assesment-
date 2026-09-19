# ADR-004: Upload Idempotency, Deduplication & Pipeline Resumability

## Status
Accepted

## Context
In educational examination workflows, teachers and reviewers frequently re-upload the same question paper or retry failed network requests. Unchecked duplicate uploads waste storage, trigger redundant OCR/LLM costs, and create duplicate question entries.
Additionally, long-running document processing jobs might encounter transient worker restarts or failures mid-way.

## Decision
1. **Deduplication Strategy**:
   - Every uploaded file's SHA-256 hash is computed during streaming ingest.
   - The `documents` table enforces a composite unique constraint `(owner_id, sha256)`.
   - On duplicate upload by the same owner, the API returns the existing document with `200 OK` (or `202 Accepted` if still processing), including a header `X-Document-Duplicate: true`.
2. **Distributed Locking**:
   - When a worker picks up a document job, it acquires a Redis distributed lock (`lock:doc:{document_id}`) with a 300-second TTL and heartbeat extension.
   - If another worker attempts to process the same document, it detects the active lock and aborts immediately.
3. **Idempotent Pipeline Persistence**:
   - Re-running a document pipeline (e.g. via `POST /api/v1/documents/{id}/reprocess`) runs within a database transaction that deletes prior extracted questions, pages, answer keys, and warnings for that document before persisting the fresh run.
   - Database foreign keys cascade appropriately, guaranteeing zero orphaned or duplicate records.

## Consequences
- Guaranteed exactly-once question persistence per document.
- Safe reprocessing without dirty data or duplicate rows.
