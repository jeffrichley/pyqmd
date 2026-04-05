"""LanceDB storage backend with native hybrid search."""

import json
import pathlib

import lancedb
import pyarrow as pa

from pyqmd.models import Chunk
from pyqmd.storage.base import StorageBackend


class LanceDBBackend(StorageBackend):
    def __init__(self, data_dir: pathlib.Path, dimension: int):
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.db = lancedb.connect(str(self.data_dir))

    def _table_name(self, collection: str) -> str:
        return f"pyqmd_{collection}"

    def _table_names(self) -> list[str]:
        """Return list of table name strings, compatible across LanceDB versions."""
        result = self.db.list_tables()
        # LanceDB >= 0.20 returns a ListTablesResponse object with a .tables attribute
        if hasattr(result, "tables"):
            return result.tables
        # Older versions return a list directly
        return list(result)

    def _get_or_create_table(self, collection: str) -> lancedb.table.Table:
        table_name = self._table_name(collection)
        if table_name in self._table_names():
            return self.db.open_table(table_name)
        schema = pa.schema([
            pa.field("chunk_id", pa.string()),
            pa.field("content", pa.string()),
            pa.field("source_file", pa.string()),
            pa.field("collection", pa.string()),
            pa.field("heading_path", pa.string()),
            pa.field("parent_id", pa.string()),
            pa.field("start_line", pa.int32()),
            pa.field("end_line", pa.int32()),
            pa.field("metadata", pa.string()),
            pa.field("context", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self.dimension)),
        ])
        return self.db.create_table(table_name, schema=schema)

    def _chunk_to_row(self, chunk: Chunk, vector: list[float]) -> dict:
        return {
            "chunk_id": chunk.id,
            "content": chunk.content,
            "source_file": chunk.source_file,
            "collection": chunk.collection,
            "heading_path": json.dumps(chunk.heading_path),
            "parent_id": chunk.parent_id or "",
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "metadata": json.dumps(chunk.metadata),
            "context": chunk.context or "",
            "vector": vector,
        }

    def _row_to_chunk(self, row: dict) -> Chunk:
        return Chunk(
            id=row["chunk_id"],
            content=row["content"],
            context=row["context"] if row.get("context") else None,
            source_file=row["source_file"],
            collection=row["collection"],
            heading_path=json.loads(row["heading_path"]),
            parent_id=row["parent_id"] if row.get("parent_id") else None,
            start_line=row["start_line"],
            end_line=row["end_line"],
            metadata=json.loads(row["metadata"]),
        )

    def store(self, collection: str, chunks_with_vectors: list[tuple[Chunk, list[float]]]) -> None:
        table = self._get_or_create_table(collection)
        rows = [self._chunk_to_row(c, v) for c, v in chunks_with_vectors]
        table.add(rows)
        try:
            table.create_fts_index("content", replace=True)
        except Exception:
            pass  # FTS index creation can fail in some environments

    def search_vector(self, collection: str, query_vector: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        table_name = self._table_name(collection)
        if table_name not in self._table_names():
            return []
        table = self.db.open_table(table_name)
        results = table.search(query_vector).limit(top_k).to_list()
        return [(r["chunk_id"], float(r.get("_distance", 0.0))) for r in results]

    def search_text(self, collection: str, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        table_name = self._table_name(collection)
        if table_name not in self._table_names():
            return []
        table = self.db.open_table(table_name)
        try:
            results = table.search(query, query_type="fts").limit(top_k).to_list()
            return [(r["chunk_id"], float(r.get("_score", 0.0))) for r in results]
        except Exception:
            return []

    def get_chunk(self, collection: str, chunk_id: str) -> Chunk | None:
        table_name = self._table_name(collection)
        if table_name not in self._table_names():
            return None
        table = self.db.open_table(table_name)
        results = table.search().where(f"chunk_id = '{chunk_id}'").limit(1).to_list()
        if not results:
            return None
        return self._row_to_chunk(results[0])

    def delete_by_source_file(self, collection: str, source_file: str) -> None:
        table_name = self._table_name(collection)
        if table_name not in self._table_names():
            return
        table = self.db.open_table(table_name)
        table.delete(f"source_file = '{source_file}'")

    def delete_collection(self, collection: str) -> None:
        table_name = self._table_name(collection)
        if table_name in self._table_names():
            self.db.drop_table(table_name)

    def count(self, collection: str) -> int:
        table_name = self._table_name(collection)
        if table_name not in self._table_names():
            return 0
        table = self.db.open_table(table_name)
        return table.count_rows()

    def list_collections(self) -> list[str]:
        prefix = "pyqmd_"
        return [
            name[len(prefix):]
            for name in self._table_names()
            if name.startswith(prefix)
        ]
