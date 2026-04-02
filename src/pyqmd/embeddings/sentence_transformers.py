"""SentenceTransformer embedding model."""

import io
import logging
import os
import sys
import warnings

from pyqmd.embeddings.base import EmbeddingModel


class SentenceTransformerEmbedding(EmbeddingModel):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Suppress all noisy model loading output (progress bars, weight reports)
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("transformers").setLevel(logging.ERROR)

        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                os.environ["TRANSFORMERS_VERBOSITY"] = "error"
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(model_name)
        finally:
            sys.stderr = old_stderr

        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension
