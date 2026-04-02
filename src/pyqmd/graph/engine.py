"""GraphRAG engine wrapping nano-graphrag with Ollama backend.

Builds a knowledge graph from indexed markdown content by extracting
entities and relationships via a local Ollama model. Supports both
global and local graph queries.
"""

import asyncio
import pathlib
from typing import Optional

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from nano_graphrag import GraphRAG, QueryParam
from nano_graphrag._utils import EmbeddingFunc

console = Console()


async def _ollama_complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: list = [],
    **kwargs,
) -> str:
    """Async LLM completion via Ollama for nano-graphrag."""
    hashing_kv = kwargs.pop("hashing_kv", None)

    # Check cache first
    if hashing_kv is not None:
        import hashlib
        cache_key = hashlib.md5(f"{system_prompt}:{prompt}".encode()).hexdigest()
        cached = await hashing_kv.get_by_id(cache_key)
        if cached is not None and cached.get("return"):
            return cached["return"]

    model = kwargs.pop("model", "qwen3:14b")
    base_url = kwargs.pop("base_url", "http://localhost:11434")
    max_tokens = kwargs.pop("max_tokens", 4096)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.3,
                    "num_ctx": 32000,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        result = data.get("message", {}).get("content", "")

        # Handle thinking models
        if not result and "thinking" in data:
            result = data["thinking"]
        if "<think>" in result:
            import re
            result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()

    # Cache the result
    if hashing_kv is not None:
        await hashing_kv.upsert({cache_key: {"return": result}})

    return result


async def _ollama_embed(texts: list[str], **kwargs) -> list[list[float]]:
    """Async embedding via sentence-transformers (runs sync in executor)."""
    from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding

    # Lazy singleton
    if not hasattr(_ollama_embed, "_embedder"):
        _ollama_embed._embedder = SentenceTransformerEmbedding()
    return _ollama_embed._embedder.embed(texts)


class GraphEngine:
    """Manages a nano-graphrag knowledge graph for pyqmd content."""

    def __init__(
        self,
        data_dir: pathlib.Path,
        best_model: str = "qwen3:14b",
        cheap_model: str = "llama3.2",
        ollama_url: str = "http://localhost:11434",
    ):
        self.data_dir = pathlib.Path(data_dir)
        self.graph_dir = self.data_dir / "graphrag"
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self.best_model = best_model
        self.cheap_model = cheap_model
        self.ollama_url = ollama_url
        self._graph = None

    def _get_graph(self) -> GraphRAG:
        """Lazy-load the GraphRAG instance."""
        if self._graph is None:
            # Create model functions with bound parameters
            async def best_complete(prompt, system_prompt=None, history_messages=[], **kwargs):
                kwargs["model"] = self.best_model
                kwargs["base_url"] = self.ollama_url
                return await _ollama_complete(prompt, system_prompt, history_messages, **kwargs)

            async def cheap_complete(prompt, system_prompt=None, history_messages=[], **kwargs):
                kwargs["model"] = self.cheap_model
                kwargs["base_url"] = self.ollama_url
                return await _ollama_complete(prompt, system_prompt, history_messages, **kwargs)

            from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding
            embedder = SentenceTransformerEmbedding()

            self._graph = GraphRAG(
                working_dir=str(self.graph_dir),
                best_model_func=best_complete,
                best_model_max_token_size=32000,
                best_model_max_async=4,
                cheap_model_func=cheap_complete,
                cheap_model_max_token_size=8192,
                cheap_model_max_async=8,
                embedding_func=EmbeddingFunc(
                    embedding_dim=embedder.dimension,
                    max_token_size=512,
                    func=_ollama_embed,
                ),
            )
        return self._graph

    def build(
        self,
        content: str | list[str],
        show_progress: bool = True,
    ) -> None:
        """Build the graph from text content.

        Args:
            content: A string or list of strings to index into the graph.
            show_progress: Whether to show a progress indicator.
        """
        graph = self._get_graph()

        if isinstance(content, list):
            # Batch insert
            if show_progress:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        f"Building graph ({len(content)} documents)...", total=None
                    )
                    for i, text in enumerate(content):
                        if text.strip():
                            graph.insert(text)
                        progress.update(task, description=f"Building graph ({i+1}/{len(content)} documents)...")
            else:
                for text in content:
                    if text.strip():
                        graph.insert(text)
        else:
            if show_progress:
                console.print("[bold]Building graph...[/bold]")
            graph.insert(content)

    def build_from_directory(
        self,
        directory: pathlib.Path,
        mask: str = "**/*.md",
    ) -> int:
        """Build the graph from all markdown files in a directory.

        Returns count of files processed.
        """
        files = sorted(pathlib.Path(directory).glob(mask))
        if not files:
            console.print(f"[yellow]No files matching {mask} in {directory}[/yellow]")
            return 0

        console.print(f"[bold]Found {len(files)} files to process.[/bold]")

        graph = self._get_graph()
        count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Building graph...", total=None)
            for i, f in enumerate(files):
                text = f.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    try:
                        graph.insert(text)
                        count += 1
                    except Exception as e:
                        progress.console.print(f"[yellow]Error on {f.name}: {e}[/yellow]")
                progress.update(task, description=f"Building graph ({i+1}/{len(files)} files)...")

        return count

    def query(
        self,
        query: str,
        mode: str = "local",
    ) -> str:
        """Query the knowledge graph.

        Args:
            query: The question to ask.
            mode: "local" for entity-traversal, "global" for community summaries.

        Returns the answer as a string.
        """
        graph = self._get_graph()
        param = QueryParam(mode=mode)
        return graph.query(query, param=param)

    def is_built(self) -> bool:
        """Check if the graph has been built (working dir has data)."""
        return (self.graph_dir / "graph_chunk_entity_relation.graphml").exists()

    def status(self) -> dict:
        """Get graph status info."""
        if not self.is_built():
            return {"status": "not built", "graph_dir": str(self.graph_dir)}

        # Try to count entities and relationships from graphml
        graphml_path = self.graph_dir / "graph_chunk_entity_relation.graphml"
        entity_count = 0
        edge_count = 0
        if graphml_path.exists():
            text = graphml_path.read_text(errors="replace")
            entity_count = text.count("<node ")
            edge_count = text.count("<edge ")

        return {
            "status": "built",
            "graph_dir": str(self.graph_dir),
            "entities": entity_count,
            "relationships": edge_count,
            "best_model": self.best_model,
            "cheap_model": self.cheap_model,
        }
