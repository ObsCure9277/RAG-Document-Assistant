import uuid

from app.events import InMemoryEventPublisher, IngestionRequested


async def test_ingestion_event_publisher_records_version():
    publisher = InMemoryEventPublisher()
    version_id = uuid.uuid4()
    await publisher.publish(IngestionRequested(version_id))
    assert publisher.events == [IngestionRequested(version_id)]
