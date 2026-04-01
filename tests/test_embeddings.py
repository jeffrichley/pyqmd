import pytest
from pyqmd.embeddings.base import EmbeddingModel
from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding


class TestEmbeddingInterface:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            EmbeddingModel()


class TestSentenceTransformerEmbedding:
    @pytest.fixture(scope="class")
    def embedder(self):
        return SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")

    def test_embed_single_text(self, embedder):
        vectors = embedder.embed(["Hello world"])
        assert len(vectors) == 1
        assert len(vectors[0]) == 384

    def test_embed_multiple_texts(self, embedder):
        texts = ["Hello world", "Goodbye world", "Another sentence"]
        vectors = embedder.embed(texts)
        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)

    def test_similar_texts_have_higher_similarity(self, embedder):
        import numpy as np
        vectors = embedder.embed([
            "How to install pandas",
            "Installing pandas with pip",
            "The weather is nice today",
        ])
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        sim_related = cosine_sim(vectors[0], vectors[1])
        sim_unrelated = cosine_sim(vectors[0], vectors[2])
        assert sim_related > sim_unrelated

    def test_dimension_property(self, embedder):
        assert embedder.dimension == 384
