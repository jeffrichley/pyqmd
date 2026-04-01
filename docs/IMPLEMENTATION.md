# py-qmd Implementation Plan

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Package manager | uv | User preference, fast, modern |
| CLI framework | Typer | User preference, clean API |
| Logging | Rich | User preference, beautiful output |
| Primary storage | LanceDB | Embedded, native hybrid search, zero-config |
| Alt storage | SQLite + FTS5 + sqlite-vec | QMD-parity option, more control |
| Embeddings | sentence-transformers | Pluggable, local-first, huge model ecosystem |
| Default embed model | all-MiniLM-L6-v2 | Fast, good quality, 384 dims |
| Reranking | cross-encoder (sentence-transformers) | Simple, effective, upgradable to ColBERT |
| Markdown parsing | markdown-it-py or mistune | Fast, extensible |
| Document conversion | markitdown (Microsoft) | PDF/DOCX/PPTX → markdown |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     py-qmd CLI (Typer)               │
│  qmd add | qmd search | qmd index | qmd status      │
├──────────────────────────────────────────────────────┤
│                   py-qmd Python API                   │
│  PyQMD.add_collection() | .search() | .index()       │
├──────────────┬───────────────────┬───────────────────┤
│   Indexing    │     Querying      │   Management      │
│   Pipeline    │     Pipeline      │                   │
├──────────────┼───────────────────┼───────────────────┤
│              Storage Layer (pluggable)                │
│         LanceDB  |  SQLite+FTS5+sqlite-vec           │
├──────────────────────────────────────────────────────┤
│           Embedding Layer (pluggable)                 │
│   sentence-transformers | GGUF | API-based            │
├──────────────────────────────────────────────────────┤
│            Reranking Layer (pluggable)                │
│   cross-encoder | ColBERT | local LLM | none          │
└──────────────────────────────────────────────────────┘
```

## Tier 1: QMD Parity + Quick Wins

**Goal:** A working py-qmd that matches QMD's core functionality plus two easy
high-impact additions (contextual retrieval, parent-child retrieval).

### 1.1 Core Data Model

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
    metadata: dict             # Arbitrary metadata (tags, dates, etc.)

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

### 1.2 Markdown-Aware Chunking

Custom chunker inspired by QMD's scoring algorithm:

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

### 1.3 Indexing Pipeline

```
File detected (new or modified)
    │
    ▼
Parse markdown → identify structure (headings, code blocks, etc.)
    │
    ▼
Split into chunks using break-point scoring
    │
    ▼
[Optional] Generate context prefix via LLM (contextual retrieval)
    │
    ▼
Compute embeddings (sentence-transformers)
    │
    ▼
Store in LanceDB (text + vector + metadata)
    │
    ▼
Update file hash registry (for incremental updates)
```

**Incremental indexing:** Track file hashes (SHA-256 of file content). On re-index,
skip unchanged files. When a file changes, remove all its chunks and re-index it.

### 1.4 Query Pipeline

```
User query
    │
    ▼
[Optional] Query expansion (keyword variants, domain terms)
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
   [Optional] Cross-encoder reranking
      │
      ▼
   [Optional] Parent expansion (return parent chunks for context)
      │
      ▼
   Return top-K SearchResults
```

### 1.5 CLI Commands

```bash
# Collection management
qmd add <name> <path> [--mask "**/*.md"]
qmd remove <name>
qmd list                              # List all collections
qmd status [name]                     # Show index stats

# Indexing
qmd index [name]                      # Index/re-index a collection (or all)
qmd index --full                      # Force full re-index (ignore hashes)

# Searching
qmd search "query text"               # Search all collections
qmd search "query" --collection <name> # Search specific collection
qmd search "query" --top-k 10         # Limit results
qmd search "query" --no-rerank        # Skip reranking step
qmd search "query" --expand           # Enable parent chunk expansion
qmd search "query" --hyde             # Enable HyDE (Tier 2)

