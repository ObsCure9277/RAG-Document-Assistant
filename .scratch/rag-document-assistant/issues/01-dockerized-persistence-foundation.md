# 01: Dockerized persistence foundation

**What to build:** A runnable Docker Compose foundation for the personal assistant with persistent PostgreSQL/pgvector storage, migrations, and the core domain schema.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Docker Compose starts PostgreSQL with pgvector and persistent volumes.
- [ ] Database health checks and environment-based configuration work.
- [ ] Alembic can create the schema, including vector extension and required indexes.
- [ ] Core document, document version, document chunk, ingestion job, conversation, and message data can be persisted.
- [ ] Restarting the database preserves stored data.
- [ ] Automated tests verify migration and persistence behavior.
