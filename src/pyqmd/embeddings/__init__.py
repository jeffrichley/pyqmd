"""Embedding model interfaces for pyqmd."""

from pyqmd.embeddings.base import EmbeddingModel
from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding

__all__ = ["EmbeddingModel", "SentenceTransformerEmbedding"]
