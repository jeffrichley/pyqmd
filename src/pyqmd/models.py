"""Core data models for pyqmd."""

from pydantic import BaseModel, Field


class WatchConfig(BaseModel):
    """Watch command configuration."""

    debounce: float = 2.0
    poll_interval: float = 0.0
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [".obsidian/", ".git/", "*.lock", "*.tmp", "~*"]
    )


class SearchConfig(BaseModel):
    """Search tuning configuration."""

    overfetch_multiplier: int = 2


class CollectionConfig(BaseModel):
    """Per-collection configuration. None values inherit from global config."""

    path: str = ""
    mask: str = "**/*.md"
    description: str = ""
    chunk_size: int | None = None
    chunk_overlap: float | None = None
    embed_model: str | None = None


class Collection(BaseModel):
    """A named group of directories to index.

    This is the runtime representation used throughout the codebase.
    CollectionConfig is the serialized TOML representation.
    """

    name: str
    paths: list[str]
    mask: str = "**/*.md"
    description: str = ""
    chunk_size: int = 800
    chunk_overlap: float = 0.15
    embed_model: str = "all-MiniLM-L6-v2"


class Chunk(BaseModel):
    """A chunk of text extracted from a markdown file."""

    model_config = {"frozen": False}

    id: str
    content: str
    context: str | None = None
    source_file: str
    collection: str
    heading_path: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    start_line: int = 0
    end_line: int = 0
    metadata: dict = Field(default_factory=dict)

    @property
    def embeddable_content(self) -> str:
        """Content used for embedding — includes context prefix if available."""
        if self.context:
            return f"{self.context}\n\n{self.content}"
        return self.content


class SearchResult(BaseModel):
    """A search result containing a chunk and its scores."""

    chunk: Chunk
    score: float
    bm25_score: float | None = None
    vector_score: float | None = None
    rerank_score: float | None = None
