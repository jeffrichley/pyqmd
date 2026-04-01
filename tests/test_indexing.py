import pathlib
import pytest
from pyqmd.indexing.pipeline import IndexingPipeline
from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding
from pyqmd.storage.lancedb_backend import LanceDBBackend
from pyqmd.chunking.markdown import MarkdownChunker
from pyqmd.indexing.hasher import FileHashRegistry


@pytest.fixture(scope="module")
def embedder():
    return SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")


class TestIndexingPipeline:
    @pytest.fixture
    def pipeline(self, tmp_path, embedder):
        backend = LanceDBBackend(data_dir=tmp_path / "lancedb", dimension=embedder.dimension)
        chunker = MarkdownChunker(target_size=200, overlap=0.0)
        hasher = FileHashRegistry(tmp_path / "hashes.json")
        return IndexingPipeline(storage=backend, embedder=embedder, chunker=chunker, hasher=hasher)

    def test_index_single_file(self, pipeline, simple_md):
        count = pipeline.index_file(simple_md, collection="test")
        assert count > 0
        assert pipeline.storage.count("test") == count

    def test_index_directory(self, pipeline, tmp_collection):
        count = pipeline.index_directory(tmp_collection, collection="test", mask="**/*.md")
        assert count > 0
        assert pipeline.storage.count("test") == count

    def test_incremental_skips_unchanged(self, pipeline, simple_md):
        count1 = pipeline.index_file(simple_md, collection="test")
        count2 = pipeline.index_file(simple_md, collection="test")
        assert count1 > 0
        assert count2 == 0

    def test_incremental_reindexes_changed(self, pipeline, tmp_path):
        md_file = tmp_path / "changing.md"
        md_file.write_text("# Version 1\n\nOriginal content.")
        count1 = pipeline.index_file(md_file, collection="test")
        assert count1 > 0
        md_file.write_text("# Version 2\n\nNew content entirely different.")
        count2 = pipeline.index_file(md_file, collection="test")
        assert count2 > 0

    def test_force_reindex(self, pipeline, simple_md):
        count1 = pipeline.index_file(simple_md, collection="test")
        count2 = pipeline.index_file(simple_md, collection="test", force=True)
        assert count2 > 0
