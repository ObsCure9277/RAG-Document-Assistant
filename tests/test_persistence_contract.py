from app.models import Base


def test_core_persistence_tables_are_present():
    assert set(Base.metadata.tables) == {
        "documents", "document_versions", "document_chunks", "ingestion_jobs", "conversations", "messages"
    }


def test_document_chunks_have_idempotency_and_search_columns():
    table = Base.metadata.tables["document_chunks"]
    assert {column.name for column in table.columns} >= {"version_id", "chunk_index", "embedding", "search_vector"}
    assert any(tuple(constraint.columns.keys()) == ("version_id", "chunk_index") for constraint in table.constraints)
