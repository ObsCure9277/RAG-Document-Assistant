# Personal RAG document assistant

## Persistence foundation

Install dependencies, start PostgreSQL with pgvector, and apply the versioned schema:

```sh
cp .env.example .env
docker compose up -d postgres
alembic upgrade head
```

The database uses the named `postgres_data` volume, so its records survive container restarts. `DATABASE_URL` controls Alembic and the application connection; `EMBEDDING_DIMENSION` documents the configured embedding contract (the initial migration uses `text-embedding-3-small`'s 1536 dimensions).

Run the tests with `pytest`. Database integration tests activate when `DATABASE_URL` is set; point it at a disposable database after applying the migration.
