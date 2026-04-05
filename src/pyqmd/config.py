"""Configuration management for pyqmd — TOML on disk, Pydantic in memory."""

import pathlib
import tomllib

import tomli_w
from pydantic import BaseModel, Field

from pyqmd.models import Collection, SearchConfig, WatchConfig

CONFIG_FILENAME = "config.toml"


class PyQMDConfig(BaseModel):
    """Global pyqmd configuration."""

    model_config = {"arbitrary_types_allowed": True}

    data_dir: pathlib.Path
    embed_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 800
    chunk_overlap: float = 0.15
    storage_backend: str = "lancedb"
    watch: WatchConfig = Field(default_factory=WatchConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    collections: dict[str, Collection] = Field(default_factory=dict)

    def save(self) -> None:
        """Save config to TOML on disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.data_dir / CONFIG_FILENAME

        data: dict = {
            "embed_model": self.embed_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "storage_backend": self.storage_backend,
            "watch": self.watch.model_dump(),
            "search": self.search.model_dump(),
            "collections": {},
        }

        for name, col in self.collections.items():
            col_data: dict = {
                "paths": col.paths,
                "mask": col.mask,
                "description": col.description,
            }
            # Only write per-collection overrides if they differ from global
            if col.chunk_size != self.chunk_size:
                col_data["chunk_size"] = col.chunk_size
            if col.chunk_overlap != self.chunk_overlap:
                col_data["chunk_overlap"] = col.chunk_overlap
            if col.embed_model != self.embed_model:
                col_data["embed_model"] = col.embed_model
            data["collections"][name] = col_data

        config_path.write_text(tomli_w.dumps(data))

    @classmethod
    def load(cls, data_dir: pathlib.Path) -> "PyQMDConfig":
        """Load config from TOML, or return defaults if not found."""
        config_path = data_dir / CONFIG_FILENAME
        if not config_path.exists():
            # Try legacy JSON config
            json_path = data_dir / "config.json"
            if json_path.exists():
                return cls._load_legacy_json(data_dir, json_path)
            return cls(data_dir=data_dir)

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        global_chunk_size = data.get("chunk_size", 800)
        global_chunk_overlap = data.get("chunk_overlap", 0.15)
        global_embed_model = data.get("embed_model", "all-MiniLM-L6-v2")

        collections = {}
        for name, col_data in data.get("collections", {}).items():
            collections[name] = Collection(
                name=name,
                paths=col_data.get("paths", []),
                mask=col_data.get("mask", "**/*.md"),
                description=col_data.get("description", ""),
                chunk_size=col_data.get("chunk_size", global_chunk_size),
                chunk_overlap=col_data.get("chunk_overlap", global_chunk_overlap),
                embed_model=col_data.get("embed_model", global_embed_model),
            )

        watch_data = data.get("watch", {})
        search_data = data.get("search", {})

        return cls(
            data_dir=data_dir,
            embed_model=global_embed_model,
            chunk_size=global_chunk_size,
            chunk_overlap=global_chunk_overlap,
            storage_backend=data.get("storage_backend", "lancedb"),
            watch=WatchConfig(**watch_data),
            search=SearchConfig(**search_data),
            collections=collections,
        )

    @classmethod
    def _load_legacy_json(
        cls, data_dir: pathlib.Path, json_path: pathlib.Path
    ) -> "PyQMDConfig":
        """Load from legacy config.json and migrate to TOML."""
        import json

        data = json.loads(json_path.read_text())
        collections = {}
        for name, col_data in data.get("collections", {}).items():
            col_config = col_data.get("config", {})
            collections[name] = Collection(
                name=name,
                paths=col_data.get("paths", []),
                mask=col_data.get("mask", "**/*.md"),
                chunk_size=col_config.get("chunk_size", 800),
                chunk_overlap=col_config.get("chunk_overlap", 0.15),
                embed_model=col_config.get("embed_model", "all-MiniLM-L6-v2"),
            )

        config = cls(
            data_dir=data_dir,
            embed_model=data.get("embed_model", "all-MiniLM-L6-v2"),
            chunk_size=data.get("chunk_size", 800),
            chunk_overlap=data.get("chunk_overlap", 0.15),
            storage_backend=data.get("storage_backend", "lancedb"),
            collections=collections,
        )
        # Migrate: save as TOML
        config.save()
        json_path.unlink()
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
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            embed_model=self.embed_model,
        )
        self.collections[name] = collection
        return collection

    def remove_collection(self, name: str) -> None:
        """Remove a collection. Raises KeyError if not found."""
        if name not in self.collections:
            raise KeyError(f"Collection '{name}' not found")
        del self.collections[name]
