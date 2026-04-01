# Configuration

## View Current Config

```bash
qmd config
```

## Configuration File

pyqmd stores configuration at `~/.pyqmd/config.json`.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `embed_model` | `all-MiniLM-L6-v2` | Sentence transformer model for embeddings |
| `chunk_size` | `800` | Target chunk size in characters |
| `chunk_overlap` | `0.15` | Overlap between adjacent chunks (0-1) |
| `storage_backend` | `lancedb` | Storage backend (`lancedb`) |

## Data Directory

By default, pyqmd stores all data in `~/.pyqmd/`. Override with:

```bash
qmd search "query" --data-dir /custom/path
```

Or in Python:

```python
qmd = PyQMD(data_dir="/custom/path")
```
