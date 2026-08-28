import uuid

from app.retrieval import RetrievalCandidate, merge_candidates


def test_hybrid_candidates_are_deduplicated_and_ranked():
    chunk_id = uuid.uuid4()
    first = RetrievalCandidate(chunk_id, uuid.uuid4(), "notes.md", "supporting evidence", 3, "Heading", vector_score=0.7)
    duplicate = RetrievalCandidate(chunk_id, first.document_id, first.document_name, first.content, first.page_number, first.heading, text_score=0.9)
    other = RetrievalCandidate(uuid.uuid4(), uuid.uuid4(), "other.md", "other evidence", None, None, vector_score=0.8)
    results = merge_candidates([first, other], [duplicate], 10)
    assert [result.chunk_id for result in results] == [chunk_id, other.chunk_id]
    assert results[0].vector_score == 0.7
    assert results[0].text_score == 0.9
    assert results[0].page_number == 3
