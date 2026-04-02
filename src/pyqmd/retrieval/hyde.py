"""HyDE: Hypothetical Document Embeddings.

At query time, generate a hypothetical answer to the query using an LLM,
then embed that answer instead of the raw query. The hypothetical answer
is closer in embedding space to real answers than the question is.
Uses a local Ollama model.
"""

import httpx
from rich.console import Console

console = Console()

HYDE_PROMPT = """You are a knowledgeable teaching assistant. A student asks:

"{query}"

Write a brief, direct answer to this question (2-3 sentences). Be specific and factual. If you're not sure, give your best guess at what a correct answer would contain.

Answer:"""


class HyDEGenerator:
    """Generates hypothetical documents for HyDE query expansion."""

    def __init__(
        self,
        model: str = "qwen3.5:9b",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url
        self._client = httpx.Client(timeout=30.0)

    def generate_hypothetical(self, query: str) -> str:
        """Generate a hypothetical answer to a query.

        Returns the hypothetical document text, or the original query
        if generation fails.
        """
        prompt = HYDE_PROMPT.format(query=query)

        try:
            response = self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 200,
                    },
                },
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            # Clean up thinking tags
            if "<think>" in result:
                import re
                result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
            return result if result else query
        except Exception as e:
            console.print(f"[dim]HyDE generation failed, using original query: {e}[/dim]")
            return query

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return True
        except Exception:
            return False
