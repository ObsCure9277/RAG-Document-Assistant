from dataclasses import dataclass
from typing import Protocol
import uuid


@dataclass(frozen=True)
class IngestionRequested:
    version_id: uuid.UUID


class EventPublisher(Protocol):
    async def publish(self, event: IngestionRequested) -> None: ...


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[IngestionRequested] = []

    async def publish(self, event: IngestionRequested) -> None:
        self.events.append(event)


event_publisher: EventPublisher = InMemoryEventPublisher()


class InngestEventPublisher:
    def __init__(self, client: object):
        self.client = client

    async def publish(self, event: IngestionRequested) -> None:
        import inngest
        await self.client.send(inngest.Event(name="document/ingestion.requested", data={"version_id": str(event.version_id)}))

