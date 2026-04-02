"""Typer CLI for pyqmd."""

import json
import pathlib
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from pyqmd.core import PyQMD

app = typer.Typer(
    name="qmd",
    help="pyqmd: Python-native local search engine for markdown files.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

_DEFAULT_DATA_DIR = str(pathlib.Path.home() / ".pyqmd")


def _get_qmd(data_dir: str) -> PyQMD:
    return PyQMD(data_dir=pathlib.Path(data_dir))


@app.command("add")
def add_collection(
    name: Annotated[str, typer.Argument(help="Collection name")],
    path: Annotated[str, typer.Argument(help="Directory path to index")],
    mask: Annotated[str, typer.Option("--mask", help="Glob mask for file selection")] = "**/*.md",
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Add a new collection."""
    qmd = _get_qmd(data_dir)
    try:
        qmd.add_collection(name, paths=[path], mask=mask)
        console.print(f"[green]Added collection '{name}' with path: {path}[/green]")
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("remove")
def remove_collection(
    name: Annotated[str, typer.Argument(help="Collection name")],
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Remove a collection and its indexed data."""
    qmd = _get_qmd(data_dir)
    try:
        qmd.remove_collection(name)
        console.print(f"[green]Removed collection '{name}'[/green]")
    except KeyError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("list")
def list_collections(
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """List all collections."""
    qmd = _get_qmd(data_dir)
    collections = qmd.list_collections()

    if as_json:
        typer.echo(json.dumps(collections))
    else:
        if not collections:
            console.print("[yellow]No collections configured.[/yellow]")
        else:
            table = Table(title="Collections")
            table.add_column("Name", style="cyan")
            for col in collections:
                table.add_row(col)
            console.print(table)


@app.command("index")
def index_collection(
    name: Annotated[Optional[str], typer.Argument(help="Collection name (omit to index all)")] = None,
    full: Annotated[bool, typer.Option("--full", help="Force re-index all files")] = False,
    contextual: Annotated[bool, typer.Option("--contextual", help="Generate context via Ollama before embedding")] = False,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Index one or all collections."""
    qmd = _get_qmd(data_dir)
    try:
        count = qmd.index(collection_name=name, force=full, contextual=contextual)
        label = f"'{name}'" if name else "all collections"
        ctx_label = " (with contextual retrieval)" if contextual else ""
        console.print(f"[green]Indexed {label}: {count} chunks{ctx_label}[/green]")
    except KeyError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("search")
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    collection: Annotated[Optional[list[str]], typer.Option("--collection", "-c", help="Collection to search")] = None,
    top_k: Annotated[int, typer.Option("--top-k", "-k", help="Number of results")] = 10,
    no_rerank: Annotated[bool, typer.Option("--no-rerank", help="Disable reranking")] = False,
    expand: Annotated[bool, typer.Option("--expand", help="Expand to parent chunks")] = False,
    use_hyde: Annotated[bool, typer.Option("--hyde", help="Use HyDE query expansion via Ollama")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Search across collections."""
    qmd = _get_qmd(data_dir)
    results = qmd.search(
        query,
        collections=collection,
        top_k=top_k,
        rerank=not no_rerank and False,  # reranking disabled by default (slow model load)
        expand_parent=expand,
        hyde=use_hyde,
    )

    if as_json:
        data = [
            {
                "score": r.score,
                "content": r.chunk.content,
                "source_file": r.chunk.source_file,
                "collection": r.chunk.collection,
                "heading_path": r.chunk.heading_path,
                "rerank_score": r.rerank_score,
            }
            for r in results
        ]
        typer.echo(json.dumps(data))
    else:
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        for i, r in enumerate(results, 1):
            heading = " > ".join(r.chunk.heading_path) if r.chunk.heading_path else ""
            console.print(f"\n[bold cyan][{i}] {r.chunk.source_file}[/bold cyan]" + (f" [{heading}]" if heading else ""))
            console.print(f"[dim]Score: {r.score:.4f}[/dim]")
            console.print(r.chunk.content[:300] + ("..." if len(r.chunk.content) > 300 else ""))


@app.command("status")
def status(
    name: Annotated[str, typer.Argument(help="Collection name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Show status of a collection."""
    qmd = _get_qmd(data_dir)
    try:
        info = qmd.status(name)
    except KeyError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

    if as_json:
        typer.echo(json.dumps(info))
    else:
        console.print(f"[bold]Collection:[/bold] {info['name']}")
        console.print(f"[bold]Chunks:[/bold] {info['chunk_count']}")
        console.print(f"[bold]Paths:[/bold] {', '.join(info['paths'])}")
        console.print(f"[bold]Mask:[/bold] {info['mask']}")
        console.print(f"[bold]Embed model:[/bold] {info['embed_model']}")


@app.command("config")
def show_config(
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    data_dir: Annotated[str, typer.Option("--data-dir", help="Data directory")] = _DEFAULT_DATA_DIR,
) -> None:
    """Show global configuration."""
    qmd = _get_qmd(data_dir)
    cfg = qmd.config
    info = {
        "data_dir": str(cfg.data_dir),
        "embed_model": cfg.embed_model,
        "chunk_size": cfg.chunk_size,
        "chunk_overlap": cfg.chunk_overlap,
        "storage_backend": cfg.storage_backend,
        "collections": list(cfg.collections.keys()),
    }

    if as_json:
        typer.echo(json.dumps(info))
    else:
        console.print(f"[bold]Data dir:[/bold] {info['data_dir']}")
        console.print(f"[bold]Embed model:[/bold] {info['embed_model']}")
        console.print(f"[bold]Chunk size:[/bold] {info['chunk_size']}")
        console.print(f"[bold]Chunk overlap:[/bold] {info['chunk_overlap']}")
        console.print(f"[bold]Storage:[/bold] {info['storage_backend']}")
        console.print(f"[bold]Collections:[/bold] {', '.join(info['collections']) or '(none)'}")


def main() -> None:
    """Entry point for the qmd CLI."""
    app()


if __name__ == "__main__":
    main()
