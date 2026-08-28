---
title: Personal RAG document assistant
labels:
  - ready-for-agent
---

## Problem Statement

As a person with a growing collection of documents, I want to ask questions across my files and receive answers grounded in those files. The assistant should make relevant evidence easy to find, avoid inventing unsupported information, and remain usable when ingestion or external API calls fail.

## Solution

Build a Docker-hosted personal RAG document assistant with a React TypeScript frontend, FastAPI backend, PostgreSQL with pgvector, Inngest workflows, LlamaIndex utilities, and the OpenAI API. Users can upload supported documents, monitor ingestion, search through hybrid vector and PostgreSQL full-text retrieval, and chat with streamed answers containing page-aware citations.

## User Stories

1. As a personal user, I want to upload a PDF, DOCX, TXT, or Markdown document, so that it becomes available to the assistant.
2. As a personal user, I want to see whether a document is uploaded, processing, indexed, or failed, so that I know when it can be queried.
3. As a personal user, I want ingestion failures to explain what went wrong, so that I can correct or retry them.
4. As a personal user, I want ingestion to run asynchronously, so that uploading a large document does not block the interface.
5. As a personal user, I want ingestion retries to be safe, so that transient failures do not create duplicate chunks or embeddings.
6. As a personal user, I want to re-index a document, so that updated parsing or embedding settings can be applied.
7. As a personal user, I want an updated document to remain available until its replacement is indexed successfully, so that re-index failures do not cause data loss.
8. As a personal user, I want to delete a document, so that its original file, extracted text, chunks, embeddings, and metadata are removed.
9. As a personal user, I want duplicate uploads detected by checksum, so that redundant indexing work is avoided.
10. As a personal user, I want to browse my document library, so that I can understand what knowledge is available.
11. As a personal user, I want to start multiple conversations, so that separate research threads remain organized.
12. As a personal user, I want to optionally restrict a conversation to selected documents, so that answers focus on a known subset of sources.
13. As a personal user, I want to ask questions in natural language, so that I do not need to know exact document wording.
14. As a personal user, I want follow-up questions to use recent conversation context, so that I can ask naturally without repeating the subject.
15. As a personal user, I want answers streamed as they are generated, so that I receive useful feedback before generation completes.
16. As a personal user, I want factual claims backed by document citations, so that I can verify the answer.
17. As a personal user, I want citations to include document name, page when available, and a supporting excerpt, so that evidence is understandable.
18. As a personal user, I want the assistant to say when the documents do not contain enough evidence, so that it does not present guesses as facts.
19. As a personal user, I want conflicting source material called out, so that I can resolve disagreements myself.
20. As a personal user, I want retrieved document text treated as untrusted content, so that embedded instructions cannot change assistant behavior.
21. As a personal user, I want chat history persisted, so that I can return to earlier research.
22. As a personal user, I want incomplete streamed responses represented clearly, so that interrupted requests are not mistaken for complete answers.
23. As a personal user, I want the application to survive Docker restarts without losing documents or conversations, so that local persistence is dependable.
24. As a developer, I want the embedding and answer models configurable through environment variables, so that models can change without frontend changes.
25. As a developer, I want OpenAI keys kept on the backend, so that credentials are not exposed to the browser.
26. As a developer, I want bounded retries and configurable limits, so that API failures and unusually large inputs do not exhaust resources.
27. As a developer, I want structured logs for ingestion, retrieval, model calls, and chat latency, so that failures and performance issues can be diagnosed.
28. As a developer, I want a golden evaluation set, so that retrieval quality, groundedness, citation accuracy, latency, and cost can be measured.
29. As a developer, I want database schema changes versioned, so that persistent data can evolve safely.
30. As a developer, I want the system divided into clear API, worker, extraction, retrieval, and persistence boundaries, so that components can be tested independently.

## Implementation Decisions

