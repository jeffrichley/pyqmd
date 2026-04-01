"""Abstract base class for embedding models."""

from abc import ABC, abstractmethod


class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """The dimensionality of the embedding vectors."""
