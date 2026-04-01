# pyqmd: Python Query Markup Documents — Design Spec

## Overview

A Python-native local search engine for markdown files. Indexes directories of
markdown files and makes them searchable via hybrid search (BM25 + vector +
reranking), all running locally. Inspired by QMD (Tobi Lutke) but going beyond
it with contextual retrieval, parent-child expansion, ColBERT, GraphRAG, and HyDE.

No Python port of QMD exists today. The individual pieces exist in the Python
ecosystem (chunkers, embedders, vector stores, rerankers) but nobody has built
the glue layer. pyqmd fills that gap.

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Package manager | uv | User standard |
| CLI framework | Typer | User standard |
| Logging | Rich | User standard |
| Output modes | Rich (human) / JSON (machine, via `--json` flag) | Dual-mode for human + LLM use |
| Primary storage | LanceDB | Embedded, native hybrid search, zero-config |
| Alt storage | SQLite + FTS5 + sqlite-vec | QMD-parity option, more control |
| Embeddings | sentence-transformers | Pluggable, local-first, huge model ecosystem |
| Default embed model | all-MiniLM-L6-v2 | Fast, good quality, 384 dims |
| Reranking | cross-encoder (sentence-transformers) | Simple, effective, upgradable to ColBERT |
| Markdown parsing | markdown-it-py or mistune | Fast, extensible |
| Document conversion | markitdown (Microsoft) | PDF/DOCX/PPTX → markdown |

## Implementation Tiers

### Tier 1: QMD Parity + Quick Wins

Core functionality matching QMD plus two high-impact additions.

- Markdown-aware chunking with break-point scoring
- BM25 full-text search
- Vector semantic search
- Reciprocal Rank Fusion (RRF) with position-aware blending
- Cross-encoder reranking
- Collections (named groups of directories)
- Incremental indexing (hash-based change detection)
- Contextual retrieval (LLM-generated context prepended to chunks before embedding)
- Parent-child retrieval (index small chunks, return parent sections for context)
- Typer CLI + first-class Python API

### Tier 2: Beyond QMD

- HyDE (Hypothetical Document Embeddings) at query time
- ColBERT via ragatouille (late interaction, per-token embeddings)
- Advanced query expansion (LLM-generated sub-queries)
- Pluggable embedding models (sentence-transformers, GGUF, API-based)

### Tier 3: Advanced

- GraphRAG (entity/relationship extraction, multi-hop queries)
- RAPTOR (recursive summarization tree for hierarchical content)
- MCP server (expose pyqmd to Claude Code and other AI tools)
- File watching (auto-reindex on changes)

## Core Data Model

```python
@dataclass
class Chunk:
    id: str                    # SHA-256 hash of content
    content: str               # The actual text
    context: str | None        # LLM-generated context prefix (contextual retrieval)
    source_file: str           # Path to source markdown file
    collection: str            # Collection name
    heading_path: list[str]    # ["H1 title", "H2 title", "H3 title"]
    parent_id: str | None      # ID of parent chunk (parent-child retrieval)
    start_line: int            # Line number in source file
    end_line: int              # Line number in source file
    metadata: dict             # Arbitrary metadata (tags, dates, frontmatter)

@dataclass
class SearchResult:
    chunk: Chunk
    score: float               # Combined score after fusion
    bm25_score: float | None   # Individual BM25 score
    vector_score: float | None # Individual vector similarity score
    rerank_score: float | None # Reranker score (if reranking enabled)

@dataclass
class Collection:
    name: str
    paths: list[str]           # Directories to index
    mask: str                  # Glob pattern (default: "**/*.md")
    config: CollectionConfig   # Per-collection settings
```

## Markdown-Aware Chunking

Custom chunker inspired by QMD's scoring algorithm for finding natural break points:

