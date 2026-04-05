from pyqmd.models import (
    Chunk,
    Collection,
    CollectionConfig,
    SearchConfig,
    SearchResult,
    WatchConfig,
)


class TestCollectionConfig:
    def test_defaults(self):
        cfg = CollectionConfig()
        assert cfg.mask == "**/*.md"
        assert cfg.chunk_size is None
        assert cfg.chunk_overlap is None
        assert cfg.embed_model is None

    def test_override(self):
        cfg = CollectionConfig(chunk_size=1600)
        assert cfg.chunk_size == 1600


class TestWatchConfig:
    def test_defaults(self):
        cfg = WatchConfig()
        assert cfg.debounce == 2.0
        assert cfg.poll_interval == 0.0
        assert ".git/" in cfg.ignore_patterns

    def test_override(self):
        cfg = WatchConfig(debounce=5.0, ignore_patterns=[".git/"])
        assert cfg.debounce == 5.0
        assert cfg.ignore_patterns == [".git/"]


class TestSearchConfig:
    def test_defaults(self):
        cfg = SearchConfig()
        assert cfg.overfetch_multiplier == 2


class TestCollection:
    def test_defaults(self):
        col = Collection(name="test", paths=["/tmp"])
        assert col.mask == "**/*.md"
        assert col.chunk_size == 800
        assert col.chunk_overlap == 0.15

    def test_override(self):
        col = Collection(name="test", paths=["/tmp"], chunk_size=1600)
        assert col.chunk_size == 1600


class TestChunk:
    def test_embeddable_content_without_context(self):
        chunk = Chunk(
            id="abc",
            content="Hello world",
            source_file="test.md",
            collection="test",
        )
        assert chunk.embeddable_content == "Hello world"

    def test_embeddable_content_with_context(self):
        chunk = Chunk(
            id="abc",
            content="Hello world",
            context="This is context",
            source_file="test.md",
            collection="test",
        )
        assert chunk.embeddable_content == "This is context\n\nHello world"

    def test_mutable_context(self):
        chunk = Chunk(
            id="abc",
            content="Hello",
            source_file="test.md",
            collection="test",
        )
        chunk.context = "new context"
        assert chunk.context == "new context"


class TestSearchResult:
    def test_basic(self):
        chunk = Chunk(
            id="abc",
            content="Hello",
            source_file="test.md",
            collection="test",
        )
        result = SearchResult(chunk=chunk, score=0.95)
        assert result.score == 0.95
        assert result.bm25_score is None
