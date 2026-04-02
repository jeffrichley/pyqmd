"""Contextual retrieval: generate context for chunks via Ollama.

Before embedding, each chunk gets a 1-2 sentence context prefix explaining
where it fits in the document. This improves retrieval by ~49% (per Anthropic's
research). Uses a local Ollama model to generate the context for free.
"""

import httpx
from rich.console import Console

console = Console()

CONTEXT_PROMPT = """You are a context generator for a search engine. Given a document title and a chunk of text from that document, write a brief 1-2 sentence context that explains what this chunk is about and where it fits in the document. Be specific and concise.

Document: {source_file}
Heading path: {heading_path}

Chunk:
{content}

Context (1-2 sentences):"""


class OllamaContextGenerator:
    """Generates context prefixes for chunks using a local Ollama model."""

    def __init__(
        self,
        model: str = "qwen3.5:9b",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url
        self._client = httpx.Client(timeout=60.0)

    def generate_context(
        self,
        content: str,
        source_file: str = "",
        heading_path: list[str] | None = None,
    ) -> str:
        """Generate a context string for a single chunk."""
        path_str = " > ".join(heading_path) if heading_path else ""
        prompt = CONTEXT_PROMPT.format(
            source_file=source_file,
            heading_path=path_str,
            content=content[:2000],  # truncate very long chunks
        )

        try:
            response = self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100,  # short context, ~1-2 sentences
                    },
                },
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            # Clean up: remove thinking tags if present (qwen3 sometimes adds these)
            if "<think>" in result:
                # Remove everything between <think> and </think>
                import re
                result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
            return result
        except Exception as e:
            console.print(f"[yellow]Warning: Context generation failed: {e}[/yellow]")
            return ""

    def generate_batch(
        self,
        chunks: list,  # list of Chunk objects
        show_progress: bool = True,
    ) -> list[str]:
        """Generate context for a batch of chunks. Returns list of context strings."""
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn

        contexts = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                MofNCompleteColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Generating context", total=len(chunks))
                for chunk in chunks:
                    ctx = self.generate_context(
                        content=chunk.content,
                        source_file=chunk.source_file,
                        heading_path=chunk.heading_path,
                    )
                    contexts.append(ctx)
                    progress.advance(task)
        else:
            for chunk in chunks:
                ctx = self.generate_context(
                    content=chunk.content,
                    source_file=chunk.source_file,
                    heading_path=chunk.heading_path,
                )
                contexts.append(ctx)

        return contexts

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            # Check if our model is available (with or without tag)
            return any(self.model in m or m.startswith(self.model.split(":")[0]) for m in models)
        except Exception:
            return False
