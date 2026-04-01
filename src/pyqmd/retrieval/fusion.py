"""Reciprocal Rank Fusion for merging search results."""


def reciprocal_rank_fusion(
    result_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    if not result_lists:
        return []
    scores: dict[str, float] = {}
    for results in result_lists:
        for rank, (item_id, _original_score) in enumerate(results):
            rrf_score = 1.0 / (k + rank + 1)
            scores[item_id] = scores.get(item_id, 0.0) + rrf_score
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused
