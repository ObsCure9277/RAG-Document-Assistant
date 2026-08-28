from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol


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
    def extract(self, path: Path, mime_type: str) -> list[ExtractedSection]:
        if path.suffix.lower() == ".pdf" or mime_type == "application/pdf":
            import fitz
            with fitz.open(path) as document:
                return [ExtractedSection(page.get_text().strip(), path.name, page.number + 1) for page in document if page.get_text().strip()]
        if path.suffix.lower() == ".docx":
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
                    sections.append(ExtractedSection(text, path.name, heading=heading))
            return sections
        text = path.read_text(encoding="utf-8")
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
    """Create deterministic sentence-aware chunks using words as a token approximation."""
    if target_tokens <= overlap_tokens or target_tokens < 1:
        raise ValueError("target_tokens must be greater than overlap_tokens")
    chunks: list[Chunk] = []
    for section in sections:
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", section.text) if sentence.strip()]
        words: list[str] = []
        for sentence in sentences:
            sentence_words = sentence.split()
            if words and len(words) + len(sentence_words) > target_tokens:
                chunks.append(Chunk(" ".join(words), len(chunks), section.source, section.page_number, section.heading))
                words = words[-overlap_tokens:]
            words.extend(sentence_words)
        if words:
            chunks.append(Chunk(" ".join(words), len(chunks), section.source, section.page_number, section.heading))
    return chunks
