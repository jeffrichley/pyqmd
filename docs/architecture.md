# Architecture

## Overview

```
Markdown Files (source of truth)
    │
    ▼
┌──────────────────────────────┐
│     Markdown-Aware Chunker   │
│  (break-point scoring, no    │
│   code block splits, YAML    │
│   frontmatter extraction)    │
└──────────────┬───────────────┘
               │
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
┌──────────────────────────────┐
│     Retrieval Pipeline       │
│  BM25 + Vector → RRF Fusion │
│  → Cross-Encoder Reranking  │
│  → Parent Chunk Expansion   │
└──────────────────────────────┘
```

## Chunking

The chunker uses a scoring algorithm to find natural break points in markdown documents. Each potential break point (heading, blank line, end of code block) gets a score. The chunker accumulates content until it reaches the target size, then breaks at the highest-scored point.

## Hybrid Search

pyqmd runs BM25 (keyword) and vector (semantic) search in parallel, then merges results using Reciprocal Rank Fusion with k=60. This combines the precision of keyword matching with the recall of semantic search.

## Incremental Indexing

File content hashes (SHA-256) are tracked. On re-index, only changed files are reprocessed. This makes re-indexing fast even for large collections.
