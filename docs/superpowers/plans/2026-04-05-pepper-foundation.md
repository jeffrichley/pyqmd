# Pepper Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate pyqmd's config system to TOML + Pydantic, add a file-watching command, add path-prefix search filtering, and fix FTS index recreation.

**Architecture:** Config layer migrates from JSON dataclasses to TOML on disk with Pydantic models in memory. Watch command uses `watchdog` for filesystem events with optional polling fallback. Path-prefix is a post-filter on search results. FTS index moves from query-time to store-time.

**Tech Stack:** Python 3.11+, Pydantic v2, stdlib `tomllib`, `tomli-w`, `watchdog`, Typer, LanceDB

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Rewrite | `src/pyqmd/models.py` | Pydantic models: `CollectionConfig`, `WatchConfig`, `SearchConfig`, `Chunk`, `SearchResult`, `Collection` |
| Rewrite | `src/pyqmd/config.py` | `PyQMDConfig` Pydantic model, TOML read/write, resolution logic |
| Modify | `src/pyqmd/core.py` | Thread `path_prefix` through search, add `watch()` method |
| Modify | `src/pyqmd/cli.py` | Add `watch` command, add `--path-prefix` to search |
| Modify | `src/pyqmd/retrieval/pipeline.py` | Accept `path_prefix` and `overfetch_multiplier` params |
| Modify | `src/pyqmd/storage/lancedb_backend.py` | Move FTS index creation to `store()`, add `create_fts_index()` method |
| Modify | `src/pyqmd/indexing/pipeline.py` | Call `create_fts_index()` after store |
| Create | `src/pyqmd/watch.py` | `WatchService` class: watchdog + polling, debounce, ignore patterns |
| Rewrite | `tests/test_config.py` | Tests for TOML config, Pydantic models, resolution logic |
| Modify | `tests/test_storage.py` | Test FTS index created at store time |
| Modify | `tests/test_retrieval.py` | Test path-prefix filtering, overfetch multiplier |
| Create | `tests/test_watch.py` | Tests for WatchService debounce, ignore, polling |
| Modify | `tests/test_models.py` | Update for Pydantic models |
| Modify | `pyproject.toml` | Add `pydantic`, `tomli-w`, `watchdog` deps |

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:7-16`

- [ ] **Step 1: Add new dependencies to pyproject.toml**

```toml
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "lancedb>=0.6.0",
    "sentence-transformers>=2.2.0",
    "markdown-it-py>=3.0.0",
    "pyyaml>=6.0",
    "pyarrow>=14.0.0",
    "nano-graphrag>=0.0.8.2",
    "pydantic>=2.0",
    "tomli-w>=1.0.0",
    "watchdog>=3.0.0",
]
```

- [ ] **Step 2: Install dependencies**

Run: `uv sync`
Expected: All packages installed successfully.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pydantic, tomli-w, watchdog dependencies"
```

---

### Task 2: Migrate Models to Pydantic

**Files:**
- Modify: `src/pyqmd/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Read existing test_models.py to understand current test expectations**

Run: `cat tests/test_models.py`

- [ ] **Step 2: Rewrite models.py with Pydantic BaseModel classes**

Replace the entire contents of `src/pyqmd/models.py`:

```python
"""Core data models for pyqmd."""

from pydantic import BaseModel, Field


class WatchConfig(BaseModel):
    """Watch command configuration."""

    debounce: float = 2.0
    poll_interval: float = 0.0
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [".obsidian/", ".git/", "*.lock", "*.tmp", "~*"]
    )


class SearchConfig(BaseModel):
    """Search tuning configuration."""

    overfetch_multiplier: int = 2


class CollectionConfig(BaseModel):
    """Per-collection configuration. None values inherit from global config."""

    path: str = ""
    mask: str = "**/*.md"
    description: str = ""
    chunk_size: int | None = None
    chunk_overlap: float | None = None
    embed_model: str | None = None


