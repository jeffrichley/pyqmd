"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from pyqmd.models import Chunk


class StorageBackend(ABC):
    @abstractmethod
    def store(self, collection: str, chunks_with_vectors: list[tuple[Chunk, list[float]]]) -> None:
        """Store chunks with their embedding vectors."""

    @abstractmethod
    def search_vector(self, collection: str, query_vector: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        """Search by vector similarity. Returns list of (chunk_id, score)."""

    @abstractmethod
    def search_text(self, collection: str, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search by full text (BM25). Returns list of (chunk_id, score)."""

    @abstractmethod
    def get_chunk(self, collection: str, chunk_id: str) -> Chunk | None:
        """Retrieve a chunk by ID."""

    @abstractmethod
    def delete_by_source_file(self, collection: str, source_file: str) -> None:
        """Delete all chunks from a specific source file."""

    @abstractmethod
    def delete_collection(self, collection: str) -> None:
        """Delete an entire collection."""

    @abstractmethod
    def count(self, collection: str) -> int:
        """Count chunks in a collection."""

    @abstractmethod
    def list_collections(self) -> list[str]:
        """List all collection names."""
