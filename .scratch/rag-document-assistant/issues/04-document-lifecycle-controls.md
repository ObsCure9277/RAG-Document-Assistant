# 04: Document lifecycle controls

**What to build:** A user can safely re-index, retry, deduplicate, and delete documents without losing a working indexed version during a failed replacement.

**Blocked by:** 03 — Asynchronous document indexing

**Status:** ready-for-agent

- [ ] A document can be re-indexed into an immutable new version.
- [ ] The current indexed version remains active until replacement indexing succeeds.
- [ ] Failed re-indexing leaves the previous active version usable.
- [ ] Duplicate uploads are detected using a SHA-256 checksum.
- [ ] Failed ingestion can be retried from the document library.
- [ ] Deletion removes the original file, versions, chunks, embeddings, metadata, and related searchable data.
- [ ] The UI exposes re-index, retry, delete, and failure-detail actions.
- [ ] Lifecycle transitions and cleanup are covered by integration tests.
