import json
import pathlib

from pyqmd.config import PyQMDConfig


class TestConfig:
    def test_default_config(self, tmp_path: pathlib.Path):
        config = PyQMDConfig(data_dir=tmp_path / ".pyqmd")
        assert config.data_dir == tmp_path / ".pyqmd"
        assert config.embed_model == "all-MiniLM-L6-v2"
        assert config.chunk_size == 800
        assert config.storage_backend == "lancedb"

    def test_save_and_load(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)
        config.embed_model = "nomic-embed-text"
        config.save()

        loaded = PyQMDConfig.load(data_dir)
        assert loaded.embed_model == "nomic-embed-text"
        assert loaded.chunk_size == 800

    def test_load_nonexistent_returns_defaults(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig.load(data_dir)
        assert config.embed_model == "all-MiniLM-L6-v2"

    def test_collections_crud(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)

        config.add_collection("notes", ["/home/user/notes"], mask="**/*.md")
        assert "notes" in config.collections
        assert config.collections["notes"].paths == ["/home/user/notes"]

        config.remove_collection("notes")
        assert "notes" not in config.collections

    def test_add_duplicate_collection_raises(self, tmp_path: pathlib.Path):
        import pytest
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)
        config.add_collection("notes", ["/path"])
        with pytest.raises(ValueError, match="already exists"):
            config.add_collection("notes", ["/other"])

    def test_remove_nonexistent_collection_raises(self, tmp_path: pathlib.Path):
        import pytest
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)
        with pytest.raises(KeyError, match="not found"):
            config.remove_collection("nonexistent")
