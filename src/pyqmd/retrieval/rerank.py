"""Cross-encoder reranking for search results."""

from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, items: list[tuple[str, str]], top_k: int = 10) -> list[tuple[str, float]]:
        if not items:
            return []
        pairs = [(query, text) for _, text in items]
        scores = self._model.predict(pairs)
        scored = list(zip([item_id for item_id, _ in items], scores.tolist()))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
