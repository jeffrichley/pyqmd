# py-qmd: Python Query Markup Documents

## What Is This?

A Python-native local search engine for markdown files, inspired by
[QMD](https://github.com/tobi/qmd) but going beyond it. py-qmd indexes directories
of markdown files and makes them searchable via hybrid search (full-text + semantic +
reranking), all running locally with no cloud dependencies.

## Why Build This?

QMD (by Tobi Lutke) proved the concept: markdown files as a source of truth, indexed
for fast hybrid retrieval. But QMD is JavaScript/Bun only. The Python ecosystem has all
the individual pieces (chunkers, embedding models, vector stores, rerankers) but nobody
has built the glue layer that ties them together into a cohesive, local-first search
engine with a clean CLI.

py-qmd fills that gap.

## Core Principles

1. **Markdown is the source of truth.** Files are human-readable, version-controlled,
   git-diffable. py-qmd indexes them without modifying them.

2. **Local-first.** Everything runs on your machine. No API keys required for core
   search functionality. (LLM-powered features like contextual retrieval and HyDE
   optionally use an API.)

3. **Pluggable.** Swap embedding models, storage backends, rerankers. Start simple,
   upgrade components independently.

4. **Beyond QMD.** Incorporate techniques QMD doesn't have: contextual retrieval,
   parent-child retrieval, ColBERT, GraphRAG, HyDE.

5. **Python-native.** Built with uv, Rich logging, Typer CLI. First-class Python
   library API alongside the CLI.

## Who Is This For?

- Developers who keep knowledge in markdown (notes, docs, meeting transcripts)
- AI agent builders who need a local retrieval backend (Claude Code skills, MCP servers)
- Educators who need to search across semesters of course materials and forum archives
- Anyone who wants "search my markdown files" without spinning up Elasticsearch

## How It Compares to QMD

| Feature | QMD | py-qmd |
|---------|-----|--------|
| Language | JavaScript/Bun | Python |
| Chunking | Markdown-aware, AST for code | Same + configurable scoring |
| BM25 | SQLite FTS5 | LanceDB native (or SQLite FTS5) |
| Vector search | sqlite-vec | LanceDB native (or sqlite-vec) |
| Embeddings | embeddinggemma-300M (GGUF) | Pluggable (sentence-transformers, GGUF, API) |
| Reranking | Qwen3-Reranker-0.6B | Pluggable (cross-encoder, ColBERT, local LLM) |
| Fusion | RRF | RRF + position-aware blending |
| Contextual retrieval | No | Yes (Tier 1) |
| Parent-child retrieval | No | Yes (Tier 1) |
| HyDE | Partial | Yes (Tier 2) |
| ColBERT | No | Yes (Tier 2) |
| GraphRAG | No | Yes (Tier 3) |
| RAPTOR | No | Yes (Tier 3) |
| CLI | Custom | Typer + Rich |
| Python API | No | First-class |
| MCP server | Separate wrapper | Built-in option |
| Claude Code skill | No | Planned |

## Relationship to the EdStem Bot Project

py-qmd is a standalone library that the EdStem automation system will use as its
knowledge base and retrieval engine. The dependency flows one way:

```
py-qmd (standalone library, reusable)
    ↑
ed-api (EdStem API client)
    ↑
ed-ingest (scraper + media pipeline → markdown files → py-qmd collections)
    ↑
ed-bot (answer engine, Claude Code skills)
```

py-qmd knows nothing about EdStem. It just indexes and searches markdown files.
