# Configuration

## View Current Config

```bash
qmd config
```

## Configuration File

pyqmd stores configuration at `~/.pyqmd/config.toml`. If you have an older `config.json`, it is auto-migrated on first run.

### Full example

```toml
# Global defaults
embed_model = "all-MiniLM-L6-v2"
chunk_size = 800
chunk_overlap = 0.15
storage_backend = "lancedb"

[search]
overfetch_multiplier = 3.0   # candidate pool = top_k * multiplier for RRF

[watch]
debounce = 1.0               # seconds to wait after last change before re-indexing
poll_interval = 0.0           # polling interval in seconds; 0 = disabled (use OS events)
ignore_patterns = [           # glob patterns to ignore during watch
    "*.tmp",
    ".git/**",
]

[collections.my-notes]       # per-collection overrides
chunk_size = 1200
chunk_overlap = 0.20
embed_model = "all-MiniLM-L6-v2"
```

## Global Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `embed_model` | `all-MiniLM-L6-v2` | Sentence transformer model for embeddings |
| `chunk_size` | `800` | Target chunk size in characters |
| `chunk_overlap` | `0.15` | Overlap between adjacent chunks (0-1) |
| `storage_backend` | `lancedb` | Storage backend (`lancedb`) |

## `[search]` Section

| Setting | Default | Description |
|---------|---------|-------------|
| `overfetch_multiplier` | `3.0` | Multiplier applied to `top_k` to size the candidate pool for reciprocal rank fusion |

## `[watch]` Section

| Setting | Default | Description |
|---------|---------|-------------|
| `debounce` | `1.0` | Seconds to wait after the last filesystem change before re-indexing |
| `poll_interval` | `0.0` | Polling fallback interval in seconds; `0` disables polling (uses OS events via watchdog) |
| `ignore_patterns` | `["*.tmp", ".git/**"]` | Glob patterns of paths to ignore during watch |

## `[collections.name]` Section

Per-collection overrides. Any global setting (`chunk_size`, `chunk_overlap`, `embed_model`) can be set per collection:

```toml
[collections.research-papers]
chunk_size = 1500
chunk_overlap = 0.10
```

### Resolution order

Per-collection value > global value > built-in default.

## Data Directory

By default, pyqmd stores all data in `~/.pyqmd/`. Override with:

```bash
qmd search "query" --data-dir /custom/path
```

Or in Python:

```python
qmd = PyQMD(data_dir="/custom/path")
```
