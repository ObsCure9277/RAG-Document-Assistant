from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePath

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


@dataclass(frozen=True)
class Upload:
    filename: str
    content: bytes
    mime_type: str

    @property
    def extension(self) -> str:
        return PurePath(self.filename).suffix.lower()

    @property
    def checksum(self) -> str:
        return sha256(self.content).hexdigest()


def validate_upload(upload: Upload, max_bytes: int) -> None:
    if upload.extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS - {".markdown"}))
        raise ValueError(f"Unsupported file type. Please upload: {supported}.")
    if len(upload.content) > max_bytes:
        raise ValueError(f"File is too large. The maximum size is {max_bytes} bytes.")
