import uuid

from app.lifecycle import enqueue_reindex, enqueue_retry, latest_version
from app.models import Document, DocumentVersion


def test_reindex_creates_a_new_immutable_version_without_changing_active_version():
    document = Document(id=uuid.uuid4(), title="Notes", original_filename="notes.txt", mime_type="text/plain", checksum="a" * 64, size_bytes=5)
    original = DocumentVersion(id=uuid.uuid4(), version_number=1, checksum=document.checksum, status="indexed")
    document.versions.append(original)
    document.active_version_id = original.id

    replacement = enqueue_reindex(document)

    assert replacement.version_number == 2
    assert replacement.status == "uploaded"
    assert document.active_version_id == original.id
    assert len(replacement.ingestion_jobs) == 1


def test_retry_enqueues_a_fresh_job_and_resets_failed_version():
    version = DocumentVersion(version_number=1, checksum="b" * 64, status="failed", is_searchable=False)
    job = enqueue_retry(version)

    assert version.status == "uploaded"
    assert job.status == "queued"
    assert version.ingestion_jobs == [job]


def test_latest_version_uses_version_number():
    document = Document(id=uuid.uuid4(), title="Notes", original_filename="notes.txt", mime_type="text/plain", checksum="c" * 64, size_bytes=5)
    first = DocumentVersion(id=uuid.uuid4(), version_number=1, checksum=document.checksum)
    second = DocumentVersion(id=uuid.uuid4(), version_number=2, checksum=document.checksum)
    document.versions.extend([second, first])
    assert latest_version(document) is second

