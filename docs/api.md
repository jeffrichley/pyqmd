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

#### `index(name=None, force=False) -> int`

Index a collection (or all if name is None). Returns the number of chunks indexed.

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
