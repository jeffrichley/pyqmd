import pathlib
import pytest
from pyqmd.retrieval.pipeline import RetrievalPipeline
from pyqmd.indexing.pipeline import IndexingPipeline
from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding
from pyqmd.storage.lancedb_backend import LanceDBBackend
from pyqmd.chunking.markdown import MarkdownChunker
from pyqmd.indexing.hasher import FileHashRegistry
from pyqmd.models import SearchResult


@pytest.fixture(scope="module")
def embedder():
    return SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")


@pytest.fixture
def indexed_backend(tmp_path, embedder, fixtures_dir):
    backend = LanceDBBackend(data_dir=tmp_path / "lancedb", dimension=embedder.dimension)
    chunker = MarkdownChunker(target_size=200, overlap=0.0)
    hasher = FileHashRegistry(tmp_path / "hashes.json")
    pipeline = IndexingPipeline(storage=backend, embedder=embedder, chunker=chunker, hasher=hasher)
    pipeline.index_directory(fixtures_dir, collection="test", mask="**/*.md")
    return backend


@pytest.fixture
def prefixed_backend(tmp_path, embedder):
    """Create indexed backend with files in subdirectories for path-prefix testing."""
    # Create directory structure
    projects_dir = tmp_path / "vault" / "projects"
    projects_dir.mkdir(parents=True)
    weekly_dir = tmp_path / "vault" / "weekly"
    weekly_dir.mkdir(parents=True)

    (projects_dir / "status.md").write_text(
        "# Project Status\n\nThe NIWC project deadline is Friday. We need to finalize the deliverables.\n"
    )
    (weekly_dir / "week14.md").write_text(
        "# Weekly Summary\n\nThis week we accomplished the migration of all services.\n"
    )

    backend = LanceDBBackend(data_dir=tmp_path / "lancedb", dimension=embedder.dimension)
    chunker = MarkdownChunker(target_size=200, overlap=0.0)
    hasher = FileHashRegistry(tmp_path / "hashes.json")
    pipeline = IndexingPipeline(storage=backend, embedder=embedder, chunker=chunker, hasher=hasher)
    pipeline.index_directory(tmp_path / "vault", collection="vault", mask="**/*.md")
    return backend


class TestRetrievalPipeline:
    def test_basic_search(self, indexed_backend, embedder):
        pipeline = RetrievalPipeline(storage=indexed_backend, embedder=embedder, reranker=None)
        results = pipeline.search("pandas dataframes", collections=["test"], top_k=5)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_relevance(self, indexed_backend, embedder):
        pipeline = RetrievalPipeline(storage=indexed_backend, embedder=embedder, reranker=None)
        results = pipeline.search("Bollinger Bands", collections=["test"], top_k=3)
        contents = [r.chunk.content for r in results]
        assert any("Bollinger" in c for c in contents)

    def test_search_with_no_rerank(self, indexed_backend, embedder):
        pipeline = RetrievalPipeline(storage=indexed_backend, embedder=embedder, reranker=None)
        results = pipeline.search("stock data", collections=["test"], top_k=3)
        assert all(r.rerank_score is None for r in results)

    def test_search_returns_scores(self, indexed_backend, embedder):
        pipeline = RetrievalPipeline(storage=indexed_backend, embedder=embedder, reranker=None)
        results = pipeline.search("indicator", collections=["test"], top_k=3)
        assert all(r.score > 0 for r in results)

    def test_search_with_path_prefix(self, prefixed_backend, embedder):
        pipeline = RetrievalPipeline(storage=prefixed_backend, embedder=embedder, reranker=None)
        results = pipeline.search(
            "deadline deliverables",
            collections=["vault"],
            top_k=10,
            path_prefix="projects",
        )
        # Only results from the projects subdirectory
        assert len(results) > 0
        # Check that weekly results are filtered out
        for r in results:
            assert "weekly" not in r.chunk.source_file.replace("\\", "/")
