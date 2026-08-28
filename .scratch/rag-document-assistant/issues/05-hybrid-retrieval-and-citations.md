# 05: Hybrid retrieval and citations

**What to build:** A retrieval path finds relevant document evidence using both semantic and lexical search and returns citation-ready results.

**Blocked by:** 03 — Asynchronous document indexing

**Status:** ready-for-agent

- [ ] pgvector cosine similarity search uses the HNSW index.
- [ ] PostgreSQL full-text search uses the `simple` configuration and a GIN index.
- [ ] Vector and full-text candidates are merged and deduplicated.
- [ ] Optional conversation document filters are enforced.
- [ ] Configurable candidate counts, similarity threshold, and context limits are applied.
- [ ] Results include document name, page or section, heading, excerpt, chunk identifier, and scores where available.
- [ ] Retrieval does not return chunks from deleted or inactive versions.
- [ ] Retrieval integration tests verify ranking inputs, filtering, deduplication, and citation metadata.
