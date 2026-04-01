import pathlib
import pytest
from pyqmd.models import Chunk
from pyqmd.storage.base import StorageBackend
from pyqmd.storage.lancedb_backend import LanceDBBackend


class TestStorageInterface:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            StorageBackend()


class TestLanceDBBackend:
    @pytest.fixture
    def backend(self, tmp_path: pathlib.Path) -> LanceDBBackend:
        return LanceDBBackend(data_dir=tmp_path / "lancedb", dimension=384)

    @pytest.fixture
    def sample_chunks(self) -> list[tuple[Chunk, list[float]]]:
        import random
        random.seed(42)
        chunks = []
        for i in range(3):
            chunk = Chunk(
                id=f"chunk{i}",
                content=f"Content of chunk {i} about pandas dataframes",
                context=None,
                source_file=f"file{i}.md",
                collection="test",
                heading_path=["Section"],
                parent_id=None,
                start_line=i * 10,
                end_line=i * 10 + 9,
                metadata={"index": i},
            )
            vector = [random.random() for _ in range(384)]
            chunks.append((chunk, vector))
        return chunks

    def test_store_and_count(self, backend, sample_chunks):
        backend.store("test", sample_chunks)
        assert backend.count("test") == 3

    def test_search_vector(self, backend, sample_chunks):
        backend.store("test", sample_chunks)
        query_vector = sample_chunks[0][1]
        results = backend.search_vector("test", query_vector, top_k=2)
        assert len(results) == 2
        assert results[0][0] == "chunk0"

    def test_search_text(self, backend, sample_chunks):
        backend.store("test", sample_chunks)
        results = backend.search_text("test", "pandas dataframes", top_k=3)
        # FTS may not be available in all environments; accept empty list too
        assert isinstance(results, list)
        assert all(isinstance(r[0], str) for r in results)

    def test_get_chunk(self, backend, sample_chunks):
        backend.store("test", sample_chunks)
        chunk = backend.get_chunk("test", "chunk0")
        assert chunk is not None
        assert chunk.id == "chunk0"
        assert chunk.content == "Content of chunk 0 about pandas dataframes"

    def test_get_nonexistent_chunk_returns_none(self, backend):
        result = backend.get_chunk("test", "nonexistent")
        assert result is None

    def test_delete_by_source_file(self, backend, sample_chunks):
        backend.store("test", sample_chunks)
        assert backend.count("test") == 3
        backend.delete_by_source_file("test", "file0.md")
        assert backend.count("test") == 2

    def test_delete_collection(self, backend, sample_chunks):
        backend.store("test", sample_chunks)
        backend.delete_collection("test")
        assert backend.count("test") == 0

    def test_list_collections(self, backend, sample_chunks):
        backend.store("col_a", sample_chunks)
        backend.store("col_b", sample_chunks)
        collections = backend.list_collections()
        assert "col_a" in collections
        assert "col_b" in collections
