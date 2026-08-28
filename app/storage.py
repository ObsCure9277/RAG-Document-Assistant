from pathlib import Path
import uuid


class OriginalStorage:
    def __init__(self, root: Path):
        self.root = root

    def path_for(self, document_id: uuid.UUID, filename: str) -> Path:
        return self.root / str(document_id) / filename

    async def save(self, document_id: uuid.UUID, filename: str, content: bytes) -> Path:
        destination = self.path_for(document_id, filename)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(destination)
        return destination

    def delete(self, document_id: uuid.UUID, filename: str) -> None:
        destination = self.path_for(document_id, filename)
        if destination.exists():
            destination.unlink()
        if destination.parent.exists() and not any(destination.parent.iterdir()):
            destination.parent.rmdir()