class Collection(BaseModel):
    """A named group of directories to index.

    This is the runtime representation used throughout the codebase.
    CollectionConfig is the serialized TOML representation.
    """

    name: str
    paths: list[str]
    mask: str = "**/*.md"
    description: str = ""
    chunk_size: int = 800
    chunk_overlap: float = 0.15
    embed_model: str = "all-MiniLM-L6-v2"


class Chunk(BaseModel):
    """A chunk of text extracted from a markdown file."""

    model_config = {"frozen": False}

    id: str
    content: str
    context: str | None = None
    source_file: str
    collection: str
    heading_path: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    start_line: int = 0
    end_line: int = 0
    metadata: dict = Field(default_factory=dict)

    @property
    def embeddable_content(self) -> str:
        """Content used for embedding — includes context prefix if available."""
        if self.context:
            return f"{self.context}\n\n{self.content}"
        return self.content


class SearchResult(BaseModel):
    """A search result containing a chunk and its scores."""

    chunk: Chunk
    score: float
    bm25_score: float | None = None
    vector_score: float | None = None
    rerank_score: float | None = None
```

- [ ] **Step 3: Update test_models.py for Pydantic models**

Replace the contents of `tests/test_models.py` — update construction syntax (keyword args are required for Pydantic, no positional), and verify behavior is the same:

```python
from pyqmd.models import (
    Chunk,
    Collection,
    CollectionConfig,
    SearchConfig,
    SearchResult,
    WatchConfig,
)


class TestCollectionConfig:
    def test_defaults(self):
        cfg = CollectionConfig()
        assert cfg.mask == "**/*.md"
        assert cfg.chunk_size is None
        assert cfg.chunk_overlap is None
        assert cfg.embed_model is None

    def test_override(self):
        cfg = CollectionConfig(chunk_size=1600)
        assert cfg.chunk_size == 1600


class TestWatchConfig:
    def test_defaults(self):
        cfg = WatchConfig()
        assert cfg.debounce == 2.0
        assert cfg.poll_interval == 0.0
        assert ".git/" in cfg.ignore_patterns

    def test_override(self):
        cfg = WatchConfig(debounce=5.0, ignore_patterns=[".git/"])
        assert cfg.debounce == 5.0
        assert cfg.ignore_patterns == [".git/"]


class TestSearchConfig:
    def test_defaults(self):
        cfg = SearchConfig()
        assert cfg.overfetch_multiplier == 2


class TestCollection:
    def test_defaults(self):
        col = Collection(name="test", paths=["/tmp"])
        assert col.mask == "**/*.md"
        assert col.chunk_size == 800
        assert col.chunk_overlap == 0.15

    def test_override(self):
        col = Collection(name="test", paths=["/tmp"], chunk_size=1600)
        assert col.chunk_size == 1600


class TestChunk:
    def test_embeddable_content_without_context(self):
        chunk = Chunk(
            id="abc",
            content="Hello world",
            source_file="test.md",
            collection="test",
        )
        assert chunk.embeddable_content == "Hello world"

    def test_embeddable_content_with_context(self):
        chunk = Chunk(
            id="abc",
            content="Hello world",
            context="This is context",
            source_file="test.md",
            collection="test",
        )
        assert chunk.embeddable_content == "This is context\n\nHello world"

    def test_mutable_context(self):
        chunk = Chunk(
            id="abc",
            content="Hello",
            source_file="test.md",
            collection="test",
        )
        chunk.context = "new context"
        assert chunk.context == "new context"


class TestSearchResult:
    def test_basic(self):
        chunk = Chunk(
            id="abc",
            content="Hello",
            source_file="test.md",
            collection="test",
        )
        result = SearchResult(chunk=chunk, score=0.95)
        assert result.score == 0.95
        assert result.bm25_score is None
