---
hide:
  - navigation
---

<div class="iris-hero" markdown>

# pyqmd

**Python-native local search engine for markdown files.**

Hybrid BM25 + vector search with reranking, contextual retrieval, and parent-child expansion. Inspired by QMD, built to go beyond it.

[Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/jeffrichley/pyqmd){ .md-button }

</div>

<div class="iris-cards" markdown>

<div class="iris-card" markdown>

### Hybrid Search

Parallel BM25 full-text and semantic vector search, merged with Reciprocal Rank Fusion for the best of both worlds.

</div>

<div class="iris-card" markdown>

### Markdown-Native

Your markdown files are the source of truth. Human-readable, version-controlled, git-diffable. pyqmd indexes without modifying.

</div>

<div class="iris-card" markdown>

### Smart Chunking

Break-point scoring algorithm finds natural split points in your documents. Never splits code blocks or tables.

</div>

<div class="iris-card" markdown>

### Cross-Encoder Reranking

Optional reranking pass using a cross-encoder model to boost the most relevant results to the top.

</div>

<div class="iris-card" markdown>

### Parent-Child Retrieval

Index small chunks for precision, return parent sections for context. Get the best of both granularities.

</div>

<div class="iris-card" markdown>

### Dual-Mode CLI

Rich terminal output for humans, `--json` for LLMs and scripts. Every command works both ways.

</div>

</div>

## Quick Example

```python
from pyqmd import PyQMD

qmd = PyQMD(data_dir="~/.pyqmd")

# Add and index a collection
qmd.add_collection("notes", paths=["~/notes"])
qmd.index("notes")

# Search
results = qmd.search("how to handle NaN values", top_k=5)
for result in results:
    print(f"{result.score:.3f} | {result.chunk.source_file}")
```

```bash
# Or use the CLI
qmd add notes ~/notes
qmd index notes
qmd search "how to handle NaN values" --json
```
