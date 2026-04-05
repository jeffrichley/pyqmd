"""Retrieval pipeline: hybrid BM25 + vector search with RRF fusion, reranking, and parent expansion."""

from pyqmd.embeddings.base import EmbeddingModel
from pyqmd.models import Chunk, SearchResult
from pyqmd.retrieval.fusion import reciprocal_rank_fusion
from pyqmd.retrieval.parent import expand_parents
from pyqmd.storage.base import StorageBackend


class RetrievalPipeline:
    """Orchestrates query → parallel BM25+vector → RRF fusion → optional rerank → optional parent expansion."""

    def __init__(
        self,
        storage: StorageBackend,
        embedder: EmbeddingModel,
        reranker=None,
        hyde_generator=None,
    ):
        self.storage = storage
        self.embedder = embedder
        self.reranker = reranker
        self.hyde_generator = hyde_generator

    def search(
        self,
        query: str,
        collections: list[str],
        top_k: int = 10,
        rerank: bool = True,
        expand_parent: bool = False,
        hyde: bool = False,
        path_prefix: str | None = None,
        overfetch_multiplier: int = 2,
    ) -> list[SearchResult]:
        """Search across collections using hybrid BM25+vector retrieval with RRF fusion.

        Args:
            query: The search query string.
            collections: List of collection names to search.
            top_k: Maximum number of results to return.
            rerank: Whether to apply cross-encoder reranking (only if reranker is set).
            expand_parent: Whether to expand results to parent chunks for more context.
            hyde: Whether to use HyDE (Hypothetical Document Embeddings) for the vector search.
            path_prefix: If set, only return results from files whose path contains this prefix.
            overfetch_multiplier: Multiplier for overfetching candidates before filtering/reranking.

        Returns:
            List of SearchResult objects sorted by descending score.
        """
        # 1. Embed query (optionally via HyDE)
        if hyde and self.hyde_generator:
            hypothetical = self.hyde_generator.generate_hypothetical(query)
            query_vector = self.embedder.embed([hypothetical])[0]
        else:
            query_vector = self.embedder.embed([query])[0]

        # 2. Parallel BM25 + vector search across all collections
        all_bm25: list[tuple[str, float]] = []
        all_vector: list[tuple[str, float]] = []

        for collection in collections:
            bm25_results = self.storage.search_text(collection, query, top_k=top_k * overfetch_multiplier)
            vector_results = self.storage.search_vector(collection, query_vector, top_k=top_k * overfetch_multiplier)
            all_bm25.extend(bm25_results)
            all_vector.extend(vector_results)

        # 3. RRF fusion
        result_lists = []
        if all_bm25:
            result_lists.append(all_bm25)
        if all_vector:
            result_lists.append(all_vector)
        if not result_lists:
            return []

        fused: list[tuple[str, float]] = reciprocal_rank_fusion(result_lists, k=60)

        # 4. Build lookup maps for scores and collect unique chunk_ids
        bm25_score_map: dict[str, float] = {cid: score for cid, score in all_bm25}
        vector_score_map: dict[str, float] = {cid: score for cid, score in all_vector}

        # Limit to top_k * overfetch_multiplier before fetching to avoid unnecessary lookups
        candidate_ids = [chunk_id for chunk_id, _ in fused[: top_k * overfetch_multiplier]]
        fused_score_map: dict[str, float] = {chunk_id: score for chunk_id, score in fused}

        # 5. Fetch Chunk objects from storage
        chunks: dict[str, Chunk] = {}
        for chunk_id in candidate_ids:
            # Determine which collection owns this chunk_id
            for collection in collections:
                chunk = self.storage.get_chunk(collection, chunk_id)
                if chunk is not None:
                    chunks[chunk_id] = chunk
                    break

        # Build SearchResults for fetched chunks (preserve fused order)
        results: list[SearchResult] = []
        for chunk_id in candidate_ids:
            chunk = chunks.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                SearchResult(
                    chunk=chunk,
                    score=fused_score_map[chunk_id],
                    bm25_score=bm25_score_map.get(chunk_id),
                    vector_score=vector_score_map.get(chunk_id),
                    rerank_score=None,
                )
            )

        # 6. Filter by path prefix
        if path_prefix:
            norm_prefix = path_prefix.replace("\\", "/")
            results = [
                r for r in results
                if norm_prefix in r.chunk.source_file.replace("\\", "/")
            ]

        # 7. Optional parent expansion
        if expand_parent and results:
            chunk_lookup: dict[str, Chunk] = {r.chunk.id: r.chunk for r in results}
            expanded_chunks = expand_parents([r.chunk.id for r in results], chunk_lookup)
            # Rebuild results from expanded chunks, preserving scores where available
            existing_score_map: dict[str, float] = {r.chunk.id: r.score for r in results}
            expanded_results: list[SearchResult] = []
            for chunk in expanded_chunks:
                score = existing_score_map.get(chunk.id, 0.0)
                expanded_results.append(
                    SearchResult(
                        chunk=chunk,
                        score=score,
                        bm25_score=bm25_score_map.get(chunk.id),
                        vector_score=vector_score_map.get(chunk.id),
                        rerank_score=None,
                    )
                )
            results = expanded_results

        # 8. Optional reranking
        if rerank and self.reranker is not None and results:
            items = [(r.chunk.id, r.chunk.content) for r in results]
            reranked = self.reranker.rerank(query, items, top_k=top_k)
            rerank_score_map: dict[str, float] = {cid: score for cid, score in reranked}
            chunk_map: dict[str, SearchResult] = {r.chunk.id: r for r in results}
            reranked_results: list[SearchResult] = []
            for chunk_id, rr_score in reranked:
                original = chunk_map.get(chunk_id)
                if original is None:
                    continue
                reranked_results.append(
                    SearchResult(
                        chunk=original.chunk,
                        score=original.score,
                        bm25_score=original.bm25_score,
                        vector_score=original.vector_score,
                        rerank_score=rr_score,
                    )
                )
            return reranked_results[:top_k]

        return results[:top_k]
