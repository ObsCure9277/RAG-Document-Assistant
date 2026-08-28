# 03: Asynchronous document indexing

**What to build:** An uploaded document is asynchronously extracted, chunked, embedded, and made searchable through an observable Inngest workflow.

**Blocked by:** 02 — Upload and document library

**Status:** ready-for-agent

- [ ] FastAPI emits an ingestion event after upload.
- [ ] The Inngest worker extracts PDF, DOCX, TXT, and Markdown content.
- [ ] Extracted content preserves page or section, heading, source, and chunk-order metadata where available.
- [ ] LlamaIndex creates sentence-aware or semantic chunks of approximately 500–800 tokens with 50–100 token overlap.
- [ ] OpenAI `text-embedding-3-small` embeddings are generated in bounded batches.
- [ ] Chunks and embeddings are persisted and the document reaches `indexed` only after successful completion.
- [ ] Failures persist an actionable reason and expose `failed` status.
- [ ] Retries are bounded and do not create duplicate chunks or embeddings.
- [ ] Workflow and API tests verify the end-to-end indexing path.
