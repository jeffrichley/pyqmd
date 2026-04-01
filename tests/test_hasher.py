import pathlib
import pytest
from pyqmd.indexing.hasher import FileHashRegistry


class TestFileHashRegistry:
    @pytest.fixture
    def registry(self, tmp_path: pathlib.Path) -> FileHashRegistry:
        return FileHashRegistry(tmp_path / "hashes.json")

    @pytest.fixture
    def sample_file(self, tmp_path: pathlib.Path) -> pathlib.Path:
        f = tmp_path / "test.md"
        f.write_text("# Hello\n\nWorld")
        return f

    def test_new_file_is_changed(self, registry, sample_file):
        assert registry.has_changed(sample_file) is True

    def test_recorded_file_is_unchanged(self, registry, sample_file):
        registry.record(sample_file)
        assert registry.has_changed(sample_file) is False

    def test_modified_file_is_changed(self, registry, sample_file):
        registry.record(sample_file)
        sample_file.write_text("# Changed content")
        assert registry.has_changed(sample_file) is True

    def test_save_and_load(self, tmp_path, sample_file):
        registry1 = FileHashRegistry(tmp_path / "hashes.json")
        registry1.record(sample_file)
        registry1.save()

        registry2 = FileHashRegistry(tmp_path / "hashes.json")
        assert registry2.has_changed(sample_file) is False

    def test_remove_file(self, registry, sample_file):
        registry.record(sample_file)
        assert registry.has_changed(sample_file) is False
        registry.remove(sample_file)
        assert registry.has_changed(sample_file) is True
