import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.documents import Upload, validate_upload
from app.events import IngestionRequested, InngestEventPublisher, event_publisher
from app.inngest_worker import client as inngest_client, index_document
import inngest.fast_api
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


def _storage() -> OriginalStorage:
    return OriginalStorage(get_settings().upload_root)


async def _read_upload(file: UploadFile, max_bytes: int) -> bytes:
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"File is too large. The maximum size is {max_bytes} bytes.")
    return content


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/documents", response_model=list[DocumentSummary])
async def list_documents(session: AsyncSession = Depends(get_session)) -> list[DocumentSummary]:
    result = await session.execute(select(Document).options(selectinload(Document.versions)).order_by(Document.created_at.desc()))
    documents = result.scalars().all()
    return [DocumentSummary(id=d.id, title=d.title, original_filename=d.original_filename, mime_type=d.mime_type, size_bytes=d.size_bytes, checksum=d.checksum, status=d.versions[-1].status if d.versions else "uploaded") for d in documents]


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

    existing = (await session.execute(select(Document).options(selectinload(Document.versions)).where(Document.checksum == upload.checksum))).scalar_one_or_none()
    if existing:
        return DocumentSummary(id=existing.id, title=existing.title, original_filename=existing.original_filename, mime_type=existing.mime_type, size_bytes=existing.size_bytes, checksum=existing.checksum, status=existing.versions[-1].status if existing.versions else "uploaded")

    document = Document(id=uuid.uuid4(), title=Path(filename).stem, original_filename=filename, mime_type=upload.mime_type, checksum=upload.checksum, size_bytes=len(content))
    document.versions.append(DocumentVersion(version_number=1, checksum=upload.checksum, status="uploaded"))
    session.add(document)
    await session.flush()
    committed = False
    try:
        await _storage().save(document.id, filename, content)
        await session.commit()
        committed = True
        await event_publisher.publish(IngestionRequested(document.versions[0].id))
    except Exception:
        if not committed:
            await session.rollback()
            _storage().delete(document.id, filename)
        raise
    return DocumentSummary(id=document.id, title=document.title, original_filename=document.original_filename, mime_type=document.mime_type, size_bytes=document.size_bytes, checksum=document.checksum, status="uploaded")







