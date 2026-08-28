import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL pointing at PostgreSQL/pgvector")


async def test_database_has_migrated_schema_and_vector_extension():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            tables = (await connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))).scalars().all()
            extension = (await connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))).scalar_one_or_none()
        assert extension == "vector"
        assert {"documents", "document_versions", "document_chunks", "ingestion_jobs", "conversations", "messages"} <= set(tables)
    finally:
        await engine.dispose()
