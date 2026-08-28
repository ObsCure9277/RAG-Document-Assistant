"""Inngest adapter for the indexing workflow."""
import inngest
import uuid

from app.db import session_factory
from app.settings import get_settings
from app.embeddings import OpenAIEmbedder
from app.settings import get_settings
from app.storage import OriginalStorage
from app.worker import index_version

settings = get_settings()
client = inngest.Inngest(app_id="rag-document-assistant", event_key=settings.inngest_event_key or None, signing_key=settings.inngest_signing_key or None)


@client.create_function(
    fn_id="index-document-version",
    trigger=inngest.TriggerEvent(event="document/ingestion.requested"),
    retries=2,
)
async def index_document(event: inngest.Event) -> None:
    settings = get_settings()
    async with session_factory() as session:
        await index_version(
            uuid.UUID(event.data["version_id"]),
            session,
            OpenAIEmbedder(settings.openai_api_key, settings.embedding_model, settings.embedding_batch_size),
            OriginalStorage(settings.upload_root),
            max_attempts=settings.max_indexing_attempts,
        )



