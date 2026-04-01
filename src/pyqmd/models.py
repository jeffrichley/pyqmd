"""Core data models for pyqmd."""

from dataclasses import dataclass, field


@dataclass
class CollectionConfig:
    """Per-collection configuration."""

    chunk_size: int = 800
    chunk_overlap: float = 0.15
    embed_model: str = "all-MiniLM-L6-v2"


@dataclass
class Chunk:
    """A chunk of text extracted from a markdown file."""

    id: str
    content: str
    context: str | None
    source_file: str
    collection: str
    heading_path: list[str]
    parent_id: str | None
    start_line: int
    end_line: int
    metadata: dict = field(default_factory=dict)

    @property
    def embeddable_content(self) -> str:
        """Content used for embedding — includes context prefix if available."""
        if self.context:
            return f"{self.context}\n\n{self.content}"
        return self.content


@dataclass
class SearchResult:
    """A search result containing a chunk and its scores."""

    chunk: Chunk
    score: float
    bm25_score: float | None = None
    vector_score: float | None = None
    rerank_score: float | None = None


@dataclass
class Collection:
    """A named group of directories to index."""

    name: str
    paths: list[str]
    mask: str = "**/*.md"
    config: CollectionConfig = field(default_factory=CollectionConfig)
