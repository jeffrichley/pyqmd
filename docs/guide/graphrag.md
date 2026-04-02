# GraphRAG

GraphRAG builds a knowledge graph from your markdown files by extracting entities and the relationships between them. Once the graph is built you can ask multi-hop questions that require connecting information across many documents — the kind of questions that keyword search or vector search answer poorly.

## What it does

Standard search finds chunks that are similar to your query. GraphRAG works differently:

1. **Entity extraction** — An Ollama LLM reads every document and identifies named entities (concepts, techniques, people, systems) and the relationships between them.
2. **Community detection** — Related entities are clustered into communities and each community gets a summary.
3. **Graph query** — At query time, the graph is traversed to find entities and relationships relevant to your question, and a synthesized answer is assembled from that subgraph.

This makes GraphRAG well-suited for questions like "How does the CAPM model relate to portfolio optimization?" that span concepts scattered across multiple files.

## Prerequisites

Two Ollama models are required:

```bash
ollama pull qwen3:14b    # entity extraction (best model)
ollama pull llama3.2     # community summaries (cheap model)
```

Ollama must be running at `http://localhost:11434`.

## Building the graph

### From all collections

```bash
qmd graph build
```

Reads every file from every registered collection and builds the graph.

### From a specific collection

```bash
qmd graph build --collection my-notes
```

### From a directory

```bash
qmd graph build ~/notes/finance
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--collection`, `-c` | — | Build from a named collection |
| `--best-model` | `qwen3:14b` | Ollama model for entity extraction |
| `--cheap-model` | `llama3.2` | Ollama model for community summaries |
| `--data-dir` | `~/.pyqmd` | Data directory |

!!! note "Build time"
    Building the graph is slow — entity extraction calls the LLM for every document. A collection of 200 files may take 20–60 minutes depending on hardware. The graph is persisted to disk and only needs to be rebuilt when your content changes significantly.

## Querying the graph

```bash
qmd graph query "How does the Sharpe ratio relate to portfolio variance?"
```

### Query modes

GraphRAG supports two modes controlled by `--mode`:

**Local mode** (default) — traverses the graph starting from entities most relevant to the query. Best for specific, entity-centric questions.

```bash
qmd graph query "What is the CAPM formula?" --mode local
```

**Global mode** — synthesizes an answer from community summaries. Better for broad thematic questions that span many documents.

```bash
qmd graph query "What are the main themes in this collection?" --mode global
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--mode`, `-m` | `local` | Query mode: `local` or `global` |
| `--best-model` | `qwen3:14b` | Ollama model for query synthesis |
| `--cheap-model` | `llama3.2` | Ollama model for summaries |
| `--json` | — | Output as JSON |
| `--data-dir` | `~/.pyqmd` | Data directory |

### JSON output

```bash
qmd graph query "Explain momentum strategies" --json
```

```json
{
  "query": "Explain momentum strategies",
  "mode": "local",
  "answer": "Momentum strategies exploit the tendency of assets..."
}
```

## Checking graph status

```bash
qmd graph status
```

Displays entity count, relationship count, storage location, and which models are configured.

```bash
qmd graph status --json
```

## When to use GraphRAG vs regular search

| Scenario | Recommendation |
|----------|---------------|
| Find specific text passages | `qmd search` |
| Single-concept lookup | `qmd search` |
| Query uses technical jargon | `qmd search --hyde` |
| Multi-hop: "A relates to B via C" | `qmd graph query` |
| Thematic overview across many docs | `qmd graph query --mode global` |
| Relationship mapping | `qmd graph query` |

GraphRAG answers are synthesized prose, not ranked chunks. Use it when you want a composed answer, not a list of sources. For citation-quality retrieval, stick with `qmd search`.

## Python API

```python
from pyqmd.graph.engine import GraphEngine
import pathlib

engine = GraphEngine(
    data_dir=pathlib.Path("~/.pyqmd").expanduser(),
    best_model="qwen3:14b",
    cheap_model="llama3.2",
)

# Build from a directory
engine.build_from_directory(pathlib.Path("~/notes"))

# Query
answer = engine.query("How does CAPM relate to the efficient frontier?", mode="local")
print(answer)

# Status
info = engine.status()
print(f"Entities: {info['entities']}, Relationships: {info['relationships']}")
```
