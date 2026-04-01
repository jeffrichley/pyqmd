import pathlib
from pyqmd.chunking.markdown import MarkdownChunker
from pyqmd.models import Chunk


class TestMarkdownChunker:
    def test_chunks_simple_document(self, simple_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=200, overlap=0.0)
        chunks = chunker.chunk_file(simple_md, collection="test")
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_preserves_heading_path(self, simple_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=200, overlap=0.0)
        chunks = chunker.chunk_file(simple_md, collection="test")
        advanced = [c for c in chunks if "Advanced Config" in c.content]
        assert len(advanced) == 1
        assert "Getting Started" in advanced[0].heading_path
        assert "Configuration" in advanced[0].heading_path

    def test_never_splits_code_blocks(self, with_code_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=50, overlap=0.0)
        chunks = chunker.chunk_file(with_code_md, collection="test")
        for chunk in chunks:
            fences = chunk.content.count("```")
            assert fences % 2 == 0, f"Code block split in chunk: {chunk.content[:80]}"

    def test_parses_frontmatter_as_metadata(self, with_frontmatter_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=500, overlap=0.0)
        chunks = chunker.chunk_file(with_frontmatter_md, collection="test")
        assert len(chunks) > 0
        assert chunks[0].metadata.get("project") == "Martingale"
        assert chunks[0].metadata.get("category") == "assignments"

    def test_all_chunks_share_frontmatter_metadata(self, with_frontmatter_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=100, overlap=0.0)
        chunks = chunker.chunk_file(with_frontmatter_md, collection="test")
        for chunk in chunks:
            assert chunk.metadata.get("project") == "Martingale"

    def test_large_document_produces_multiple_chunks(self, large_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=200, overlap=0.0)
        chunks = chunker.chunk_file(large_md, collection="test")
        assert len(chunks) >= 3

    def test_parent_child_relationships(self, nested_headings_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=150, overlap=0.0)
        chunks = chunker.chunk_file(nested_headings_md, collection="test")
        chunks_with_parents = [c for c in chunks if c.parent_id is not None]
        assert len(chunks_with_parents) > 0

    def test_chunk_ids_are_unique(self, large_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=200, overlap=0.0)
        chunks = chunker.chunk_file(large_md, collection="test")
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_source_file_is_set(self, simple_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=500, overlap=0.0)
        chunks = chunker.chunk_file(simple_md, collection="test")
        for chunk in chunks:
            assert chunk.source_file == str(simple_md)

    def test_collection_is_set(self, simple_md: pathlib.Path):
        chunker = MarkdownChunker(target_size=500, overlap=0.0)
        chunks = chunker.chunk_file(simple_md, collection="my_notes")
        for chunk in chunks:
            assert chunk.collection == "my_notes"

    def test_overlap_produces_more_chunks(self, large_md: pathlib.Path):
        chunker_no_overlap = MarkdownChunker(target_size=200, overlap=0.0)
        chunker_with_overlap = MarkdownChunker(target_size=200, overlap=0.15)
        chunks_no = chunker_no_overlap.chunk_file(large_md, collection="test")
        chunks_yes = chunker_with_overlap.chunk_file(large_md, collection="test")
        assert len(chunks_yes) >= len(chunks_no)
