"""Parent chunk expansion for richer context in search results."""

from pyqmd.models import Chunk


def expand_parents(chunk_ids: list[str], chunk_lookup: dict[str, Chunk]) -> list[Chunk]:
    seen: set[str] = set()
    result: list[Chunk] = []

    for chunk_id in chunk_ids:
        chunk = chunk_lookup.get(chunk_id)
        if chunk is None:
            continue
        if chunk.parent_id and chunk.parent_id not in seen:
            parent = chunk_lookup.get(chunk.parent_id)
            if parent is not None:
                result.append(parent)
                seen.add(parent.id)
        if chunk_id not in seen:
            result.append(chunk)
            seen.add(chunk_id)

    return result
