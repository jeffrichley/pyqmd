# Installation

## From Source (recommended for now)

pyqmd uses [uv](https://docs.astral.sh/uv/) for package management.

```bash
# Clone the repository
git clone https://github.com/jeffrichley/pyqmd.git
cd pyqmd

# Install with uv
uv sync

# Verify it works
uv run qmd --help
```

## Global Installation

To make `qmd` available anywhere without `uv run`:

```bash
uv tool install --editable /path/to/pyqmd
```

This installs the `qmd` command globally.

## Dependencies

pyqmd installs the following automatically:

| Package | Purpose |
|---------|---------|
| `sentence-transformers` | Embedding models (all-MiniLM-L6-v2) |
| `lancedb` | Vector + full-text storage |
| `typer` | CLI framework |
| `rich` | Terminal formatting |
| `markdown-it-py` | Markdown parsing |
| `pyyaml` | Configuration files |

!!! note "First Run"
    The first time you index or search, pyqmd downloads the embedding model (~90MB). This is a one-time download.
