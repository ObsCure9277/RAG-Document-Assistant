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
client = inngest.Inngest(
    app_id="rag-document-assistant",
    api_base_url=settings.inngest_event_api_url.removesuffix("/e"),
    event_api_base_url=settings.inngest_event_api_url,
    event_key=settings.inngest_event_key or None,
    signing_key=settings.inngest_signing_key or None,
    is_production=not bool(settings.inngest_event_key == "local-dev-key"),
)


@client.create_function(
    fn_id="ingest-file",
    trigger=inngest.TriggerEvent(event="document/ingestion.requested"),
    retries=2,
)
async def index_document(ctx: inngest.Context) -> None:
    settings = get_settings()
    async with session_factory() as session:
        await index_version(
            uuid.UUID(ctx.event.data["version_id"]),
            session,
            OpenAIEmbedder(settings.openai_api_key, settings.embedding_model, settings.embedding_batch_size, settings.openai_timeout_seconds, settings.openai_retry_attempts, settings.openai_retry_base_delay, settings.openai_base_url),
            OriginalStorage(settings.upload_root),
            max_attempts=settings.max_indexing_attempts,
        )




