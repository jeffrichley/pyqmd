import pytest
from pyqmd.retrieval.rerank import CrossEncoderReranker


class TestCrossEncoderReranker:
    @pytest.fixture(scope="class")
    def reranker(self):
        return CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")

    def test_rerank_returns_same_items(self, reranker):
        items = [
            ("id1", "Python is a programming language"),
            ("id2", "The weather is sunny today"),
            ("id3", "Installing Python packages with pip"),
        ]
        results = reranker.rerank("How to install Python?", items, top_k=3)
        assert len(results) == 3
        ids = {r[0] for r in results}
        assert ids == {"id1", "id2", "id3"}

    def test_rerank_boosts_relevant_results(self, reranker):
        items = [
            ("id1", "The weather is sunny today"),
            ("id2", "Installing Python packages with pip install"),
            ("id3", "Cooking a delicious pasta recipe"),
        ]
        results = reranker.rerank("How to install Python packages?", items, top_k=3)
        assert results[0][0] == "id2"

    def test_rerank_respects_top_k(self, reranker):
        items = [("id1", "text one"), ("id2", "text two"), ("id3", "text three")]
        results = reranker.rerank("query", items, top_k=2)
        assert len(results) == 2
