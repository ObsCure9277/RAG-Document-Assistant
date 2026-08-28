import uuid
from pathlib import Path

import inngest.fast_api
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.documents import Upload, validate_upload
from app.events import IngestionRequested, InngestEventPublisher, event_publisher
from app.inngest_worker import client as inngest_client, index_document
from app.embeddings import OpenAIEmbedder
from app.chat import build_grounded_prompt, sse
from app.chat_models import OpenAIChatModel
from app.retrieval import retrieve, Citation
from app.reliability import Timer, configure_logging, log_event
from app.lifecycle import enqueue_reindex, enqueue_retry, latest_version, load_document
from app.models import Conversation, Document, DocumentVersion, Message
from app.settings import get_settings
from app.storage import OriginalStorage

configure_logging()
app = FastAPI(title="Personal RAG document assistant")
if get_settings().inngest_signing_key:
    inngest.fast_api.serve(app, inngest_client, [index_document], serve_path="/api/inngest")
if get_settings().inngest_event_key:
    event_publisher = InngestEventPublisher(inngest_client)


class CitationResponse(BaseModel):
    document_id: uuid.UUID
    document_name: str
    page_number: int | None
    heading: str | None
    excerpt: str
    vector_score: float | None
    text_score: float | None
    score: float

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


def _citation_payload(citation: Citation) -> dict:
    return {"document_id": str(citation.document_id), "document_name": citation.document_name, "page_number": citation.page_number, "heading": citation.heading, "excerpt": citation.excerpt, "vector_score": citation.vector_score, "text_score": citation.text_score, "score": citation.score}

def _storage() -> OriginalStorage:
    return OriginalStorage(Path(get_settings().upload_root))


def _summary(document: Document) -> DocumentSummary:
    version = latest_version(document)
    jobs = version.__dict__.get("ingestion_jobs", []) if version else []
    job = max(jobs, key=lambda item: item.created_at, default=None)
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


@app.get("/api/search", response_model=list[CitationResponse])
async def search_documents(query: str, document_ids: list[uuid.UUID] | None = None, session: AsyncSession = Depends(get_session)) -> list[CitationResponse]:
    settings = get_settings()
    if not query.strip():
        raise HTTPException(status_code=400, detail="Search query must not be empty")
    embedder = OpenAIEmbedder(settings.openai_api_key, settings.embedding_model, settings.embedding_batch_size, base_url=settings.openai_base_url)
    query_embedding = (await embedder.embed([query]))[0]
    citations = await retrieve(session, query, query_embedding, vector_limit=settings.retrieval_vector_candidates, text_limit=settings.retrieval_text_candidates, context_limit=settings.retrieval_context_limit, similarity_threshold=settings.retrieval_similarity_threshold, document_ids=document_ids)
    return [CitationResponse.model_validate(citation.__dict__) for citation in citations]

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





class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str | None


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    status: str
    citations: list[dict]


class ChatRequest(BaseModel):
    content: str
    document_ids: list[uuid.UUID] | None = None


@app.post("/api/conversations", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(session: AsyncSession = Depends(get_session)) -> ConversationSummary:
    conversation = Conversation()
    session.add(conversation)
    await session.commit()
    return ConversationSummary(id=conversation.id, title=conversation.title)


@app.get("/api/conversations", response_model=list[ConversationSummary])
async def list_conversations(session: AsyncSession = Depends(get_session)) -> list[ConversationSummary]:
    result = await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    return [ConversationSummary(id=item.id, title=item.title) for item in result.scalars().all()]


@app.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(conversation_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[MessageResponse]:
    result = await session.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at))
    return [MessageResponse(id=item.id, role=item.role, content=item.content, status=item.status, citations=item.citations) for item in result.scalars().all()]


@app.post("/api/conversations/{conversation_id}/messages")
async def create_message(conversation_id: uuid.UUID, request: ChatRequest, session: AsyncSession = Depends(get_session)) -> StreamingResponse:
    from fastapi.responses import StreamingResponse
    settings = get_settings()
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Message content must not be empty")
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    history_result = await session.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(settings.conversation_history_limit))
    history_rows = list(reversed(history_result.scalars().all()))
    history = [{"role": item.role, "content": item.content} for item in history_rows]
    user_message = Message(conversation_id=conversation_id, role="user", content=request.content, status="complete")
    session.add(user_message)
    await session.commit()
    model = OpenAIChatModel(settings.openai_api_key, settings.answer_model, settings.answer_max_tokens, settings.openai_timeout_seconds, settings.openai_retry_attempts, settings.openai_retry_base_delay, settings.openai_base_url)

    async def stream_response():
        answer = ""
        citations: list[Citation] = []
        timer = Timer()
        try:
            query = await model.rewrite(request.content, history)
            query_embedding = (await OpenAIEmbedder(settings.openai_api_key, settings.embedding_model, settings.embedding_batch_size, settings.openai_timeout_seconds, settings.openai_retry_attempts, settings.openai_retry_base_delay, settings.openai_base_url).embed([query]))[0]
            citations = await retrieve(session, query, query_embedding, vector_limit=settings.retrieval_vector_candidates, text_limit=settings.retrieval_text_candidates, context_limit=settings.retrieval_context_limit, similarity_threshold=settings.retrieval_similarity_threshold, document_ids=request.document_ids)
            yield sse("citations", [_citation_payload(citation) for citation in citations])
            prompt = build_grounded_prompt(query, history, citations)
            answer_timer = Timer()
            log_event("llm_answer_started", conversation_id=str(conversation_id))
            async for token in model.stream(prompt.messages):
                answer += token
                yield sse("token", {"text": token})
            assistant = Message(conversation_id=conversation_id, role="assistant", content=answer, status="complete", citations=[_citation_payload(citation) for citation in citations])
            session.add(assistant)
            await session.commit()
            log_event("chat_completed", conversation_id=str(conversation_id), citations=len(citations), duration_ms=timer.elapsed_ms)
            yield sse("complete", {"message_id": assistant.id})
        except Exception as error:
            await session.rollback()
            session.add(Message(conversation_id=conversation_id, role="assistant", content=answer, status="incomplete", citations=[_citation_payload(citation) for citation in citations]))
            await session.commit()
            log_event("chat_failed", conversation_id=str(conversation_id), duration_ms=timer.elapsed_ms)
            yield sse("error", {"detail": str(error), "incomplete": True})

    return StreamingResponse(stream_response(), media_type="text/event-stream")