# Configuration
qmd config                            # Show current config
qmd config set embed_model <model>    # Change embedding model
qmd config set chunk_size 800         # Change target chunk size
```

### 1.6 Python API

```python
from py_qmd import PyQMD

# Initialize
qmd = PyQMD(data_dir="~/.py-qmd")

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
```

## Tier 2: Beyond QMD

### 2.1 HyDE (Hypothetical Document Embeddings)

At query time, generate a hypothetical answer via LLM, embed it, and use that
embedding for vector search. Bridges the vocabulary gap between questions and answers.

```python
results = qmd.search("why does my indicator return NaN", hyde=True)
# Internally:
# 1. LLM generates: "The indicator returns NaN because the lookback period
#    exceeds the available data..."
# 2. That hypothetical answer is embedded
# 3. Vector search uses the hypothetical embedding (closer to real answers)
```

### 2.2 ColBERT Integration

Replace or augment single-vector search with ColBERT's per-token late interaction.

```python
qmd.config.set("retriever", "colbert")  # or "hybrid+colbert"
# Uses ragatouille under the hood
```

### 2.3 Advanced Query Expansion

Use an LLM to generate multiple sub-queries from a single user query:

```python
# User: "my bollinger bands look wrong"
# Expanded:
#   - "bollinger bands incorrect values"
#   - "technical indicator calculation error"
#   - "rolling standard deviation pandas"
```

### 2.4 Pluggable Embedding Models

```python
qmd = PyQMD(embed_model="nomic-embed-text")     # sentence-transformers
qmd = PyQMD(embed_model="gguf:model.gguf")      # Local GGUF via llama-cpp
qmd = PyQMD(embed_model="openai:text-embedding-3-small")  # API-based
```

## Tier 3: Advanced Features

### 3.1 GraphRAG

Build a knowledge graph from indexed content. Extract entities (functions, concepts,
error types) and relationships. Enable multi-hop queries.

```python
qmd.build_graph("course-qa")  # Extract entities + relationships
results = qmd.graph_search("relationship between Sharpe ratio and volatility")
```

### 3.2 RAPTOR

Recursive summarization tree for hierarchical content. Best for static collections
(lecture notes, course docs) that don't change often.

```python
qmd.build_raptor_tree("lectures")  # Cluster → summarize → recurse
results = qmd.search("market microstructure", strategy="raptor")
```

### 3.3 MCP Server

Expose py-qmd as an MCP server for Claude Code and other AI tools.

```bash
qmd serve --mcp                # Start MCP server
qmd serve --mcp --port 8080    # Custom port
```

### 3.4 File Watching

Watch collections for changes and auto-reindex.

```bash
qmd watch                      # Watch all collections
qmd watch --collection notes   # Watch specific collection
```

## Project Structure

```
py-qmd/
├── pyproject.toml              # uv project config
├── README.md
├── src/
│   └── py_qmd/
│       ├── __init__.py         # Public API
│       ├── cli.py              # Typer CLI
│       ├── core.py             # PyQMD main class
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
│       │   ├── hyde.py         # HyDE query expansion
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
│       │   ├── gguf.py         # Local GGUF models
│       │   └── api.py          # API-based embeddings (OpenAI, etc.)
│       ├── graph/              # Tier 3: GraphRAG
│       ├── raptor/             # Tier 3: RAPTOR
│       ├── models.py           # Data models (Chunk, SearchResult, etc.)
│       └── config.py           # Configuration management
├── tests/
│   ├── test_chunking.py
│   ├── test_indexing.py
│   ├── test_retrieval.py
│   └── fixtures/
│       └── sample_markdown/    # Test markdown files
└── docs/
    ├── VISION.md
    ├── IMPLEMENTATION.md
    └── research/
        ├── qmd-architecture.md
        ├── advanced-retrieval-techniques.md
        └── python-ecosystem.md
```
