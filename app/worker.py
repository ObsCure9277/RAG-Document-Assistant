from datetime import datetime, timezone
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.indexing import DocumentExtractor, Embedder, chunk_sections
from app.models import Document, DocumentChunk, DocumentVersion, IngestionJob
from app.reliability import Timer, log_event
from app.storage import OriginalStorage
from app.settings import get_settings


async def index_version(version_id: uuid.UUID, session: AsyncSession, embedder: Embedder, storage: OriginalStorage, extractor: DocumentExtractor | None = None, max_attempts: int = 3) -> None:
    timer = Timer()
    log_event("index_started", version_id=str(version_id))
    version = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == version_id))).scalar_one()
    job = (await session.execute(select(IngestionJob).where(IngestionJob.version_id == version_id).order_by(IngestionJob.created_at.desc()))).scalars().first()
    if job is None:
        job = IngestionJob(version_id=version_id)
        session.add(job)
    if (job.attempts or 0) >= max_attempts:
        version.status = "failed"
        job.status = "failed"
        job.error_message = "Maximum indexing attempts reached; retry requires a new job."
        await session.commit()
        log_event("index_failed", version_id=str(version_id), duration_ms=timer.elapsed_ms, attempts=job.attempts)
        return
    job.attempts = (job.attempts or 0) + 1
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    version.status = "processing"
    await session.flush()
    try:
        document = (await session.execute(select(Document).where(Document.id == version.document_id))).scalar_one()
        load_timer = Timer()
        log_event("load_and_chunk_started", version_id=str(version_id))
        settings = get_settings() if extractor is None else None
        default_extractor = DocumentExtractor(settings.max_document_pages, settings.max_document_tokens, settings.max_document_archive_bytes) if settings else DocumentExtractor()
        sections = (extractor or default_extractor).extract(storage.path_for(document.id, document.original_filename), document.mime_type)
        max_pages = settings.max_document_pages if settings else 500
        max_chars = (settings.max_document_tokens if settings else 200000) * 4
        if len({section.page_number for section in sections if section.page_number is not None}) > max_pages or sum(len(section.text) for section in sections) > max_chars:
            raise ValueError("Document exceeds the configured extraction limits")
        chunks = chunk_sections(sections)
        log_event("load_and_chunk_completed", version_id=str(version_id), sections=len(sections), chunks=len(chunks), duration_ms=load_timer.elapsed_ms, chunks_per_second=round(len(chunks) / max(load_timer.elapsed_ms / 1000, 0.001), 2))
        embed_timer = Timer()
        log_event("embed_and_upsert_started", version_id=str(version_id), chunks=len(chunks))
        vectors = await embedder.embed([chunk.content for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding provider returned an unexpected number of vectors")
        await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id == version_id))
        version.extracted_text = "\n\n".join(section.text for section in sections)
        log_event("embeddings_completed", version_id=str(version_id), embeddings=len(vectors))
        for chunk, vector in zip(chunks, vectors, strict=True):
            session.add(DocumentChunk(version_id=version_id, chunk_index=chunk.chunk_index, content=chunk.content, page_number=chunk.page_number, heading=chunk.heading, metadata_={"source": chunk.source}, embedding=vector))
        version.status = "indexed"
        document.active_version_id = version.id
        version.is_searchable = True
        version.indexed_at = datetime.now(timezone.utc)
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.error_message = None
        await session.commit()
        log_event("embed_and_upsert_completed", version_id=str(version_id), chunks=len(chunks), duration_ms=embed_timer.elapsed_ms, chunks_per_second=round(len(chunks) / max(embed_timer.elapsed_ms / 1000, 0.001), 2))
        log_event("index_completed", version_id=str(version_id), chunks=len(chunks), duration_ms=timer.elapsed_ms, attempts=job.attempts)
    except Exception as error:
        await session.rollback()
        version = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == version_id))).scalar_one()
        job = (await session.execute(select(IngestionJob).where(IngestionJob.version_id == version_id).order_by(IngestionJob.created_at.desc()))).scalars().first()
        if job is None:
            job = IngestionJob(version_id=version_id)
            session.add(job)
        job.attempts = (job.attempts or 0) + 1
        job.status = "failed" if job.attempts >= max_attempts else "queued"
        job.error_message = "Indexing failed. Please retry the document."
        version.status = "failed" if job.attempts >= max_attempts else "uploaded"
        await session.commit()
        log_event("index_failed", version_id=str(version_id), duration_ms=timer.elapsed_ms, attempts=job.attempts, error_type=type(error).__name__)
