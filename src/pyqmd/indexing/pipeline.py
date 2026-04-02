"""Indexing pipeline: chunk files, embed, store."""

import pathlib
from typing import Optional

from pyqmd.chunking.markdown import MarkdownChunker
from pyqmd.embeddings.base import EmbeddingModel
from pyqmd.indexing.hasher import FileHashRegistry
from pyqmd.progress import ProgressObserver, SilentObserver
from pyqmd.storage.base import StorageBackend


class IndexingPipeline:
    def __init__(
        self,
        storage: StorageBackend,
        embedder: EmbeddingModel,
        chunker: MarkdownChunker,
        hasher: FileHashRegistry,
        context_generator: Optional["OllamaContextGenerator"] = None,
        observer: ProgressObserver | None = None,
    ):
        self.storage = storage
        self.embedder = embedder
        self.chunker = chunker
        self.hasher = hasher
        self.context_generator = context_generator
        self.observer = observer or SilentObserver()

    def index_file(self, path: pathlib.Path, collection: str, force: bool = False) -> int:
        if not force and not self.hasher.has_changed(path):
            return 0
        self.storage.delete_by_source_file(collection, str(path))
        chunks = self.chunker.chunk_file(path, collection=collection)
        if not chunks:
            return 0

        # Generate contextual retrieval prefixes if available
        if self.context_generator:
            contexts = self.context_generator.generate_batch(chunks, show_progress=False)
            for chunk, ctx in zip(chunks, contexts):
                if ctx:
                    chunk.context = ctx

        texts = [c.embeddable_content for c in chunks]
        vectors = self.embedder.embed(texts)
        self.storage.store(collection, list(zip(chunks, vectors)))
        self.hasher.record(path)
        self.hasher.save()
        return len(chunks)

    def index_directory(
        self,
        directory: pathlib.Path,
        collection: str,
        mask: str = "**/*.md",
        force: bool = False,
    ) -> int:
        files = [f for f in sorted(directory.glob(mask)) if f.is_file()]
        if not files:
            return 0

        self.observer.on_start(f"Indexing {collection}", total=len(files))
        total = 0
        for path in files:
            count = self.index_file(path, collection=collection, force=force)
            total += count
            self.observer.on_advance()
        self.observer.on_complete(f"Indexing {collection}", total=total)
        return total
