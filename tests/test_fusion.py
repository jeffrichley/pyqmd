from pyqmd.retrieval.fusion import reciprocal_rank_fusion


class TestRRF:
    def test_single_result_list(self):
        bm25 = [("a", 10.0), ("b", 5.0), ("c", 1.0)]
        fused = reciprocal_rank_fusion([bm25], k=60)
        assert len(fused) == 3
        assert fused[0][0] == "a"

    def test_two_result_lists_agreement(self):
        bm25 = [("a", 10.0), ("b", 5.0), ("c", 1.0)]
        vector = [("a", 0.9), ("c", 0.7), ("b", 0.5)]
        fused = reciprocal_rank_fusion([bm25, vector], k=60)
        assert fused[0][0] == "a"

    def test_two_result_lists_disagreement(self):
        bm25 = [("a", 10.0), ("b", 5.0)]
        vector = [("b", 0.9), ("a", 0.5)]
        fused = reciprocal_rank_fusion([bm25, vector], k=60)
        ids = [f[0] for f in fused]
        assert set(ids) == {"a", "b"}

    def test_unique_items_across_lists(self):
        bm25 = [("a", 10.0)]
        vector = [("b", 0.9)]
        fused = reciprocal_rank_fusion([bm25, vector], k=60)
        assert len(fused) == 2

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion([], k=60)
        assert fused == []

    def test_scores_are_positive(self):
        bm25 = [("a", 10.0), ("b", 5.0)]
        vector = [("a", 0.9), ("b", 0.5)]
        fused = reciprocal_rank_fusion([bm25, vector], k=60)
        assert all(score > 0 for _, score in fused)