```

- [ ] **Step 4: Run tests to verify models work**

Run: `uv run pytest tests/test_models.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pyqmd/models.py tests/test_models.py
git commit -m "refactor: migrate models to Pydantic BaseModel"
```

---

### Task 3: Migrate Config to TOML + Pydantic

**Files:**
- Rewrite: `src/pyqmd/config.py`
- Rewrite: `tests/test_config.py`

This is the most impactful task. The config class changes from a dataclass with JSON to a Pydantic model with TOML. The public API (`load`, `save`, `add_collection`, `remove_collection`) stays the same so callers don't break.

- [ ] **Step 1: Write failing tests for the new config system**

Replace `tests/test_config.py`:

```python
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
        # Simulate a TOML with per-collection override
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
        # No per-collection override, so should inherit global
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: Failures due to missing `watch`, `search` attributes and JSON format.

- [ ] **Step 3: Rewrite config.py**

Replace `src/pyqmd/config.py`:

```python
"""Configuration management for pyqmd — TOML on disk, Pydantic in memory."""

import pathlib
import tomllib

import tomli_w
from pydantic import BaseModel, Field

from pyqmd.models import Collection, CollectionConfig, SearchConfig, WatchConfig

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
```

- [ ] **Step 4: Run config tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: All tests pass.

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -v --ignore=tests/test_cli.py`
Expected: All pass. Some tests in other modules may need minor fixes due to model changes (dataclass → Pydantic construction). Fix any that fail.

- [ ] **Step 6: Update core.py for new model structure**

The `Collection` model no longer has a nested `.config` object. Update `src/pyqmd/core.py` references:

Change `col.config.chunk_size` → `col.chunk_size`, `col.config.chunk_overlap` → `col.chunk_overlap`, `col.config.embed_model` → `col.embed_model` throughout `core.py`.

Specifically in `_get_indexing_pipeline` (line 49-51):
```python
chunker = MarkdownChunker(
    target_size=col.chunk_size,
    overlap=col.chunk_overlap,
)
```

And in `status` (line 249):
```python
"embed_model": col.embed_model,
```

- [ ] **Step 7: Update cli.py for new model structure**

In `show_config` command, update the config info dict if it references `storage_backend` or collection config. Also update `add_collection` — `Collection` no longer takes a `config` kwarg; it gets flat fields.

Check the graph commands that access `col.paths` and `col.mask` — these should still work since `Collection` still has those fields.

- [ ] **Step 8: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All pass.

- [ ] **Step 9: Commit**

```bash
git add src/pyqmd/config.py src/pyqmd/models.py src/pyqmd/core.py src/pyqmd/cli.py tests/test_config.py tests/test_models.py
git commit -m "refactor: migrate config to TOML + Pydantic with watch/search sections"
```

---

### Task 4: Fix FTS Index Recreation

**Files:**
- Modify: `src/pyqmd/storage/lancedb_backend.py:80-103`
- Modify: `src/pyqmd/indexing/pipeline.py:132-136`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write a test that verifies FTS index is created at store time**

Add to `tests/test_storage.py`:

```python
def test_fts_index_created_on_store(self, backend, sample_chunks):
    """FTS index should be created during store(), not on each search."""
    backend.store("test", sample_chunks)
    # search_text should work without needing to create the index itself
    results = backend.search_text("test", "pandas dataframes", top_k=3)
    assert isinstance(results, list)
```

- [ ] **Step 2: Run test to verify it passes (baseline — current code creates index in search_text)**

Run: `uv run pytest tests/test_storage.py::TestLanceDBBackend::test_fts_index_created_on_store -v`
Expected: PASS (the test passes because the current code creates the index during search, but we'll restructure where it happens).

- [ ] **Step 3: Move FTS index creation from search_text to store**

In `src/pyqmd/storage/lancedb_backend.py`, modify `store()` to create the FTS index after inserting rows:

```python
def store(self, collection: str, chunks_with_vectors: list[tuple[Chunk, list[float]]]) -> None:
    table = self._get_or_create_table(collection)
    rows = [self._chunk_to_row(c, v) for c, v in chunks_with_vectors]
    table.add(rows)
    try:
        table.create_fts_index("content", replace=True)
    except Exception:
        pass  # FTS index creation can fail in some environments
