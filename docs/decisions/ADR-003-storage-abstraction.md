# ADR-003: Pluggable Storage Abstraction Layer

## Status
Accepted

## Context
Documents (PDFs, images) and extracted visual assets (diagrams, tables, cropped figures, rendered page previews) require persistent object storage. Depending on the environment:
- Local development and automated testing require zero external cloud dependencies.
- Production and multi-container Docker deployments require S3-compatible object storage (AWS S3, Cloudflare R2, MinIO, or Google Cloud Storage).

Furthermore, direct user-controlled file paths risk path traversal vulnerabilities (`../../etc/passwd`).

## Decision
We define an abstract `StorageBackend` interface in `app/storage/base.py` with concrete implementations:
1. `LocalStorageBackend`: Stores files in a configured local directory using UUID keys and SHA256-derived subdirectories (`data/storage/ab/cd/<uuid>.ext`). Path normalization and traversal checks are enforced on every operation.
2. `S3StorageBackend`: Uses `aioboto3` or standard async S3 clients for production bucket storage with presigned URLs.

Files are streamed in chunks (64 KB) during upload, with byte-counter limits checked during streaming to prevent RAM exhaustion.

## Consequences
- Clean separation between storage management and domain pipeline logic.
- Assets are referenced by logical storage keys (`stored_key`), never raw filesystem paths.
- Streamed image and page preview endpoints stream authorized files directly through the API with authentication checks.
