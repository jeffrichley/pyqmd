# QMD (Query Markup Documents) Architecture Research

## Overview

QMD is a local search engine for markdown files created by Tobi Lutke (Shopify founder).
It is heavily used as a memory/retrieval backend for OpenClaw agents. The canonical repo
is [github.com/tobi/qmd](https://github.com/tobi/qmd).

**Key principle:** Markdown files are the source of truth — human-readable, version-controlled,
git-diffable. QMD indexes them for fast hybrid search without modifying the originals.

## Architecture

### Three Search Layers

1. **BM25 full-text search** — fast keyword matching for exact terms, error messages, code
   symbols, function names. Uses SQLite FTS5 under the hood.

2. **Vector semantic search** — finds conceptually similar content using local GGUF embedding
   models (embeddinggemma-300M). Vectors stored in sqlite-vec.

3. **Hybrid search with LLM re-ranking** — runs both in parallel, merges via Reciprocal Rank
   Fusion (RRF), then re-ranks with a local language model.

### Chunking Strategy

QMD uses a scoring algorithm to find natural markdown break points rather than cutting at
hard token boundaries:

- **Target chunk size:** ~900 tokens with 15% overlap
- **Break point scoring:** H1=100, H2=90, code block boundary=80, paragraph break=60, etc.
- **Code blocks are never split** — they are kept whole as atomic units
- **Tree-sitter integration** for AST-aware chunking of code files (not just markdown)
- **SHA-256 deduplication** — identical chunks across files are stored once

### Indexing Pipeline

1. Recursively scan `**/*.md` files (configurable via `--mask`)
2. Parse each file, identify natural break points using the scoring algorithm
3. Generate chunks with overlap
4. Compute embeddings for each chunk (embeddinggemma-300M, local GGUF model)
5. Store in SQLite: FTS5 index for BM25, sqlite-vec for vectors
6. SHA-256 hash each chunk for deduplication
7. Incremental updates — only re-index changed files (by mtime or hash)

### Query Pipeline (5 steps)

1. **Query expansion** — a fine-tuned Qwen3-based model generates typed sub-queries
   (keyword variants, semantic rephrasing, domain-specific expansions)
2. **Parallel retrieval** — BM25 and vector search run simultaneously
3. **Reciprocal Rank Fusion (RRF)** — merges results with k=60 (standard constant)
4. **Cross-encoder reranking** — Qwen3-Reranker-0.6B rescores the fused results
5. **Position-aware blending** — weights shift from RRF scores to reranker scores
   for lower-ranked results (top results trust RRF, tail results trust reranker)

### Collections

QMD organizes content into "collections" — named groups of directories. You can have
separate collections for different knowledge domains:

```
qmd add personal ~/notes
qmd add meetings ~/meeting-transcripts
qmd add project ~/code/my-project
```

Each collection is indexed independently but can be searched together or separately.

### Configuration & CLI

- `qmd add <name> <path>` — add a collection
- `qmd search <query>` — hybrid search across all collections
- `qmd search --collection <name> <query>` — search specific collection
- `--mask` flag to customize which files to include
- Runs entirely locally, no API keys or cloud dependencies

### Technology Stack (Original)

- **Runtime:** Bun (JavaScript)
- **Embeddings:** node-llama-cpp with GGUF models
- **Storage:** SQLite (FTS5 + sqlite-vec)
- **Reranking:** Local Qwen3-Reranker-0.6B via llama.cpp

### OpenClaw Integration

QMD plugs into OpenClaw as an optional memory backend. The plugin
[openclaw-qmd](https://github.com/YingQQQ/openclaw-qmd) provides L0/L1/L2 layered
context loading, reportedly reducing token usage by 50-80%:

- **L0:** Metadata only (titles, tags)
- **L1:** Summaries
- **L2:** Full content (loaded on demand)

### Known Limitations

- JavaScript/Bun only — no Python ecosystem support
- GGUF model management adds complexity
- No support for non-markdown file types without conversion
- No built-in support for incremental re-indexing of specific chunks (file-level only)
- Single-user design — no concurrency or multi-tenant support

## Sources

- [tobi/qmd on GitHub](https://github.com/tobi/qmd)
- [QMD Quick Start docs](https://www.mintlify.com/tobi/qmd/quickstart)
- [OpenClaw QMD Memory Engine docs](https://docs.openclaw.ai/concepts/memory-qmd)
- [OpenClaw QMD plugin](https://github.com/YingQQQ/openclaw-qmd)
- [QMD + OpenClaw Setup Guide (Gist)](https://gist.github.com/zacklavin11/e3aff840f245e39661d48a6a94cbcaef)
- [DEV Community: OpenClaw QMD local hybrid search](https://dev.to/chwu1946/openclaw-qmd-local-hybrid-search-for-10x-smarter-memory-4m8m)
