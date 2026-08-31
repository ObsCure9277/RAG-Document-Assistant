from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol
import zipfile

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode


@dataclass(frozen=True)
class ExtractedSection:
    text: str
    source: str
    page_number: int | None = None
    heading: str | None = None


@dataclass(frozen=True)
class Chunk:
    content: str
    chunk_index: int
    source: str
    page_number: int | None
    heading: str | None


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class DocumentExtractor:
    def __init__(self, max_pages: int = 500, max_tokens: int = 200000, max_archive_bytes: int = 50 * 1024 * 1024):
        self.max_pages = max_pages
        self.max_chars = max_tokens * 4
        self.max_archive_bytes = max_archive_bytes

    def _check_budget(self, total_chars: int) -> None:
        if total_chars > self.max_chars:
            raise ValueError("Document exceeds the configured extracted-content limit")

    def _validate_docx_archive(self, path: Path, max_members: int = 10000) -> None:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > max_members:
                raise ValueError("Document exceeds the configured archive member limit")
            total_size = 0
            for member in members:
                if member.file_size < 0:
                    raise ValueError("Document contains an invalid archive member")
                total_size += member.file_size
                if total_size > self.max_archive_bytes:
                    raise ValueError("Document exceeds the configured extracted-content limit")

    def extract(self, path: Path, mime_type: str) -> list[ExtractedSection]:
        if path.suffix.lower() == ".pdf" or mime_type == "application/pdf":
            import fitz
            with fitz.open(path) as document:
                if len(document) > self.max_pages:
                    raise ValueError("Document exceeds the configured page limit")
                sections: list[ExtractedSection] = []
                total_chars = 0
                for page in document:
                    text = page.get_text().strip()
                    if text:
                        total_chars += len(text)
                        self._check_budget(total_chars)
                        sections.append(ExtractedSection(text, path.name, page.number + 1))
                return sections
        if path.suffix.lower() == ".docx":
            self._validate_docx_archive(path)
            from docx import Document
            document = Document(path)
            sections: list[ExtractedSection] = []
            heading: str | None = None
            for paragraph in document.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                if paragraph.style.name.lower().startswith("heading"):
                    heading = text
                else:
                    self._check_budget(sum(len(section.text) for section in sections) + len(text))
                    sections.append(ExtractedSection(text, path.name, heading=heading))
            return sections
        raw = path.read_bytes()
        if len(raw) > self.max_chars:
            raise ValueError("Document exceeds the configured extracted-content limit")
        text = raw.decode("utf-8")
        sections = []
        heading: str | None = None
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            else:
                sections.append(ExtractedSection(line, path.name, heading=heading))
        return sections


def chunk_sections(sections: list[ExtractedSection], target_tokens: int = 600, overlap_tokens: int = 75) -> list[Chunk]:
    """Create chunks with LlamaIndex while preserving source metadata."""
    if target_tokens <= overlap_tokens or target_tokens < 1:
        raise ValueError("target_tokens must be greater than overlap_tokens")
    splitter = SentenceSplitter(chunk_size=target_tokens, chunk_overlap=overlap_tokens)
    chunks: list[Chunk] = []
    for section in sections:
        for content in splitter.split_text(section.text):
            node = TextNode(text=content, metadata={"source": section.source, "page_number": section.page_number, "heading": section.heading})
            chunks.append(Chunk(node.get_content(), len(chunks), section.source, section.page_number, section.heading))
    return chunks
