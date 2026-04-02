# Python API

## PyQMD

The main entry point for the pyqmd library.

```python
from pyqmd import PyQMD

qmd = PyQMD(data_dir="~/.pyqmd", embed_model="all-MiniLM-L6-v2")
```

### Methods

#### `add_collection(name, paths, mask="**/*.md")`

Register a new collection of markdown files.

#### `remove_collection(name)`

Remove a collection and its indexed data.

#### `list_collections() -> list[str]`

List all registered collection names.

#### `index(name=None, force=False, observer=None) -> int`

Index a collection (or all if name is None). Returns the number of chunks indexed.

Pass a `ProgressObserver` to receive progress events:

```python
from pyqmd.progress import RichProgressObserver
qmd.index("collection", observer=RichProgressObserver())
```

#### `search(query, collections=None, top_k=10, rerank=False, expand_parents=False) -> list[SearchResult]`

Search across collections. Returns a list of `SearchResult` objects.

#### `status(name) -> dict`

Get status information for a collection.

## SearchResult

```python
@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    bm25_score: float | None
    vector_score: float | None
    rerank_score: float | None
```

## Chunk

```python
@dataclass
class Chunk:
    id: str
    content: str
    context: str | None
    source_file: str
    collection: str
    heading_path: list[str]
    parent_id: str | None
    start_line: int
    end_line: int
    metadata: dict
```

## ProgressObserver

A `Protocol` that defines the interface for progress reporting. Implement this to receive events from the indexing pipeline.

```python
from pyqmd.progress import ProgressObserver

class ProgressObserver(Protocol):
    def on_start(self, operation: str, total: int) -> None: ...
    def on_advance(self, count: int = 1) -> None: ...
    def on_message(self, message: str) -> None: ...
    def on_complete(self, operation: str, total: int) -> None: ...
```

The pipeline emits one `on_start` / `on_complete` pair and one `on_advance` call per unit of work for each of the three phases (chunking, embedding, storing).

## SilentObserver

The default observer. All methods are no-ops. Safe to use in tests and library contexts where no progress output is wanted.

```python
from pyqmd.progress import SilentObserver

qmd.index("collection", observer=SilentObserver())
```

## RichProgressObserver

Renders animated Rich progress bars in the terminal. Used by the CLI for all `qmd index` calls.

```python
from pyqmd.progress import RichProgressObserver

qmd.index("collection", observer=RichProgressObserver())
```

Each indexing run shows three progress bars — one for chunking, one for embedding, and one for storing — each with a spinner, bar, count, percentage, elapsed time, and ETA.

### Custom observers

Implement the `ProgressObserver` protocol to route progress events anywhere:

```python
import logging
from pyqmd.progress import ProgressObserver

class LoggingObserver:
    def on_start(self, operation: str, total: int) -> None:
        logging.info("start %s total=%d", operation, total)

    def on_advance(self, count: int = 1) -> None:
        pass  # too noisy to log every step

    def on_message(self, message: str) -> None:
        logging.info(message)

    def on_complete(self, operation: str, total: int) -> None:
        logging.info("done %s total=%d", operation, total)

qmd.index("collection", observer=LoggingObserver())
```

## OllamaContextGenerator

Generates 1–2 sentence context prefixes for chunks using a local Ollama model. Used by the contextual retrieval pipeline.

```python
from pyqmd.indexing.contextual import OllamaContextGenerator

generator = OllamaContextGenerator(
    model="qwen3.5:9b",          # Ollama model name
    base_url="http://localhost:11434",
)
```

### Methods

#### `generate_context(content, source_file="", heading_path=None) -> str`

Generate a context string for a single chunk. Returns an empty string if Ollama is unavailable.

#### `generate_batch(chunks, show_progress=True) -> list[str]`

Generate context for a list of `Chunk` objects. Returns a list of context strings in the same order.

#### `is_available() -> bool`

Return `True` if Ollama is running and the configured model is available.

## HyDEGenerator

Generates hypothetical answers for HyDE query expansion.

```python
from pyqmd.retrieval.hyde import HyDEGenerator

hyde = HyDEGenerator(
    model="qwen3.5:9b",
    base_url="http://localhost:11434",
)
```

### Methods

#### `generate_hypothetical(query) -> str`

Generate a hypothetical 2–3 sentence answer to `query`. Returns the original query string if generation fails.

#### `is_available() -> bool`

Return `True` if Ollama is running.

## GraphEngine

Manages a nano-graphrag knowledge graph over pyqmd content.

```python
from pyqmd.graph.engine import GraphEngine
import pathlib

engine = GraphEngine(
    data_dir=pathlib.Path("~/.pyqmd").expanduser(),
    best_model="qwen3:14b",     # used for entity extraction and query synthesis
    cheap_model="llama3.2",     # used for community summaries
    ollama_url="http://localhost:11434",
)
```

### Methods

#### `build(content, show_progress=True)`

Insert a string or list of strings into the graph. Shows a progress indicator by default.

#### `build_from_directory(directory, mask="**/*.md") -> int`

Build the graph from all matching files in `directory`. Returns the number of files processed.

#### `query(query, mode="local") -> str`

Query the knowledge graph and return a synthesized answer string.

- `mode="local"` — entity traversal, best for specific questions.
- `mode="global"` — community summaries, best for broad thematic questions.

#### `is_built() -> bool`

Return `True` if the graph has been built (`.graphml` file exists on disk).

#### `status() -> dict`

Return a dict with keys: `status`, `graph_dir`, `entities`, `relationships`, `best_model`, `cheap_model`.
