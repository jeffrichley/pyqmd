# Python Ecosystem Research for py-qmd

## The Gap

No Python port of QMD exists. There is the original Node.js version, a Go rewrite
([akhenakh/qmd](https://github.com/akhenakh/qmd)), and an MCP server wrapper
([ehc-io/qmd](https://github.com/ehc-io/qmd)), but nothing in Python. No "py-qmd"
package exists on PyPI.

## Existing Python Libraries (Building Blocks)

### Markdown-Aware Chunking

The chunking problem is largely solved. Multiple pip-installable libraries handle it:

| Library | Description | Notes |
|---------|-------------|-------|
| [markdown-chunker](https://pypi.org/project/markdown-chunker/) | C++ extension, splits at headers, preserves code blocks | Configurable min/max sizes |
| [md2chunks](https://github.com/verloop/md2chunks) | Context-enriched chunking for RAG | Preserves heading hierarchy |
| [markitdown-chunker](https://pypi.org/project/markitdown-chunker/) | Markdown-aware splitting | JSON metadata export |
| [semantic-chunker](https://pypi.org/project/semantic-chunker/) | Token-aware chunking with overlap | Good for general text |
| LangChain `MarkdownHeaderTextSplitter` | Splits by headers with metadata | Part of langchain ecosystem |

**Recommendation:** `md2chunks` or `markdown-chunker` as a starting point.
May want to build our own chunker for full control over the scoring algorithm
(matching QMD's break point scoring: H1=100, H2=90, code block boundary=80, etc.).

### Embedding Models

| Model | Dimensions | Speed | Quality | Notes |
|-------|-----------|-------|---------|-------|
| `all-MiniLM-L6-v2` | 384 | Fast | Good | Best for local/lightweight |
| `bge-small-en-v1.5` | 384 | Fast | Better | BAAI, good for English |
| `jina-embeddings-v2` | 768 | Medium | Very good | Supports late chunking |
| `nomic-embed-text` | 768 | Medium | Very good | Open source, local |
| `embeddinggemma-300M` | - | Medium | Good | What QMD uses (GGUF) |

**Recommendation:** Start with `sentence-transformers` + `all-MiniLM-L6-v2` for
speed. Upgrade to `nomic-embed-text` or `jina-embeddings-v2` for quality.
Support pluggable models so users can choose.

### Vector Storage

| Storage | Type | Hybrid Search | Notes |
|---------|------|--------------|-------|
| **LanceDB** | Embedded | Native BM25 + vector | Best for local, zero-config, Python-first |
| SQLite + sqlite-vec | Embedded | Manual (separate FTS5) | What QMD uses, more control |
| ChromaDB | Embedded | Limited | Simple but struggles at scale |
| Qdrant | Client-server | Yes | Overkill for local use |

**Recommendation:** **LanceDB** as the primary backend. It handles both BM25 and
vector search natively, is embedded (no server process), and stores data as Lance
files on disk. Optionally support SQLite + sqlite-vec for QMD-parity mode.

### BM25 Libraries

| Library | Notes |
|---------|-------|
| LanceDB built-in FTS | Native, no extra dependency |
| `bm25s` | Fast pure-Python BM25, good standalone option |
| `rank-bm25` | Older, widely used |
| SQLite FTS5 | What QMD uses, excellent performance |

### Reranking

| Library | Notes |
|---------|-------|
| `sentence-transformers` CrossEncoder | e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `ragatouille` (ColBERT) | Late interaction, better than cross-encoder |
| `flashrank` | Lightweight reranking |
| Local LLM via `llama-cpp-python` | Match QMD's approach with Qwen3-Reranker |

### Document Conversion

| Library | Converts | Notes |
|---------|----------|-------|
| `markitdown` (Microsoft) | PDF, DOCX, PPTX → Markdown | Essential for ingesting project PDFs |
| `pymupdf` / `fitz` | PDF → text/images | Lower level, more control |
| `whisper` / `faster-whisper` | Audio → text | For lecture transcription |

## What Needs to Be Built (The Glue Layer)

The individual pieces exist. What's missing is the orchestration:

1. **Directory watcher** — detect file changes, trigger re-indexing
2. **Indexing pipeline** — chunk → enrich (contextual retrieval) → embed → store
3. **Query pipeline** — expand → parallel search → RRF fusion → rerank → return
4. **Collection management** — named groups of directories, independent indexes
5. **CLI interface** — Typer-based commands for all operations
6. **Pluggable backends** — swap embedding models, storage engines, rerankers
7. **Incremental updates** — only re-index changed files (hash-based detection)

## Relevant Academic Papers

- "Reconstructing Context: Evaluating Advanced Chunking Strategies for RAG"
  ([arXiv 2504.19754](https://arxiv.org/abs/2504.19754)) — compares proposition,
  semantic, and adaptive chunking strategies
- "The Chunking Paradigm: Recursive Semantic for RAG Optimization"
  ([ACL 2025](https://aclanthology.org/2025.icnlsp-1.15.pdf)) — systematic study
  of recursive semantic chunking
- "Enhancing RAG: A Study of Best Practices"
  ([arXiv 2501.07391](https://arxiv.org/abs/2501.07391)) — systematic study of
  chunk size, retrieval stride, query expansion

## Sources

- [markdown-chunker on PyPI](https://pypi.org/project/markdown-chunker/)
- [md2chunks on GitHub](https://github.com/verloop/md2chunks)
- [LanceDB docs](https://lancedb.github.io/lancedb/)
- [sentence-transformers docs](https://www.sbert.net/)
- [ragatouille GitHub](https://github.com/bclavie/RAGatouille)
- [markitdown GitHub](https://github.com/microsoft/markitdown)
- [LanceDB vectordb-recipes](https://github.com/lancedb/vectordb-recipes)
