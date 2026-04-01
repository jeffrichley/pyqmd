from pyqmd.models import Chunk, SearchResult, Collection, CollectionConfig


class TestChunk:
    def test_create_chunk(self):
        chunk = Chunk(
            id="abc123",
            content="Hello world",
            context=None,
            source_file="/path/to/file.md",
            collection="notes",
            heading_path=["H1 Title", "H2 Section"],
            parent_id=None,
            start_line=1,
            end_line=10,
            metadata={},
        )
        assert chunk.id == "abc123"
        assert chunk.content == "Hello world"
        assert chunk.context is None
        assert chunk.heading_path == ["H1 Title", "H2 Section"]

    def test_chunk_with_context(self):
        chunk = Chunk(
            id="abc123",
            content="Use the --no-cache flag.",
            context="This section describes CLI flags for the build tool.",
            source_file="/path/to/file.md",
            collection="notes",
            heading_path=[],
            parent_id="parent1",
            start_line=5,
            end_line=8,
            metadata={"project": "Martingale"},
        )
        assert chunk.context == "This section describes CLI flags for the build tool."
        assert chunk.parent_id == "parent1"
        assert chunk.metadata["project"] == "Martingale"

    def test_chunk_content_for_embedding_without_context(self):
        chunk = Chunk(
            id="abc123",
            content="Hello world",
            context=None,
            source_file="/path/to/file.md",
            collection="notes",
            heading_path=[],
            parent_id=None,
            start_line=1,
            end_line=1,
            metadata={},
        )
        assert chunk.embeddable_content == "Hello world"

    def test_chunk_content_for_embedding_with_context(self):
        chunk = Chunk(
            id="abc123",
            content="Use the --no-cache flag.",
            context="This section describes CLI flags.",
            source_file="/path/to/file.md",
            collection="notes",
            heading_path=[],
            parent_id=None,
            start_line=1,
            end_line=1,
            metadata={},
        )
        assert chunk.embeddable_content == "This section describes CLI flags.\n\nUse the --no-cache flag."


class TestSearchResult:
    def test_create_search_result(self):
        chunk = Chunk(
            id="abc123",
            content="test",
            context=None,
            source_file="test.md",
            collection="notes",
            heading_path=[],
            parent_id=None,
            start_line=1,
            end_line=1,
            metadata={},
        )
        result = SearchResult(
            chunk=chunk,
            score=0.85,
            bm25_score=0.7,
            vector_score=0.9,
            rerank_score=None,
        )
        assert result.score == 0.85
        assert result.bm25_score == 0.7
        assert result.rerank_score is None


class TestCollection:
    def test_create_collection(self):
        config = CollectionConfig()
        collection = Collection(
            name="notes",
            paths=["/home/user/notes"],
            mask="**/*.md",
            config=config,
        )
        assert collection.name == "notes"
        assert collection.mask == "**/*.md"

    def test_collection_config_defaults(self):
        config = CollectionConfig()
        assert config.chunk_size == 800
        assert config.chunk_overlap == 0.15
        assert config.embed_model == "all-MiniLM-L6-v2"
