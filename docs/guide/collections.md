# Collections

A collection is a named group of directories that pyqmd indexes and searches together.

## Adding Collections

```bash
qmd add <name> <path> [--mask "**/*.md"]
```

Examples:

```bash
qmd add notes ~/notes
qmd add project-docs ~/work/docs --mask "**/*.md"
```

## Listing Collections

```bash
qmd list
```

## Removing Collections

```bash
qmd remove <name>
```

This removes the collection configuration and its indexed data.

## Collection Status

```bash
qmd status <name>
```

Shows:

- Indexed paths
- File mask
- Chunk count
- Embedding model
- Chunk size setting