```

And remove the FTS index creation from `search_text()`:

```python
def search_text(self, collection: str, query: str, top_k: int = 10) -> list[tuple[str, float]]:
    table_name = self._table_name(collection)
    if table_name not in self._table_names():
        return []
    table = self.db.open_table(table_name)
    try:
        results = table.search(query, query_type="fts").limit(top_k).to_list()
        return [(r["chunk_id"], float(r.get("_score", 0.0))) for r in results]
    except Exception:
        return []
```

- [ ] **Step 4: Run storage tests**

Run: `uv run pytest tests/test_storage.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/pyqmd/storage/lancedb_backend.py tests/test_storage.py
git commit -m "fix: move FTS index creation from search_text to store"
```

---

### Task 5: Add Path-Prefix Filter to Search

**Files:**
- Modify: `src/pyqmd/retrieval/pipeline.py:25-33`
- Modify: `src/pyqmd/core.py:177-225`
- Modify: `src/pyqmd/cli.py:134-178`
- Modify: `tests/test_retrieval.py`

- [ ] **Step 1: Read current test_retrieval.py**

Run: `cat tests/test_retrieval.py`

Understand the existing test patterns, fixtures, and mocking approach.

- [ ] **Step 2: Write failing test for path-prefix filtering**

Add to `tests/test_retrieval.py`:

```python
def test_search_with_path_prefix(self):
    """Results should be filtered to only files matching the path prefix."""
    # Create chunks from different paths
    chunks = [
        Chunk(
            id="c1",
            content="project deadline friday",
            source_file="projects/niwc/status.md",
            collection="vault",
        ),
        Chunk(
            id="c2",
            content="weekly accomplishments",
            source_file="weekly/2026-w14.md",
            collection="vault",
        ),
        Chunk(
            id="c3",
            content="another project update",
            source_file="projects/niwc/update.md",
            collection="vault",
        ),
    ]

    # Mock storage to return all chunks
    # (adapt to existing test fixture pattern in test_retrieval.py)

    pipeline = RetrievalPipeline(
        storage=mock_storage,
        embedder=mock_embedder,
    )
    results = pipeline.search(
        "deadline",
        collections=["vault"],
        top_k=10,
        path_prefix="projects/niwc",
    )

    # Only chunks under projects/niwc should be returned
    source_files = [r.chunk.source_file for r in results]
    assert all(f.startswith("projects/niwc") for f in source_files)
```

Note: Adapt the mock setup to match whatever pattern `test_retrieval.py` already uses. The exact mock code depends on what you find in step 1.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_retrieval.py::test_search_with_path_prefix -v`
Expected: FAIL — `path_prefix` parameter doesn't exist yet.

- [ ] **Step 4: Add path_prefix parameter to RetrievalPipeline.search()**

In `src/pyqmd/retrieval/pipeline.py`, add `path_prefix: str | None = None` and `overfetch_multiplier: int = 2` to the `search()` method signature:

```python
def search(
    self,
    query: str,
    collections: list[str],
    top_k: int = 10,
    rerank: bool = True,
    expand_parent: bool = False,
    hyde: bool = False,
    path_prefix: str | None = None,
    overfetch_multiplier: int = 2,
) -> list[SearchResult]:
```

Replace the hardcoded `top_k * 2` with `top_k * overfetch_multiplier` on lines 59-60:

```python
bm25_results = self.storage.search_text(collection, query, top_k=top_k * overfetch_multiplier)
vector_results = self.storage.search_vector(collection, query_vector, top_k=top_k * overfetch_multiplier)
```

