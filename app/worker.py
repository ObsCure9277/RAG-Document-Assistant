from datetime import datetime, timezone
from pathlib import Path
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents import SUPPORTED_EXTENSIONS
from app.indexing import DocumentExtractor, Embedder, chunk_sections
from app.models import DocumentChunk, DocumentVersion, IngestionJob
from app.storage import OriginalStorage


async def index_version(
    version_id: uuid.UUID,
    session: AsyncSession,
    embedder: Embedder,
    storage: OriginalStorage,
    extractor: DocumentExtractor | None = None,
    max_attempts: int = 3,
) -> None:
    version = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == version_id))).scalar_one()
    job = (await session.execute(select(IngestionJob).where(IngestionJob.version_id == version_id).order_by(IngestionJob.created_at.desc()))).scalars().first()
    if job is None:
        job = IngestionJob(version_id=version_id)
        session.add(job)
    if job.attempts >= max_attempts:
        version.status = "failed"
        job.status = "failed"
        job.error_message = "Maximum indexing attempts reached; retry requires a new job."
        await session.commit()
        return
    job.attempts += 1
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    version.status = "processing"
    await session.flush()
    try:
        document = await session.run_sync(lambda sync_session: sync_session.get(type(version.document), version.document_id)) if False else None
        # The original filename is stored on the parent document; load it without relying on lazy IO.
        from app.models import Document
        document = (await session.execute(select(Document).where(Document.id == version.document_id))).scalar_one()
        path = storage.path_for(document.id, document.original_filename)
        sections = (extractor or DocumentExtractor()).extract(path, document.mime_type)
        chunks = chunk_sections(sections)
        vectors = await embedder.embed([chunk.content for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding provider returned an unexpected number of vectors")
        await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id == version_id))
        version.extracted_text = "\n\n".join(section.text for section in sections)
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
    except Exception as error:
        await session.rollback()
        version = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == version_id))).scalar_one()
        job = (await session.execute(select(IngestionJob).where(IngestionJob.version_id == version_id).order_by(IngestionJob.created_at.desc()))).scalars().first()
        if job is None:
            job = IngestionJob(version_id=version_id)
            session.add(job)
        job.attempts += 1
        job.status = "failed" if job.attempts >= max_attempts else "queued"
        job.error_message = f"Indexing failed: {error}"
        version.status = "failed" if job.attempts >= max_attempts else "uploaded"
        await session.commit()




