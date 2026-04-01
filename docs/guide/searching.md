# Searching

## Basic Search

```bash
qmd search "your query here"
```

## Search Options

```bash
# Search specific collection
qmd search "query" --collection my-notes

# Limit results
qmd search "query" --top-k 5

# JSON output (for scripts and LLMs)
qmd search "query" --json

# Skip reranking (faster, less precise)
qmd search "query" --no-rerank

# Include parent chunks for more context
qmd search "query" --expand
```

## How Search Works

pyqmd runs a multi-stage search pipeline:

1. **BM25 search** — full-text keyword matching
2. **Vector search** — semantic similarity via embeddings
3. **Reciprocal Rank Fusion** — merges both result sets (k=60)
4. **Cross-encoder reranking** — (optional) rescores top results for precision
5. **Parent expansion** — (optional) includes parent sections for context

## Python API

```python
from pyqmd import PyQMD

qmd = PyQMD()
results = qmd.search(
    "indicator lookback period",
    collections=["notes", "docs"],
    top_k=10,
    rerank=True,
    expand_parents=True,
)

for r in results:
    print(f"{r.score:.3f} | {r.chunk.source_file}")
    print(f"  {r.chunk.content[:200]}")
```
