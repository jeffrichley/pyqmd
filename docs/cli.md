# CLI Reference

Every command supports `--json` for machine-readable output.

## Collection Management

### `qmd add`

```bash
qmd add <name> <path> [--mask "**/*.md"]
```

Add a new collection.

### `qmd remove`

```bash
qmd remove <name>
```

Remove a collection and its indexed data.

### `qmd list`

```bash
qmd list [--json]
```

List all collections.

### `qmd status`

```bash
qmd status <name> [--json]
```

Show collection statistics.

## Indexing

### `qmd index`

```bash
qmd index [name] [--full] [--contextual]
```

Index a collection (or all collections). Use `--full` to force re-index.

| Option | Description |
|--------|-------------|
| `--full` | Force re-index all files (ignore hash cache) |
| `--contextual` | Generate LLM context prefixes via Ollama before embedding |
| `--data-dir` | Override data directory |

`--contextual` calls a local Ollama model once per chunk to generate a 1–2 sentence context prefix. This improves retrieval by ~49% at the cost of ~1 second per chunk at index time. Requires Ollama with `qwen3.5:9b` (or another configured model).

## Watching

### `qmd watch`

```bash
qmd watch <name> [--debounce FLOAT] [--poll-interval FLOAT] [--ignore PATTERN...]
```

Monitor a collection for file changes and auto-index.

| Option | Description |
|--------|-------------|
| `--debounce` | Debounce window in seconds (overrides config) |
| `--poll-interval` | Poll interval in seconds, 0=disabled (overrides config) |
| `--ignore` | Additional ignore patterns (merged with config) |
| `--data-dir` | Override data directory |

Uses watchdog for OS-level filesystem events with an optional polling fallback. Configure defaults in `[watch]` in your `config.toml`.

## Searching

### `qmd search`

```bash
qmd search <query> [options]
```

| Option | Description |
|--------|-------------|
| `--collection`, `-c` | Search specific collection |
| `--top-k`, `-k` | Number of results (default: 10) |
| `--no-rerank` | Skip cross-encoder reranking |
| `--expand` | Include parent chunks |
| `--path-prefix` | Restrict results to files under a given path |
| `--hyde` | Use HyDE query expansion via Ollama |
| `--json` | JSON output |
| `--data-dir` | Override data directory |

`--hyde` generates a hypothetical answer to the query using Ollama, then embeds that answer instead of the raw query. Improves recall for technical and domain-specific questions. Adds one Ollama call per search.

## Knowledge Graph

### `qmd graph build`

```bash
qmd graph build [directory] [--collection <name>] [--best-model <model>] [--cheap-model <model>]
```

Build a knowledge graph from markdown files via entity extraction.

| Option | Default | Description |
|--------|---------|-------------|
| `directory` | — | Directory of markdown files (omit to use all collections) |
| `--collection`, `-c` | — | Build from a specific named collection |
| `--best-model` | `qwen3:14b` | Ollama model for entity extraction |
| `--cheap-model` | `llama3.2` | Ollama model for community summaries |
| `--data-dir` | `~/.pyqmd` | Data directory |

### `qmd graph query`

```bash
qmd graph query <question> [--mode local|global] [--best-model <model>] [--cheap-model <model>] [--json]
```

Query the knowledge graph. Returns a synthesized prose answer.

| Option | Default | Description |
|--------|---------|-------------|
| `--mode`, `-m` | `local` | `local` for entity traversal, `global` for community summaries |
| `--best-model` | `qwen3:14b` | Ollama model for query synthesis |
| `--cheap-model` | `llama3.2` | Ollama model for summaries |
| `--json` | — | Output as JSON |
| `--data-dir` | `~/.pyqmd` | Data directory |

### `qmd graph status`

```bash
qmd graph status [--json]
```

Show knowledge graph status: entity count, relationship count, storage path, and configured models.

## Configuration

### `qmd config`

```bash
qmd config [--json]
```

Show current configuration.
