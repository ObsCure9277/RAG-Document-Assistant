# 02: Upload and document library

**What to build:** A user can upload supported documents and browse them in a React document library while originals and metadata are persisted.

**Blocked by:** 01 — Dockerized persistence foundation

**Status:** ready-for-agent

- [ ] PDF, DOCX, TXT, and Markdown uploads are accepted with configurable size limits.
- [ ] Unsupported and oversized files receive useful errors.
- [ ] Original files are stored in the persistent mounted volume.
- [ ] Document metadata and an initial `uploaded` state are stored in PostgreSQL.
- [ ] The React library lists documents and their current states.
- [ ] Backend secrets, including the OpenAI key, are never exposed to the frontend.
- [ ] API and UI behavior is covered by tests.
