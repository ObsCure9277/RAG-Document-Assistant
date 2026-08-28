from app.indexing import ExtractedSection, chunk_sections
from app.events import InMemoryEventPublisher, IngestionRequested
import uuid


def test_chunking_preserves_source_metadata_and_order():
    chunks = chunk_sections([ExtractedSection("One sentence. Two sentence.", "notes.md", heading="Intro")], target_tokens=2, overlap_tokens=1)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.source == "notes.md" and chunk.heading == "Intro" for chunk in chunks)


def test_chunking_rejects_invalid_overlap():
    try:
        chunk_sections([], target_tokens=10, overlap_tokens=10)
    except ValueError as error:
        assert "greater" in str(error)
    else:
        raise AssertionError("expected invalid chunk configuration to fail")


async def test_ingestion_event_publisher_records_version():
    publisher = InMemoryEventPublisher()
    version_id = uuid.uuid4()
    await publisher.publish(IngestionRequested(version_id))
    assert publisher.events == [IngestionRequested(version_id)]

