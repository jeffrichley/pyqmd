# Architecture

## Overview

```
Markdown Files (source of truth)
    │
    ├──────────────────────────────────────────────────────────┐
    │                                                          │
    ▼                                                          ▼
┌──────────────────────────────┐              ┌───────────────────────────────┐
│     Markdown-Aware Chunker   │              │         GraphRAG Pipeline     │
│  (break-point scoring, no    │              │  (nano-graphrag + Ollama)     │
│   code block splits, YAML    │              │                               │
│   frontmatter extraction)    │              │  Entity Extraction            │
└──────────────┬───────────────┘              │  (qwen3:14b)                  │
               │                              │      │                        │
               ▼                              │      ▼                        │
┌──────────────────────────────┐              │  Community Summaries          │
│  Contextual Retrieval        │              │  (llama3.2)                   │
│  (optional, --contextual)    │              │      │                        │
│  Ollama generates 1-2 sent.  │              │      ▼                        │
│  context prefix per chunk    │              │  Knowledge Graph on disk      │
└──────────────┬───────────────┘              │  (.graphml)                   │
               │                              └───────────────────────────────┘
               ▼
┌──────────────────────────────┐
│      Embedding Layer         │
│   (sentence-transformers,    │
│    all-MiniLM-L6-v2)        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Storage Layer          │
│  (LanceDB: vectors + FTS)   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│           Query Pipeline                 │
│                                          │
│  [HyDE] Ollama generates hypothetical    │
│  answer → embed answer instead of query  │
│  (optional, --hyde)                      │
│                │                         │
│                ▼                         │
│  BM25 + Vector → RRF Fusion             │
│  → Cross-Encoder Reranking              │
│  → Parent Chunk Expansion               │
└──────────────────────────────────────────┘
```

## Chunking

The chunker uses a scoring algorithm to find natural break points in markdown documents. Each potential break point (heading, blank line, end of code block) gets a score. The chunker accumulates content until it reaches the target size, then breaks at the highest-scored point.

## Hybrid Search

pyqmd runs BM25 (keyword) and vector (semantic) search in parallel, then merges results using Reciprocal Rank Fusion with k=60. This combines the precision of keyword matching with the recall of semantic search.

## Incremental Indexing

File content hashes (SHA-256) are tracked. On re-index, only changed files are reprocessed. This makes re-indexing fast even for large collections.

## Batched Indexing Pipeline

When indexing a directory, pyqmd uses a 3-phase batched approach rather than processing files one at a time:

1. **Chunk** — all files are chunked up front into a single flat list.
2. **Embed** — all chunk texts are embedded in batches of 512, maximising GPU/CPU utilisation.
3. **Store** — chunks and vectors are written to LanceDB in file-aligned batches; hashes are recorded.

With `--force`, the entire LanceDB collection is dropped once before rebuilding, which is faster than issuing per-file deletes.

## Progress Observer Pattern

Progress reporting is separated from pipeline logic via the `ProgressObserver` protocol in `pyqmd.progress`. The pipeline emits four events per phase (`on_start`, `on_advance`, `on_message`, `on_complete`) to whatever observer is passed in.

Three implementations ship out of the box:

| Class | Behaviour |
|---|---|
| `SilentObserver` | Default — does nothing (suitable for tests and library use) |
| `RichProgressObserver` | Renders animated Rich progress bars (used by the CLI) |
| Custom | Implement the `ProgressObserver` protocol for logging, JSON output, etc. |
