import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, DocumentVersion, IngestionJob


async def load_document(session: AsyncSession, document_id: uuid.UUID) -> Document | None:
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.versions).selectinload(DocumentVersion.ingestion_jobs))
        .where(Document.id == document_id)
    )
    return result.scalar_one_or_none()


def latest_version(document: Document) -> DocumentVersion | None:
    return max(document.versions, key=lambda version: version.version_number, default=None)


def enqueue_reindex(document: Document) -> DocumentVersion:
    version = DocumentVersion(
        document_id=document.id,
        version_number=max((item.version_number for item in document.versions), default=0) + 1,
        checksum=document.checksum,
        status="uploaded",
    )
    document.versions.append(version)
    version.ingestion_jobs.append(IngestionJob(status="queued"))
    return version


def enqueue_retry(version: DocumentVersion) -> IngestionJob:
    job = IngestionJob(version_id=version.id, status="queued")
    version.ingestion_jobs.append(job)
    version.status = "uploaded"
    version.is_searchable = False
    return job
