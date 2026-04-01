"""File hash registry for incremental indexing."""

import hashlib
import json
import pathlib


class FileHashRegistry:
    """Tracks file content hashes to detect changes for incremental indexing."""

    def __init__(self, registry_path: pathlib.Path):
        self.registry_path = registry_path
        self._hashes: dict[str, str] = {}
        if registry_path.exists():
            self._hashes = json.loads(registry_path.read_text())

    def _compute_hash(self, path: pathlib.Path) -> str:
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def has_changed(self, path: pathlib.Path) -> bool:
        key = str(path.resolve())
        if key not in self._hashes:
            return True
        return self._hashes[key] != self._compute_hash(path)

    def record(self, path: pathlib.Path) -> None:
        key = str(path.resolve())
        self._hashes[key] = self._compute_hash(path)

    def remove(self, path: pathlib.Path) -> None:
        key = str(path.resolve())
        self._hashes.pop(key, None)

    def save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps(self._hashes, indent=2))
