from dataclasses import dataclass
from typing import Any
import uuid

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk, DocumentVersion
from app.reliability import Timer, log_event


@dataclass(frozen=True)
class RetrievalCandidate:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    content: str
    page_number: int | None
    heading: str | None
    vector_score: float | None = None
    text_score: float | None = None


@dataclass(frozen=True)
class Citation:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int | None
    heading: str | None
    excerpt: str
    vector_score: float | None
    text_score: float | None
    score: float


def merge_candidates(vector: list[RetrievalCandidate], lexical: list[RetrievalCandidate], limit: int) -> list[Citation]:
    merged: dict[uuid.UUID, RetrievalCandidate] = {}
    for candidate in vector + lexical:
        current = merged.get(candidate.chunk_id)
        if current is None:
            merged[candidate.chunk_id] = candidate
            continue
        merged[candidate.chunk_id] = RetrievalCandidate(
            chunk_id=current.chunk_id,
            document_id=current.document_id,
            document_name=current.document_name,
            content=current.content,
            page_number=current.page_number,
            heading=current.heading,
            vector_score=current.vector_score if current.vector_score is not None else candidate.vector_score,
            text_score=current.text_score if current.text_score is not None else candidate.text_score,
        )
    citations = [
        Citation(
            chunk_id=candidate.chunk_id,
            document_id=candidate.document_id,
            document_name=candidate.document_name,
            page_number=candidate.page_number,
            heading=candidate.heading,
            excerpt=candidate.content[:500],
            vector_score=candidate.vector_score,
            text_score=candidate.text_score,
            score=max(candidate.vector_score or 0.0, candidate.text_score or 0.0),
        )
        for candidate in merged.values()
    ]
    return sorted(citations, key=lambda citation: citation.score, reverse=True)[:limit]


def _scope(document_ids: list[uuid.UUID] | None) -> list[Any]:
    conditions: list[Any] = [DocumentVersion.is_searchable.is_(True), Document.active_version_id == DocumentVersion.id]
    if document_ids:
        conditions.append(Document.id.in_(document_ids))
    return conditions


async def retrieve(
    session: AsyncSession,
    query: str,
    query_embedding: list[float],
    *,
    vector_limit: int = 20,
    text_limit: int = 20,
    context_limit: int = 8,
    similarity_threshold: float = 0.0,
    document_ids: list[uuid.UUID] | None = None,
) -> list[Citation]:
    timer = Timer()
    similarity = (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("vector_score")
    vector_statement: Select[tuple[Any, ...]] = (
        select(DocumentChunk.id, Document.id, Document.original_filename, DocumentChunk.content, DocumentChunk.page_number, DocumentChunk.heading, similarity)
        .join(DocumentVersion, DocumentVersion.id == DocumentChunk.version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(and_(*_scope(document_ids), similarity >= similarity_threshold))
        .order_by(similarity.desc())
        .limit(vector_limit)
    )
    lexical_score = func.ts_rank_cd(DocumentChunk.search_vector, func.plainto_tsquery("simple", query)).label("text_score")
    text_statement: Select[tuple[Any, ...]] = (
        select(DocumentChunk.id, Document.id, Document.original_filename, DocumentChunk.content, DocumentChunk.page_number, DocumentChunk.heading, lexical_score)
        .join(DocumentVersion, DocumentVersion.id == DocumentChunk.version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(and_(*_scope(document_ids), DocumentChunk.search_vector.op("@@")(func.plainto_tsquery("simple", query))))
        .order_by(lexical_score.desc())
        .limit(text_limit)
    )
    vector_rows = (await session.execute(vector_statement)).all()
    text_rows = (await session.execute(text_statement)).all()
    vector_candidates = [RetrievalCandidate(row[0], row[1], row[2], row[3], row[4], row[5], float(row[6])) for row in vector_rows]
    text_candidates = [RetrievalCandidate(row[0], row[1], row[2], row[3], row[4], row[5], text_score=float(row[6])) for row in text_rows]
    results = merge_candidates(vector_candidates, text_candidates, context_limit)
    log_event("retrieval_completed", query_length=len(query), vector_candidates=len(vector_candidates), text_candidates=len(text_candidates), results=len(results), duration_ms=timer.elapsed_ms)
    return results





