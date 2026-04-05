import pathlib
import time

import pytest

from pyqmd.watch import WatchService


class TestIgnorePatterns:
    def test_matches_git_directory(self):
        svc = WatchService.__new__(WatchService)
        svc.ignore_patterns = [".git/", "*.tmp"]
        assert svc._should_ignore(pathlib.Path("/repo/.git/config"))

    def test_matches_glob_pattern(self):
        svc = WatchService.__new__(WatchService)
        svc.ignore_patterns = [".git/", "*.tmp"]
        assert svc._should_ignore(pathlib.Path("/repo/file.tmp"))

    def test_no_match(self):
        svc = WatchService.__new__(WatchService)
        svc.ignore_patterns = [".git/", "*.tmp"]
        assert not svc._should_ignore(pathlib.Path("/repo/notes.md"))

    def test_matches_obsidian(self):
        svc = WatchService.__new__(WatchService)
        svc.ignore_patterns = [".obsidian/"]
        assert svc._should_ignore(pathlib.Path("/vault/.obsidian/workspace.json"))

    def test_matches_tilde_prefix(self):
        svc = WatchService.__new__(WatchService)
        svc.ignore_patterns = ["~*"]
        assert svc._should_ignore(pathlib.Path("/repo/~tempfile.md"))


class TestDebounce:
    def test_pending_files_collected(self):
        """Files added within debounce window should be batched."""
        svc = WatchService.__new__(WatchService)
        svc._pending = set()
        svc._add_pending(pathlib.Path("/repo/a.md"))
        svc._add_pending(pathlib.Path("/repo/b.md"))
        assert len(svc._pending) == 2

    def test_duplicate_paths_deduplicated(self):
        svc = WatchService.__new__(WatchService)
        svc._pending = set()
        svc._add_pending(pathlib.Path("/repo/a.md"))
        svc._add_pending(pathlib.Path("/repo/a.md"))
        assert len(svc._pending) == 1
