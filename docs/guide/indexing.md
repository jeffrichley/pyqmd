# Indexing

## Basic Indexing

```bash
# Index a specific collection
qmd index my-notes

# Index all collections
qmd index
```

## Incremental Updates

pyqmd tracks file content hashes (SHA-256). When you re-run `qmd index`, only files that have changed are re-processed.

## Force Re-index

```bash
qmd index --full
```

Ignores the hash cache and re-indexes everything.

## How Chunking Works

pyqmd uses a break-point scoring algorithm to find natural split points:

| Break Point | Score |
|-------------|-------|
| `# H1` heading | 100 |
| `## H2` heading | 90 |
| End of code block | 85 |
| `### H3` heading | 80 |
| Horizontal rule | 75 |
| `#### H4` heading | 70 |
| Blank line | 50 |

Chunks target ~800 characters with 15% overlap. Code blocks and tables are never split.

## Contextual Retrieval

Contextual retrieval adds a short LLM-generated prefix to each chunk before embedding it. The prefix describes where the chunk fits in its document — for example, "This chunk from the Sharpe Ratio guide covers the formula for annualizing daily returns." Searching with these enriched embeddings improves retrieval accuracy by approximately 49% (based on Anthropic's research on the technique).

### How to use it

```bash
qmd index --contextual
qmd index my-notes --contextual
```

Pass `--contextual` to any `qmd index` call. pyqmd will call a local Ollama model once per chunk to generate the context prefix, then embed the combined text.

### Prerequisites

[Ollama](https://ollama.com) must be running locally. The default model is `qwen3.5:9b`:

```bash
ollama pull qwen3.5:9b
```

### Performance

Context generation adds roughly 1 second per chunk depending on your hardware. For a 500-chunk collection that is around 8 minutes. You only pay this cost once — subsequent incremental indexes only process new or changed files.

### Python API

```python
qmd.index("my-notes", contextual=True)
```

## YAML Frontmatter

Frontmatter is parsed and attached as metadata to every chunk from that file:

```markdown
---
title: "My Document"
category: "notes"
tags: ["python", "ml"]
---

# Content here...
```
