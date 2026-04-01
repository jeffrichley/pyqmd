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
