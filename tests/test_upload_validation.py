import pytest

from app.documents import Upload, validate_upload


def test_supported_uploads_are_accepted():
    for filename in ("notes.txt", "paper.pdf", "resume.docx", "readme.md"):
        validate_upload(Upload(filename, b"content", "text/plain"), 100)


def test_unsupported_and_oversized_uploads_have_actionable_errors():
    with pytest.raises(ValueError, match="Unsupported file type"):
        validate_upload(Upload("archive.zip", b"content", "application/zip"), 100)
    with pytest.raises(ValueError, match="maximum size"):
        validate_upload(Upload("notes.txt", b"12345", "text/plain"), 4)
