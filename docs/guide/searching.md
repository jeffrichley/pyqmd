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

## HyDE Query Expansion

HyDE (Hypothetical Document Embeddings) improves search for technical or domain-specific queries by flipping the embedding direction. Instead of embedding your question and searching for similar text, pyqmd asks Ollama to write a short hypothetical answer to your question, embeds that answer, and searches for documents that are similar to it. Questions and answers use different vocabulary; this approach puts the query in the same embedding space as the answers.

### How to use it

```bash
qmd search "what is the Sharpe ratio formula" --hyde
```

### When it helps

HyDE is most effective when:

- Your query uses question phrasing ("what", "how", "why") but your documents use declarative statements.
- The domain has specific terminology that differs between questions and answers.
- Standard search returns results that seem off-topic.

For short keyword searches ("Sharpe ratio formula") standard search is usually sufficient.

### Cost

Each `--hyde` search makes one additional Ollama API call. On local hardware this typically adds 1–3 seconds to the search latency.

### Python API

```python
results = qmd.search("what is the Sharpe ratio formula", hyde=True)
```

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
