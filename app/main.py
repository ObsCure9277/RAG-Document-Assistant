import uuid
from pathlib import Path

import inngest.fast_api
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.documents import Upload, validate_upload
from app.events import IngestionRequested, InngestEventPublisher, event_publisher
from app.inngest_worker import client as inngest_client, index_document
from app.lifecycle import enqueue_reindex, enqueue_retry, latest_version, load_document
from app.models import Document, DocumentVersion
from app.settings import get_settings
from app.storage import OriginalStorage

app = FastAPI(title="Personal RAG document assistant")
if get_settings().inngest_signing_key:
    inngest.fast_api.serve(app, inngest_client, [index_document], serve_path="/api/inngest")
if get_settings().inngest_event_key:
    event_publisher = InngestEventPublisher(inngest_client)


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    status: str
    version: int
    active_version_id: uuid.UUID | None
    error_message: str | None = None


def _storage() -> OriginalStorage:
    return OriginalStorage(Path(get_settings().upload_root))


def _summary(document: Document) -> DocumentSummary:
    version = latest_version(document)
    job = max(version.ingestion_jobs, key=lambda item: item.created_at, default=None) if version else None
    return DocumentSummary(
        id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        checksum=document.checksum,
        status=version.status if version else "uploaded",
        version=version.version_number if version else 0,
        active_version_id=document.active_version_id,
        error_message=job.error_message if job and version and version.status == "failed" else None,
    )


async def _read_upload(file: UploadFile, max_bytes: int) -> bytes:
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"File is too large. The maximum size is {max_bytes} bytes.")
    return content


async def _publish(version_id: uuid.UUID) -> None:
    await event_publisher.publish(IngestionRequested(version_id))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/documents", response_model=list[DocumentSummary])
async def list_documents(session: AsyncSession = Depends(get_session)) -> list[DocumentSummary]:
    result = await session.execute(select(Document).options(selectinload(Document.versions).selectinload(DocumentVersion.ingestion_jobs)).order_by(Document.created_at.desc()))
    return [_summary(document) for document in result.scalars().all()]


@app.post("/api/documents", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)) -> DocumentSummary:
    settings = get_settings()
    filename = Path(file.filename or "").name
    try:
        content = await _read_upload(file, settings.max_upload_bytes)
        upload = Upload(filename=filename, content=content, mime_type=file.content_type or "application/octet-stream")
        validate_upload(upload, settings.max_upload_bytes)
    except ValueError as error:
        raise HTTPException(status_code=413 if "too large" in str(error) else 415, detail=str(error)) from error

    existing = await load_document_by_checksum(session, upload.checksum)
    if existing:
        return _summary(existing)
    document = Document(id=uuid.uuid4(), title=Path(filename).stem, original_filename=filename, mime_type=upload.mime_type, checksum=upload.checksum, size_bytes=len(content))
    document.versions.append(DocumentVersion(version_number=1, checksum=upload.checksum, status="uploaded"))
    session.add(document)
    await session.flush()
    committed = False
    try:
        await _storage().save(document.id, filename, content)
        await session.commit()
        committed = True
        await _publish(document.versions[0].id)
    except Exception:
        if not committed:
            await session.rollback()
            _storage().delete(document.id, filename)
        raise
    return _summary(document)


async def load_document_by_checksum(session: AsyncSession, checksum: str) -> Document | None:
    result = await session.execute(select(Document).options(selectinload(Document.versions).selectinload(DocumentVersion.ingestion_jobs)).where(Document.checksum == checksum))
    return result.scalar_one_or_none()


@app.post("/api/documents/{document_id}/reindex", response_model=DocumentSummary)
async def reindex_document(document_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> DocumentSummary:
    document = await load_document(session, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    version = enqueue_reindex(document)
    await session.commit()
    await _publish(version.id)
    document = await load_document(session, document_id)
    return _summary(document)


@app.post("/api/documents/{document_id}/retry", response_model=DocumentSummary)
async def retry_document(document_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> DocumentSummary:
    document = await load_document(session, document_id)
    version = latest_version(document) if document else None
    if not document or not version:
        raise HTTPException(status_code=404, detail="Document not found")
    if version.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed document versions can be retried")
    job = enqueue_retry(version)
    await session.commit()
    await _publish(version.id)
    document = await load_document(session, document_id)
    return _summary(document)


@app.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    document = await load_document(session, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    filename = document.original_filename
    await session.delete(document)
    await session.commit()
    _storage().delete(document_id, filename)
