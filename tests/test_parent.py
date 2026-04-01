from pyqmd.models import Chunk
from pyqmd.retrieval.parent import expand_parents


def _make_chunk(id: str, parent_id: str | None = None, content: str = "text") -> Chunk:
    return Chunk(id=id, content=content, context=None, source_file="test.md",
                 collection="test", heading_path=[], parent_id=parent_id,
                 start_line=0, end_line=0, metadata={})


class TestExpandParents:
    def test_no_parents_returns_same(self):
        chunks = [_make_chunk("a"), _make_chunk("b")]
        lookup = {c.id: c for c in chunks}
        expanded = expand_parents(["a", "b"], lookup)
        assert [c.id for c in expanded] == ["a", "b"]

    def test_adds_parent_chunk(self):
        parent = _make_chunk("parent", content="Parent content")
        child = _make_chunk("child", parent_id="parent", content="Child content")
        lookup = {c.id: c for c in [parent, child]}
        expanded = expand_parents(["child"], lookup)
        ids = [c.id for c in expanded]
        assert "child" in ids
        assert "parent" in ids

    def test_no_duplicate_parents(self):
        parent = _make_chunk("parent", content="Parent content")
        child1 = _make_chunk("child1", parent_id="parent")
        child2 = _make_chunk("child2", parent_id="parent")
        lookup = {c.id: c for c in [parent, child1, child2]}
        expanded = expand_parents(["child1", "child2"], lookup)
        ids = [c.id for c in expanded]
        assert ids.count("parent") == 1

    def test_original_order_preserved(self):
        parent = _make_chunk("parent")
        child = _make_chunk("child", parent_id="parent")
        other = _make_chunk("other")
        lookup = {c.id: c for c in [parent, child, other]}
        expanded = expand_parents(["child", "other"], lookup)
        child_idx = next(i for i, c in enumerate(expanded) if c.id == "child")
        other_idx = next(i for i, c in enumerate(expanded) if c.id == "other")
        assert child_idx < other_idx