```python
BREAK_SCORES = {
    "h1":              100,    # # Heading 1
    "h2":               90,    # ## Heading 2
    "h3":               80,    # ### Heading 3
    "h4":               70,    # #### Heading 4
    "code_block_end":   85,    # End of fenced code block
    "hr":               75,    # Horizontal rule / thematic break
    "blank_line":       50,    # Empty line between paragraphs
    "list_end":         45,    # End of a list
    "blockquote_end":   40,    # End of a blockquote
}
```

**Rules:**
- Target chunk size: ~800 tokens (configurable)
- Overlap: 15% (configurable)
- Never split inside fenced code blocks
- Never split inside tables
- Preserve heading hierarchy as metadata on each chunk
- Parent-child: each chunk stores its parent heading's chunk ID
- YAML frontmatter is parsed and attached as metadata to all chunks from that file

## Indexing Pipeline

```
File detected (new or modified by hash)
    │
    ▼
Parse markdown → identify structure (headings, code blocks, tables, frontmatter)
    │
    ▼
Split into chunks using break-point scoring algorithm
    │
    ▼
Establish parent-child relationships between chunks
    │
    ▼
[Optional] Generate context prefix via LLM for each chunk (contextual retrieval)
    │
    ▼
Compute embeddings (sentence-transformers, configurable model)
    │
    ▼
Store in LanceDB: text (for BM25) + vector + metadata
    │
    ▼
Update file hash registry (SHA-256 of file content → indexed timestamp)
```

**Incremental indexing:** Track file hashes. On re-index, skip unchanged files.
When a file changes, remove all its chunks and re-index it. This is file-level
granularity (matching QMD), not chunk-level.

## Query Pipeline

```
User query
    │
    ▼
[Optional] Query expansion via LLM (keyword variants, domain terms)
    │
    ▼
[Optional] HyDE: generate hypothetical answer, embed that instead (Tier 2)
    │
    ▼
┌───────────┐     ┌──────────────┐
│ BM25      │     │ Vector       │
│ search    │     │ search       │
└─────┬─────┘     └──────┬───────┘
      │                  │
      ▼                  ▼
   Reciprocal Rank Fusion (k=60)
      │
      ▼
   [Optional] Cross-encoder reranking (or ColBERT in Tier 2)
      │
      ▼
   [Optional] Parent expansion (return parent chunks for context)
      │
      ▼
   Return top-K SearchResults
```

## CLI Commands

Every command supports `--json` for machine-readable output.

```bash
# Collection management
qmd add <name> <path> [--mask "**/*.md"]     # add a collection
qmd remove <name>                             # remove a collection
qmd list                                      # list all collections
qmd status [name]                             # show index stats

# Indexing
qmd index [name]                              # index/re-index a collection (or all)
qmd index --full                              # force full re-index (ignore hashes)
qmd index --contextual                        # enable contextual retrieval (LLM calls)

# Searching
qmd search "query text"                       # search all collections
qmd search "query" --collection <name>        # search specific collection
qmd search "query" --top-k 10                 # limit results
qmd search "query" --no-rerank                # skip reranking step
qmd search "query" --expand                   # enable parent chunk expansion
qmd search "query" --hyde                     # enable HyDE (Tier 2)

# Configuration
qmd config                                    # show current config
qmd config set embed_model <model>            # change embedding model
qmd config set chunk_size 800                 # change target chunk size
qmd config set storage lancedb|sqlite         # change storage backend
```

## Python API

```python
from pyqmd import PyQMD

# Initialize
qmd = PyQMD(data_dir="~/.pyqmd")

# Add and index a collection
qmd.add_collection("notes", paths=["~/notes"], mask="**/*.md")
qmd.index("notes")

# Search
results = qmd.search("how to handle NaN values", top_k=5)
for result in results:
    print(f"{result.score:.3f} | {result.chunk.source_file}")
    print(f"  {result.chunk.heading_path}")
    print(f"  {result.chunk.content[:200]}")

# Search with options
results = qmd.search(
    "indicator lookback period",
    collections=["notes", "docs"],
    top_k=10,
    rerank=True,
    expand_parents=True,
)

# Pluggable models (Tier 2)
qmd = PyQMD(embed_model="nomic-embed-text")
qmd = PyQMD(embed_model="gguf:model.gguf")
qmd = PyQMD(embed_model="openai:text-embedding-3-small")
```

