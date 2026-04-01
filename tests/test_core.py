import pathlib
import pytest
from pyqmd.core import PyQMD
from pyqmd.models import SearchResult


class TestPyQMD:
    @pytest.fixture
    def qmd(self, tmp_path):
        return PyQMD(data_dir=tmp_path / ".pyqmd")

    def test_add_collection(self, qmd, fixtures_dir):
        qmd.add_collection("test", paths=[str(fixtures_dir)])
        assert "test" in qmd.list_collections()

    def test_remove_collection(self, qmd, fixtures_dir):
        qmd.add_collection("test", paths=[str(fixtures_dir)])
        qmd.remove_collection("test")
        assert "test" not in qmd.list_collections()

    def test_index_and_search(self, qmd, fixtures_dir):
        qmd.add_collection("test", paths=[str(fixtures_dir)])
        count = qmd.index("test")
        assert count > 0
        results = qmd.search("Bollinger Bands", top_k=3)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_specific_collection(self, qmd, fixtures_dir):
        qmd.add_collection("test", paths=[str(fixtures_dir)])
        qmd.index("test")
        results = qmd.search("stock data", collections=["test"], top_k=3)
        assert len(results) > 0

    def test_search_empty_collection(self, qmd):
        results = qmd.search("anything", collections=["nonexistent"], top_k=3)
        assert results == []

    def test_status(self, qmd, fixtures_dir):
        qmd.add_collection("test", paths=[str(fixtures_dir)])
        qmd.index("test")
        status = qmd.status("test")
        assert status["name"] == "test"
        assert status["chunk_count"] > 0
        assert "paths" in status