And on line 80:
```python
candidate_ids = [chunk_id for chunk_id, _ in fused[: top_k * overfetch_multiplier]]
```

Add path-prefix filtering after building results (before parent expansion, around line 108):

```python
# Filter by path prefix
if path_prefix:
    results = [
        r for r in results
        if r.chunk.source_file.startswith(path_prefix)
    ]
```

- [ ] **Step 5: Thread path_prefix through core.py**

In `src/pyqmd/core.py`, add `path_prefix: str | None = None` to `PyQMD.search()`:

```python
def search(
    self,
    query: str,
    collections: list[str] | None = None,
    top_k: int = 10,
    rerank: bool = False,
    expand_parent: bool = False,
    hyde: bool = False,
    path_prefix: str | None = None,
) -> list[SearchResult]:
```

And pass it through to the pipeline call along with overfetch_multiplier from config:

```python
return pipeline.search(
    query,
    collections=valid_collections,
    top_k=top_k,
    rerank=rerank,
    expand_parent=expand_parent,
    hyde=hyde,
    path_prefix=path_prefix,
    overfetch_multiplier=self.config.search.overfetch_multiplier,
)
```

- [ ] **Step 6: Add --path-prefix to CLI search command**

In `src/pyqmd/cli.py`, add the option to the `search` command:

```python
@app.command("search")
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    collection: Annotated[Optional[list[str]], typer.Option("--collection", "-c", help="Collection to search")] = None,
    top_k: Annotated[int, typer.Option("--top-k", "-k", help="Number of results")] = 10,
    path_prefix: Annotated[Optional[str], typer.Option("--path-prefix", help="Filter results to files under this path prefix")] = None,
    no_rerank: Annotated[bool, typer.Option("--no-rerank", help="Disable reranking")] = False,
    expand: Annotated[bool, typer.Option("--expand", help="Expand to parent chunks")] = False,
    use_hyde: Annotated[bool, typer.Option("--hyde", help="Use HyDE query expansion via Ollama")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
```

And pass it to the search call:

```python
results = qmd.search(
    query,
    collections=collection,
    top_k=top_k,
    rerank=not no_rerank and False,
    expand_parent=expand,
    hyde=use_hyde,
    path_prefix=path_prefix,
)
```

- [ ] **Step 7: Run tests**

Run: `uv run pytest tests/test_retrieval.py -v`
Expected: All pass including the new path-prefix test.

- [ ] **Step 8: Commit**

```bash
git add src/pyqmd/retrieval/pipeline.py src/pyqmd/core.py src/pyqmd/cli.py tests/test_retrieval.py
git commit -m "feat: add --path-prefix filter and configurable overfetch multiplier"
```

---

### Task 6: Add Watch Command

**Files:**
- Create: `src/pyqmd/watch.py`
- Modify: `src/pyqmd/cli.py`
- Modify: `src/pyqmd/core.py`
- Create: `tests/test_watch.py`

This is the largest task. The `WatchService` class encapsulates filesystem monitoring, debounce, polling, and ignore-pattern filtering.

- [ ] **Step 1: Write tests for WatchService**

Create `tests/test_watch.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_watch.py -v`
Expected: FAIL — `pyqmd.watch` module doesn't exist.

- [ ] **Step 3: Implement WatchService**

Create `src/pyqmd/watch.py`:

