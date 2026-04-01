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
qmd index [name] [--full]
```

Index a collection (or all collections). Use `--full` to force re-index.

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
| `--json` | JSON output |
| `--data-dir` | Override data directory |

## Configuration

### `qmd config`

```bash
qmd config [--json]
```

Show current configuration.
