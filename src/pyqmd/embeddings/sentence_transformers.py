"""SentenceTransformer embedding model."""

import logging
import warnings

from sentence_transformers import SentenceTransformer

from pyqmd.embeddings.base import EmbeddingModel


class SentenceTransformerEmbedding(EmbeddingModel):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Suppress noisy model loading warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
            self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension
