import pathlib

import pytest

from pyqmd.config import PyQMDConfig


class TestConfigDefaults:
    def test_default_config(self, tmp_path: pathlib.Path):
        config = PyQMDConfig(data_dir=tmp_path / ".pyqmd")
        assert config.data_dir == tmp_path / ".pyqmd"
        assert config.embed_model == "all-MiniLM-L6-v2"
        assert config.chunk_size == 800
        assert config.chunk_overlap == 0.15
        assert config.watch.debounce == 2.0
        assert config.search.overfetch_multiplier == 2

    def test_load_nonexistent_returns_defaults(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig.load(data_dir)
        assert config.embed_model == "all-MiniLM-L6-v2"
        assert config.chunk_size == 800


class TestConfigSaveLoad:
    def test_save_creates_toml(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)
        config.save()
        assert (data_dir / "config.toml").exists()

    def test_roundtrip(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir, embed_model="nomic-embed-text")
        config.add_collection("vault", ["/home/user/vault"], mask="**/*.md")
        config.save()

        loaded = PyQMDConfig.load(data_dir)
        assert loaded.embed_model == "nomic-embed-text"
        assert "vault" in loaded.collections
        assert loaded.collections["vault"].paths == ["/home/user/vault"]

    def test_watch_config_roundtrip(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)
        config.watch.debounce = 5.0
        config.watch.poll_interval = 30.0
        config.save()

        loaded = PyQMDConfig.load(data_dir)
        assert loaded.watch.debounce == 5.0
        assert loaded.watch.poll_interval == 30.0

    def test_search_config_roundtrip(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir)
        config.search.overfetch_multiplier = 4
        config.save()

        loaded = PyQMDConfig.load(data_dir)
        assert loaded.search.overfetch_multiplier == 4


class TestConfigResolution:
    def test_collection_inherits_global_chunk_size(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir, chunk_size=1200)
        col = config.add_collection("notes", ["/notes"])
        assert col.chunk_size == 1200

    def test_collection_overrides_global_chunk_size(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir, chunk_size=800)
        config.add_collection("vault", ["/vault"])
        config.save()

        # Write a TOML with per-collection chunk_size
        toml_path = data_dir / "config.toml"
        content = toml_path.read_text()
        content = content.replace(
            "[collections.vault]",
            "[collections.vault]\nchunk_size = 1600",
        )
        toml_path.write_text(content)

        loaded = PyQMDConfig.load(data_dir)
        assert loaded.collections["vault"].chunk_size == 1600

    def test_collection_without_override_uses_global(self, tmp_path: pathlib.Path):
        data_dir = tmp_path / ".pyqmd"
        config = PyQMDConfig(data_dir=data_dir, chunk_size=800)
        config.add_collection("notes", ["/notes"])
        config.save()

        loaded = PyQMDConfig.load(data_dir)
        assert loaded.collections["notes"].chunk_size == 800


class TestConfigCRUD:
    def test_add_collection(self, tmp_path: pathlib.Path):
        config = PyQMDConfig(data_dir=tmp_path / ".pyqmd")
        col = config.add_collection("notes", ["/home/user/notes"], mask="**/*.md")
        assert "notes" in config.collections
        assert col.paths == ["/home/user/notes"]

    def test_add_duplicate_raises(self, tmp_path: pathlib.Path):
        config = PyQMDConfig(data_dir=tmp_path / ".pyqmd")
        config.add_collection("notes", ["/path"])
        with pytest.raises(ValueError, match="already exists"):
            config.add_collection("notes", ["/other"])

    def test_remove_collection(self, tmp_path: pathlib.Path):
        config = PyQMDConfig(data_dir=tmp_path / ".pyqmd")
        config.add_collection("notes", ["/path"])
        config.remove_collection("notes")
        assert "notes" not in config.collections

    def test_remove_nonexistent_raises(self, tmp_path: pathlib.Path):
        config = PyQMDConfig(data_dir=tmp_path / ".pyqmd")
        with pytest.raises(KeyError, match="not found"):
            config.remove_collection("nonexistent")


class TestLegacyMigration:
    def test_migrates_json_to_toml(self, tmp_path: pathlib.Path):
        import json
        data_dir = tmp_path / ".pyqmd"
        data_dir.mkdir(parents=True)
        json_path = data_dir / "config.json"
        json_path.write_text(json.dumps({
            "embed_model": "all-MiniLM-L6-v2",
            "chunk_size": 800,
            "chunk_overlap": 0.15,
            "storage_backend": "lancedb",
            "collections": {
                "notes": {
                    "paths": ["/home/user/notes"],
                    "mask": "**/*.md",
                    "config": {
                        "chunk_size": 800,
                        "chunk_overlap": 0.15,
                        "embed_model": "all-MiniLM-L6-v2",
                    },
                }
            },
        }))

        config = PyQMDConfig.load(data_dir)
        assert "notes" in config.collections
        assert config.collections["notes"].paths == ["/home/user/notes"]
        # TOML should be created
        assert (data_dir / "config.toml").exists()
        # JSON should be removed
        assert not json_path.exists()