## Storage Backends

### LanceDB (default)

Embedded, zero-config. Native BM25 + vector search. Data stored as Lance files
on disk. No server process needed.

### SQLite + FTS5 + sqlite-vec (QMD-parity option)

More control, matches QMD's architecture. FTS5 for BM25, sqlite-vec for vectors.
Single SQLite file per collection.

Both backends implement the same abstract interface so they're swappable via config.

## Project Structure

```
pyqmd/
├── pyproject.toml              # uv project config
├── README.md
├── src/
│   └── pyqmd/
│       ├── __init__.py         # Public API: PyQMD
│       ├── cli.py              # Typer CLI entry point
│       ├── core.py             # PyQMD main class
│       ├── models.py           # Data models (Chunk, SearchResult, Collection)
│       ├── config.py           # Configuration management
│       ├── chunking/
│       │   ├── __init__.py
│       │   ├── markdown.py     # Markdown-aware chunker
│       │   ├── scoring.py      # Break-point scoring algorithm
│       │   └── code.py         # AST-aware code chunking (tree-sitter)
│       ├── indexing/
│       │   ├── __init__.py
│       │   ├── pipeline.py     # Indexing pipeline orchestration
│       │   ├── contextual.py   # Contextual retrieval (LLM context generation)
│       │   └── hasher.py       # File hash tracking for incremental updates
│       ├── retrieval/
│       │   ├── __init__.py
│       │   ├── pipeline.py     # Query pipeline orchestration
│       │   ├── bm25.py         # BM25 search
│       │   ├── vector.py       # Vector search
│       │   ├── fusion.py       # RRF + position-aware blending
│       │   ├── rerank.py       # Cross-encoder / ColBERT reranking
│       │   ├── hyde.py         # HyDE query expansion (Tier 2)
│       │   └── parent.py       # Parent-child expansion
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract storage interface
│       │   ├── lancedb.py      # LanceDB backend
│       │   └── sqlite.py       # SQLite + FTS5 + sqlite-vec backend
│       ├── embeddings/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract embedding interface
│       │   ├── sentence_transformers.py
│       │   ├── gguf.py         # Local GGUF models (Tier 2)
│       │   └── api.py          # API-based embeddings (Tier 2)
│       ├── graph/              # Tier 3: GraphRAG
│       └── raptor/             # Tier 3: RAPTOR
├── tests/
│   ├── test_chunking.py
│   ├── test_indexing.py
│   ├── test_retrieval.py
│   ├── test_storage.py
│   └── fixtures/
│       └── sample_markdown/    # Test markdown files
└── docs/
    ├── VISION.md
    ├── IMPLEMENTATION.md
    ├── superpowers/
    │   └── specs/
    │       └── 2026-04-01-pyqmd-design.md  # This file
    └── research/
        ├── qmd-architecture.md
        ├── advanced-retrieval-techniques.md
        └── python-ecosystem.md
```

## References

- [QMD](https://github.com/tobi/qmd) — Original by Tobi Lutke. Node.js/Bun.
  Architecture reference for chunking, indexing, and query pipeline.
- [LanceDB](https://lancedb.github.io/lancedb/) — Embedded vector store with
  native hybrid search.
- [sentence-transformers](https://www.sbert.net/) — Embedding and cross-encoder models.
- [ragatouille](https://github.com/bclavie/RAGatouille) — ColBERT wrapper for Python.
- [nano-graphrag](https://github.com/gusye1234/nano-graphrag) — Lightweight GraphRAG.
- [Anthropic: Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
  — Technique for prepending context to chunks before embedding.
- [markitdown](https://github.com/microsoft/markitdown) — PDF/DOCX → markdown.
- [markdown-chunker](https://pypi.org/project/markdown-chunker/) — Existing markdown
  chunking library (reference, may use or build our own).
