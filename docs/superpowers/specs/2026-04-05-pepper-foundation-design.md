# Pepper Foundation Requirements — Design Spec

## Overview

Four requirements to make pyqmd ready for Pepper integration: config system migration, a watch command, path-prefix search filtering, and an FTS index fix. The config migration is the foundation — watch and search tuning depend on it.

## Requirement 1: Config Migration (TOML + Pydantic)

### On-Disk Format

Migrate from `config.json` to `config.toml` at `{data_dir}/config.toml`.

```toml
# Global defaults
chunk_size = 800
chunk_overlap = 0.15
embed_model = "all-MiniLM-L6-v2"

[search]
overfetch_multiplier = 2  # fetches top_k * this for RRF fusion

[watch]
debounce = 2.0            # seconds to wait after last change before re-indexing
poll_interval = 0         # 0 = disabled, >0 = poll every N seconds
ignore_patterns = [".obsidian/", ".git/", "*.lock", "*.tmp", "~*"]

[collections.vault]
path = "Memory/"
mask = "**/*.md"
description = "Pepper's memory vault"
chunk_size = 1600  # overrides global

[collections.notes]
path = "Notes/"
mask = "**/*.md"
description = "General notes"
# chunk_size not set — inherits global 800
```

### In-Memory Models

Pydantic `BaseModel` classes replace the existing dataclasses:

- **`WatchConfig`**: `debounce: float = 2.0`, `poll_interval: float = 0`, `ignore_patterns: list[str] = [defaults]`
- **`SearchConfig`**: `overfetch_multiplier: int = 2`
- **`CollectionConfig`**: `path: str`, `mask: str = "**/*.md"`, `description: str = ""`, `chunk_size: int | None = None`, `chunk_overlap: float | None = None`, `embed_model: str | None = None`
- **`PyQMDConfig`**: `chunk_size: int = 800`, `chunk_overlap: float = 0.15`, `embed_model: str = "all-MiniLM-L6-v2"`, `search: SearchConfig`, `watch: WatchConfig`, `collections: dict[str, CollectionConfig]`

### Resolution Logic

Per-collection > global TOML > hardcoded default (via Pydantic defaults).

Example: `collection.chunk_size or config.chunk_size` — if a collection doesn't set `chunk_size`, it inherits the global value.

### Files Modified

- `src/pyqmd/config.py` — Replace dataclasses with Pydantic models, replace JSON read/write with TOML
- `src/pyqmd/core.py` — Update `PyQMD` to use new config models
- `pyproject.toml` — Add `pydantic` dependency. Use stdlib `tomllib` for TOML parsing (Python >=3.11 required). Add `tomli-w` for TOML writing.

### Internal State

Internal state (hash registries, etc.) stays as-is — JSON files, Pydantic models in memory. The migration only affects user-facing configuration.

---

## Requirement 2: Watch Command

### CLI Signature

```
qmd watch <collection> [--debounce FLOAT] [--poll-interval FLOAT] [--ignore PATTERN...]
```

CLI flags override TOML values for that invocation only (not persisted).

### Architecture

New module: `src/pyqmd/watch.py` containing `WatchService`.

**Dependencies**: `watchdog` library (added to `pyproject.toml`). Uses `ReadDirectoryChangesW` on Windows natively.

### Behavior

**Dual-mode detection:**
- **Filesystem events (default)**: `watchdog` observer watches the collection directory recursively. On file create/modify/delete events, affected paths are added to a pending set.
- **Polling fallback**: When `poll_interval > 0`, a periodic scan runs using `FileHashRegistry.has_changed()` on all files matching the collection's mask. Catches changes that filesystem watchers miss (network drives, mounted volumes, edge cases).
- Both modes can run simultaneously.

**Debounce**: After the debounce window expires with no new events, trigger re-index on the pending set.

**Ignore patterns**: Applied at the event handler level — events matching patterns are filtered out before hitting the pending set. Patterns from TOML config merged with any CLI `--ignore` additions.

**Re-indexing**: Leverages existing `IndexingPipeline` and `FileHashRegistry.has_changed()`. Even if watchdog fires spuriously, only truly changed files get re-indexed. Delete events remove chunks for that file from the index.

**Output**: Stdout for activity (which files re-indexed). Stderr for errors.

**Shutdown**: Graceful on SIGINT/SIGTERM via signal handlers. Runs as a long-lived process.

### Files Modified

- `src/pyqmd/watch.py` — New module: `WatchService` class
- `src/pyqmd/cli.py` — Add `@app.command("watch")`
- `src/pyqmd/core.py` — Add `watch()` method delegating to `WatchService`
- `pyproject.toml` — Add `watchdog` dependency

---

## Requirement 3: Path-Prefix Filter on Search

### CLI Signature

```
qmd search <collection> <query> [--path-prefix PATH]
```

### Implementation

Post-filter on search results. The hybrid search (BM25 + vector) runs normally, then results are filtered where `chunk.source_file` starts with the resolved prefix relative to the collection root.

If the prefix narrows results, fewer results are returned. No over-fetch adjustment — users can bump `--top-k` if needed.

### Search Tuning

`overfetch_multiplier` is configurable in TOML under `[search]`. Controls how many candidates are fetched for RRF fusion (`top_k * overfetch_multiplier`). Currently hardcoded to 2.

### Files Modified

- `src/pyqmd/retrieval/pipeline.py` — Add `path_prefix: str | None` parameter to `search()`, filter results post-fusion
- `src/pyqmd/cli.py` — Add `--path-prefix` option to search command
- `src/pyqmd/core.py` — Thread `path_prefix` parameter through `PyQMD.search()`

---

## Requirement 4: FTS Index Fix

### Problem

`search_text()` in `lancedb_backend.py` calls `create_fts_index("content", replace=True)` on every search query. This recreates the full-text search index from scratch each time.

### Fix

Move `create_fts_index()` to the indexing pipeline. Call it once after `store()` completes. Remove it from `search_text()`.

### Files Modified

- `src/pyqmd/storage/lancedb_backend.py` — Remove `create_fts_index` from `search_text()`, add it to `store()` or `_get_or_create_table()`
- `src/pyqmd/indexing/pipeline.py` — Ensure FTS index is created/updated after bulk insert

---

## Implementation Order

1. **Config migration** (TOML + Pydantic) — foundation for everything else
2. **FTS index fix** — independent, small, immediate perf win
3. **Path-prefix filter** — independent, small
4. **Watch command** — depends on config migration for settings

Requirements 2 and 3 can be done in parallel after the config migration.

---

## Chunk Size

Default stays at 800 characters. Configurable globally in TOML (`chunk_size = 1600`) and per-collection (`[collections.vault] chunk_size = 1600`). No hardcoded change needed — Pepper sets its preferred size in the TOML config.

---

## Dependencies Added

- `watchdog` — filesystem event monitoring (cross-platform, Windows-native)
- `pydantic>=2.0` — config model validation (already a transitive dep via nano-graphrag, but should be declared explicitly)
- `tomli-w` — TOML writing (stdlib `tomllib` is read-only)

## Dependencies Potentially Removed

- None — existing deps remain unchanged
