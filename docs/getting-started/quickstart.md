# Quick Start

## 1. Add a Collection

Point pyqmd at a directory of markdown files:

```bash
qmd add my-notes ~/Documents/notes
```

This registers the collection but doesn't index it yet.

## 2. Index the Collection

```bash
qmd index my-notes
```

pyqmd will:

1. Scan all `**/*.md` files in the directory
2. Parse YAML frontmatter as metadata
3. Split files into chunks at natural break points
4. Compute embeddings for each chunk
5. Store everything in LanceDB

!!! tip "Incremental Indexing"
    Re-running `qmd index` only processes files that have changed since the last index (tracked by SHA-256 hash). Use `--full` to force a complete re-index.

## 3. Search

```bash
qmd search "how to handle missing data"
```

For machine-readable output:

```bash
qmd search "how to handle missing data" --json
```

## 4. Check Status

```bash
qmd status my-notes
```

Shows chunk count, paths, and configuration for the collection.

## Python API

```python
from pyqmd import PyQMD

qmd = PyQMD(data_dir="~/.pyqmd")
qmd.add_collection("notes", paths=["~/notes"])
qmd.index("notes")

results = qmd.search("Bollinger Bands", top_k=5)
for r in results:
    print(f"{r.score:.3f} {r.chunk.heading_path}")
    print(f"  {r.chunk.content[:200]}")
```