- Run PostgreSQL with the pgvector extension in Docker Compose. Persist database data with a named volume.
- Run separate Compose services for PostgreSQL, FastAPI, an Inngest development server, a Python Inngest worker, and the React frontend. Uploaded originals use a Docker-mounted volume.
- Use SQLAlchemy 2.x with async sessions and asyncpg. Use Alembic for explicit schema migrations and enabling pgvector.
- Use core entities for documents, immutable document versions, document chunks, ingestion jobs, conversations, and messages. Store embeddings on document chunks.
- Use OpenAI `text-embedding-3-small` initially, with an explicitly configured vector dimension. Treat embedding-model changes as re-indexing migrations.
- Use PyMuPDF for PDF extraction, python-docx for DOCX extraction, and native decoding for TXT and Markdown. Normalize extraction into pages or sections with source metadata.
- Use LlamaIndex for loading, node creation, metadata, and retrieval utilities, while application code owns lifecycle state, persistence, and chat behavior.
- Chunk sentence-aware or semantic content at approximately 500–800 tokens with 50–100 tokens of overlap. Preserve page, heading, source, and chunk-order metadata.
- Process documents asynchronously through an Inngest workflow with extraction, normalization, chunking, batched embeddings, persistence, and finalization steps.
- Make ingestion idempotent using deterministic document/version identifiers, checksums, and unique chunk constraints. Mark a version searchable only after all required embeddings are persisted.
- Use hybrid retrieval combining pgvector cosine similarity and PostgreSQL full-text search with the `simple` configuration. Use HNSW and GIN indexes, merge and deduplicate candidates, then bound the final context.
- Initial retrieval configuration is approximately 20 vector candidates, 20 full-text candidates, and 6–10 final context chunks; all are configurable and evaluated against the golden dataset.
- Rewrite follow-up questions into standalone retrieval queries using recent conversation context. Send a bounded message window and retrieved evidence to the answer model.
- Enforce a grounded system prompt: use only supplied context, do not invent citations, state insufficient evidence, identify conflicts, and treat document text as untrusted data.
- Expose document upload/list/re-index/delete, conversation list/create, message creation, and message-history API capabilities. Stream chat answers over Server-Sent Events.
- Persist the user message before retrieval and persist the completed assistant response and structured citations after streaming. Mark interrupted responses incomplete.
- Keep document originals outside PostgreSQL in the mounted volume, while PostgreSQL stores extracted text, metadata, chunks, and embeddings.
- Store OpenAI credentials, Inngest settings, database settings, model names, and operational limits in environment variables. Provide an example configuration without secrets.
- Apply file-size, page/token, concurrency, context, timeout, retry, and conversation-history limits. Retry transient OpenAI failures with bounded exponential backoff.
- Do not add authentication, multi-tenancy, workspace roles, billing, OCR, spreadsheets, agentic retrieval, local-model fallback, or external object storage in v1.

## Testing Decisions

- Prefer tests at the highest seam: exercise the application through its API and worker boundaries with a disposable PostgreSQL/pgvector database where practical.
- Test externally observable behavior rather than internal implementation details.
- Test document lifecycle transitions, checksum deduplication, extraction normalization, chunk metadata, idempotent retries, re-index activation, deletion cleanup, and failure reporting.
- Test pgvector retrieval, PostgreSQL full-text retrieval, hybrid merging, document filters, score thresholds, and citation metadata.
- Test chat streaming, grounded refusal behavior, follow-up query rewriting, citation structure, incomplete responses, and bounded conversation context.
- Test Inngest workflow retries and recovery without producing duplicate chunks or embeddings.
- Test Docker persistence across service restarts and migration application on a fresh database.
- Maintain a 30–50 question golden dataset with expected supporting documents or chunks and human ratings for groundedness and citation correctness.
- Track retrieval recall, citation accuracy, answer faithfulness, latency, and OpenAI cost. Existing repository test prior art is absent because the repository currently contains no application implementation.

## Out of Scope

- Multi-user authentication and authorization.
- Workspaces, sharing, roles, and tenant isolation.
- Production cloud deployment, managed object storage, and external hosting.
- OCR and image understanding for scanned PDFs.
- Spreadsheet and complex table extraction.
- Agentic or multi-step tool-using retrieval.
- Local LLM or embedding-model fallback.
- User-selectable models in the frontend.
- Billing, quotas beyond local operational limits, and analytics dashboards.
- Deep links into a document viewer beyond page and excerpt citations.

## Further Notes

The highest-value first vertical slice is: Dockerized PostgreSQL/pgvector, schema migration, document upload, asynchronous indexing, one retrieval endpoint, and a citation-bearing streamed chat response. Retrieval settings should be tuned using the golden dataset rather than assumed defaults.
