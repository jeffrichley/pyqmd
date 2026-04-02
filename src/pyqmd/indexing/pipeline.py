"""Indexing pipeline: chunk files, embed, store.

Supports two modes:
- Per-file: chunk → embed → store one file at a time (used for single files)
- Batched: chunk ALL files → embed in large batches → store all (much faster for directories)
"""

import pathlib
from typing import Optional

from pyqmd.chunking.markdown import MarkdownChunker
from pyqmd.embeddings.base import EmbeddingModel
from pyqmd.indexing.hasher import FileHashRegistry
from pyqmd.progress import ProgressObserver, SilentObserver
from pyqmd.storage.base import StorageBackend

# Embedding batch size — how many texts to embed in one call.
# Larger = better GPU utilization, but more memory.
EMBED_BATCH_SIZE = 512


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
        """Index a single file. Used for incremental updates."""
        if not force and not self.hasher.has_changed(path):
            return 0
        self.storage.delete_by_source_file(collection, str(path))
        chunks = self.chunker.chunk_file(path, collection=collection)
        if not chunks:
            return 0

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
        """Index all files in a directory using batched embedding.

        Phase 1: Chunk all files (fast, CPU only)
        Phase 2: Embed all chunks in large batches (GPU/CPU intensive, benefits from batching)
        Phase 3: Store all chunks and update hashes
        """
        files = [f for f in sorted(directory.glob(mask)) if f.is_file()]
        if not files:
            return 0

        # Filter to files that need indexing
        if not force:
            files = [f for f in files if self.hasher.has_changed(f)]
            if not files:
                return 0

        # Phase 1: Chunk all files
        self.observer.on_start(f"Chunking {collection}", total=len(files))

        all_chunks = []       # flat list of all chunks
        file_boundaries = []  # (file_path, start_idx, end_idx) for hash tracking

        for path in files:
            self.storage.delete_by_source_file(collection, str(path))
            chunks = self.chunker.chunk_file(path, collection=collection)

            if self.context_generator and chunks:
                contexts = self.context_generator.generate_batch(chunks, show_progress=False)
                for chunk, ctx in zip(chunks, contexts):
                    if ctx:
                        chunk.context = ctx

            start_idx = len(all_chunks)
            all_chunks.extend(chunks)
            file_boundaries.append((path, start_idx, len(all_chunks)))
            self.observer.on_advance()

        self.observer.on_complete(f"Chunking {collection}", total=len(files))

        if not all_chunks:
            return 0

        # Phase 2: Embed in large batches
        self.observer.on_start(
            f"Embedding {collection} ({len(all_chunks)} chunks)",
            total=(len(all_chunks) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE,
        )

        all_texts = [c.embeddable_content for c in all_chunks]
        all_vectors = []

        for i in range(0, len(all_texts), EMBED_BATCH_SIZE):
            batch = all_texts[i : i + EMBED_BATCH_SIZE]
            vectors = self.embedder.embed(batch)
            all_vectors.extend(vectors)
            self.observer.on_advance()

        self.observer.on_complete(f"Embedding {collection}", total=len(all_chunks))

        # Phase 3: Store and update hashes
        self.observer.on_start(f"Storing {collection}", total=len(file_boundaries))

        pairs = list(zip(all_chunks, all_vectors))

        # Store in batches aligned to file boundaries for clean error recovery
        for path, start_idx, end_idx in file_boundaries:
            file_pairs = pairs[start_idx:end_idx]
            if file_pairs:
                self.storage.store(collection, file_pairs)
            self.hasher.record(path)
            self.observer.on_advance()

        self.hasher.save()
        self.observer.on_complete(f"Storing {collection}", total=len(all_chunks))

        return len(all_chunks)