```python
"""File watcher for automatic re-indexing on changes."""

import fnmatch
import logging
import pathlib
import signal
import sys
import threading
import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class WatchService:
    """Watches a collection directory and auto-indexes on file changes.

    Supports dual-mode detection:
    - Filesystem events via watchdog (default, instant)
    - Polling via FileHashRegistry (optional, catches edge cases)
    """

    def __init__(
        self,
        collection_name: str,
        directory: pathlib.Path,
        mask: str,
        index_fn: callable,
        poll_fn: callable | None = None,
        debounce: float = 2.0,
        poll_interval: float = 0.0,
        ignore_patterns: list[str] | None = None,
    ):
        self.collection_name = collection_name
        self.directory = directory
        self.mask = mask
        self.index_fn = index_fn
        self.poll_fn = poll_fn
        self.debounce = debounce
        self.poll_interval = poll_interval
        self.ignore_patterns = ignore_patterns or [
            ".obsidian/", ".git/", "*.lock", "*.tmp", "~*"
        ]

        self._pending: set[pathlib.Path] = set()
        self._pending_deletes: set[pathlib.Path] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._running = False

    def _should_ignore(self, path: pathlib.Path) -> bool:
        """Check if a path matches any ignore pattern."""
        path_str = str(path)
        name = path.name
        for pattern in self.ignore_patterns:
            # Directory pattern (ends with /)
            if pattern.endswith("/"):
                dir_name = pattern.rstrip("/")
                if dir_name in pathlib.Path(path_str).parts:
                    return True
            # Glob pattern
            elif fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _add_pending(self, path: pathlib.Path) -> None:
        """Add a file to the pending set for batch re-indexing."""
        self._pending.add(path)

    def _add_pending_delete(self, path: pathlib.Path) -> None:
        """Add a file to the pending deletes set."""
        self._pending_deletes.add(path)

    def _schedule_flush(self) -> None:
        """Schedule a debounced flush of pending files."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        """Process all pending file changes."""
        with self._lock:
            pending = set(self._pending)
            pending_deletes = set(self._pending_deletes)
            self._pending.clear()
            self._pending_deletes.clear()

        if pending_deletes:
            for path in pending_deletes:
                logger.info("Deleted: %s", path)
            # Delete handling delegated to index_fn with force
            # The index_fn uses hasher, which won't find deleted files

        if pending:
            file_list = sorted(pending)
            logger.info(
                "Re-indexing %d file(s) in '%s': %s",
                len(file_list),
                self.collection_name,
                ", ".join(p.name for p in file_list),
            )
            try:
                count = self.index_fn(file_list)
                logger.info("Indexed %d chunks.", count)
            except Exception:
                logger.exception("Error during re-indexing")

    def _poll_loop(self) -> None:
        """Periodic polling loop using FileHashRegistry."""
        while self._running:
            time.sleep(self.poll_interval)
            if not self._running:
                break
            try:
                if self.poll_fn:
                    changed = self.poll_fn()
                    if changed:
                        logger.info(
                            "Poll detected %d changed file(s).", len(changed)
                        )
                        with self._lock:
                            self._pending.update(changed)
                        self._schedule_flush()
            except Exception:
                logger.exception("Error during poll")

    def run(self) -> None:
        """Start watching. Blocks until SIGINT/SIGTERM."""
        self._running = True

        # Set up signal handlers for graceful shutdown
        def shutdown(signum, frame):
            logger.info("Shutting down watcher...")
            self._running = False

        signal.signal(signal.SIGINT, shutdown)
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, shutdown)

        # Start watchdog observer
        handler = _ChangeHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.directory), recursive=True)
        observer.start()
        logger.info(
            "Watching '%s' (%s) — debounce=%.1fs",
            self.collection_name,
            self.directory,
            self.debounce,
        )

        # Start poll thread if enabled
        poll_thread = None
        if self.poll_interval > 0 and self.poll_fn:
            poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            poll_thread.start()
            logger.info("Polling enabled — interval=%.1fs", self.poll_interval)

        try:
            while self._running:
                time.sleep(0.5)
        finally:
            observer.stop()
            observer.join()
            if self._timer:
                self._timer.cancel()
            logger.info("Watcher stopped.")


class _ChangeHandler(FileSystemEventHandler):
    """Watchdog event handler that feeds into WatchService."""

    def __init__(self, service: WatchService):
        self.service = service

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = pathlib.Path(event.src_path)

        if self.service._should_ignore(path):
            return

        # Only care about files matching the collection mask
        if not fnmatch.fnmatch(path.name, self.service.mask.split("/")[-1]):
            return

        if event.event_type == "deleted":
            self.service._add_pending_delete(path)
        else:
            self.service._add_pending(path)

        self.service._schedule_flush()
```

