import json
import pathlib
import pytest
from typer.testing import CliRunner
from pyqmd.cli import app

runner = CliRunner()


class TestCLI:
    def test_add_collection(self, tmp_path, fixtures_dir):
        result = runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", str(tmp_path / ".pyqmd")])
        assert result.exit_code == 0

    def test_list_collections(self, tmp_path, fixtures_dir):
        data_dir = str(tmp_path / ".pyqmd")
        runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", data_dir])
        result = runner.invoke(app, ["list", "--data-dir", data_dir, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "test" in data

    def test_remove_collection(self, tmp_path, fixtures_dir):
        data_dir = str(tmp_path / ".pyqmd")
        runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", data_dir])
        result = runner.invoke(app, ["remove", "test", "--data-dir", data_dir])
        assert result.exit_code == 0

    def test_index_collection(self, tmp_path, fixtures_dir):
        data_dir = str(tmp_path / ".pyqmd")
        runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", data_dir])
        result = runner.invoke(app, ["index", "test", "--data-dir", data_dir])
        assert result.exit_code == 0
        assert "indexed" in result.stdout.lower() or "chunk" in result.stdout.lower()

    def test_search(self, tmp_path, fixtures_dir):
        data_dir = str(tmp_path / ".pyqmd")
        runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", data_dir])
        runner.invoke(app, ["index", "test", "--data-dir", data_dir])
        result = runner.invoke(app, ["search", "Bollinger Bands", "--data-dir", data_dir, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) > 0

    def test_status(self, tmp_path, fixtures_dir):
        data_dir = str(tmp_path / ".pyqmd")
        runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", data_dir])
        runner.invoke(app, ["index", "test", "--data-dir", data_dir])
        result = runner.invoke(app, ["status", "test", "--data-dir", data_dir, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["chunk_count"] > 0

    def test_search_json_output_is_valid(self, tmp_path, fixtures_dir):
        data_dir = str(tmp_path / ".pyqmd")
        runner.invoke(app, ["add", "test", str(fixtures_dir), "--data-dir", data_dir])
        runner.invoke(app, ["index", "test", "--data-dir", data_dir])
        result = runner.invoke(app, ["search", "pandas", "--data-dir", data_dir, "--json"])
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        if data:
            assert "score" in data[0]
            assert "content" in data[0]
            assert "source_file" in data[0]
