"""Configuration management for pyqmd."""

import json
import pathlib
from dataclasses import dataclass, field

from pyqmd.models import Collection, CollectionConfig


CONFIG_FILENAME = "config.json"


@dataclass
class PyQMDConfig:
    """Global pyqmd configuration, stored as JSON on disk."""

    data_dir: pathlib.Path
    embed_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 800
    chunk_overlap: float = 0.15
    storage_backend: str = "lancedb"
    collections: dict[str, Collection] = field(default_factory=dict)

    def save(self) -> None:
        """Save config to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.data_dir / CONFIG_FILENAME
        data = {
            "embed_model": self.embed_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "storage_backend": self.storage_backend,
            "collections": {
                name: {
                    "paths": col.paths,
                    "mask": col.mask,
                    "config": {
                        "chunk_size": col.config.chunk_size,
                        "chunk_overlap": col.config.chunk_overlap,
                        "embed_model": col.config.embed_model,
                    },
                }
                for name, col in self.collections.items()
            },
        }
        config_path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, data_dir: pathlib.Path) -> "PyQMDConfig":
        """Load config from disk, or return defaults if not found."""
        config_path = data_dir / CONFIG_FILENAME
        if not config_path.exists():
            return cls(data_dir=data_dir)
        data = json.loads(config_path.read_text())
        collections = {}
        for name, col_data in data.get("collections", {}).items():
            col_config_data = col_data.get("config", {})
            col_config = CollectionConfig(
                chunk_size=col_config_data.get("chunk_size", 800),
                chunk_overlap=col_config_data.get("chunk_overlap", 0.15),
                embed_model=col_config_data.get("embed_model", "all-MiniLM-L6-v2"),
            )
            collections[name] = Collection(
                name=name,
                paths=col_data["paths"],
                mask=col_data.get("mask", "**/*.md"),
                config=col_config,
            )
        config = cls(
            data_dir=data_dir,
            embed_model=data.get("embed_model", "all-MiniLM-L6-v2"),
            chunk_size=data.get("chunk_size", 800),
            chunk_overlap=data.get("chunk_overlap", 0.15),
            storage_backend=data.get("storage_backend", "lancedb"),
            collections=collections,
        )
        return config

    def add_collection(
        self, name: str, paths: list[str], mask: str = "**/*.md"
    ) -> Collection:
        """Add a new collection. Raises ValueError if name already exists."""
        if name in self.collections:
            raise ValueError(f"Collection '{name}' already exists")
        collection = Collection(
            name=name,
            paths=paths,
            mask=mask,
            config=CollectionConfig(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                embed_model=self.embed_model,
            ),
        )
        self.collections[name] = collection
        return collection

    def remove_collection(self, name: str) -> None:
        """Remove a collection. Raises KeyError if not found."""
        if name not in self.collections:
            raise KeyError(f"Collection '{name}' not found")
        del self.collections[name]