- [ ] **Step 4: Run watch tests**

Run: `uv run pytest tests/test_watch.py -v`
Expected: All pass.

- [ ] **Step 5: Add watch() method to core.py**

Add to `src/pyqmd/core.py`:

```python
def watch(
    self,
    collection_name: str,
    debounce: float | None = None,
    poll_interval: float | None = None,
    ignore_patterns: list[str] | None = None,
) -> None:
    """Watch a collection's directory for changes and auto-index.

    Args:
        collection_name: Name of the collection to watch.
        debounce: Seconds to wait after last change (overrides config).
        poll_interval: Seconds between polls, 0 to disable (overrides config).
        ignore_patterns: Additional ignore patterns (merged with config).
    """
    from pyqmd.watch import WatchService

    col = self.config.collections.get(collection_name)
    if col is None:
        raise KeyError(f"Collection '{collection_name}' not found")

    watch_cfg = self.config.watch
    effective_debounce = debounce if debounce is not None else watch_cfg.debounce
    effective_poll = poll_interval if poll_interval is not None else watch_cfg.poll_interval
    effective_ignore = list(watch_cfg.ignore_patterns)
    if ignore_patterns:
        effective_ignore.extend(ignore_patterns)

    directory = pathlib.Path(col.paths[0])
    pipeline = self._get_indexing_pipeline(collection_name)

    def index_fn(file_list: list[pathlib.Path]) -> int:
        """Index a list of changed files."""
        total = 0
        for path in file_list:
            total += pipeline.index_file(path, collection=collection_name)
        return total

    def poll_fn() -> list[pathlib.Path]:
        """Check all files for changes via hash comparison."""
        files = sorted(directory.glob(col.mask))
        return [f for f in files if f.is_file() and pipeline.hasher.has_changed(f)]

    service = WatchService(
        collection_name=collection_name,
        directory=directory,
        mask=col.mask,
        index_fn=index_fn,
        poll_fn=poll_fn if effective_poll > 0 else None,
        debounce=effective_debounce,
        poll_interval=effective_poll,
        ignore_patterns=effective_ignore,
    )
    service.run()
```

- [ ] **Step 6: Add watch command to CLI**

Add to `src/pyqmd/cli.py`:

```python
@app.command("watch")
def watch_collection(
    name: Annotated[str, typer.Argument(help="Collection name to watch")],
    debounce: Annotated[Optional[float], typer.Option("--debounce", help="Debounce window in seconds")] = None,
    poll_interval: Annotated[Optional[float], typer.Option("--poll-interval", help="Poll interval in seconds (0=disabled)")] = None,
    ignore: Annotated[Optional[list[str]], typer.Option("--ignore", help="Additional ignore patterns")] = None,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Watch a collection for file changes and auto-index."""
    qmd = _get_qmd(data_dir)
    try:
        qmd.watch(
            name,
            debounce=debounce,
            poll_interval=poll_interval,
            ignore_patterns=ignore,
        )
    except KeyError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add src/pyqmd/watch.py src/pyqmd/core.py src/pyqmd/cli.py tests/test_watch.py
git commit -m "feat: add qmd watch command with watchdog + polling support"
```

---

### Task 7: Update BACKLOG.md

**Files:**
- Modify: `BACKLOG.md`

- [ ] **Step 1: Add completed items and any new tech debt discovered**

Update `BACKLOG.md` to reflect that the Pepper foundation requirements are implemented. Keep the diskcache entry. Add any new items discovered during implementation.

- [ ] **Step 2: Commit**

```bash
git add BACKLOG.md
git commit -m "docs: update backlog with Pepper foundation completion"
```
