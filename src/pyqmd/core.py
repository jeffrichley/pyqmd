"""PyQMD core class — main entry point for indexing and searching."""

import pathlib

from pyqmd.chunking.markdown import MarkdownChunker
from pyqmd.config import PyQMDConfig
from pyqmd.embeddings.sentence_transformers import SentenceTransformerEmbedding
from pyqmd.indexing.hasher import FileHashRegistry
from pyqmd.indexing.pipeline import IndexingPipeline
from pyqmd.models import Collection, SearchResult
from pyqmd.retrieval.pipeline import RetrievalPipeline
from pyqmd.storage.lancedb_backend import LanceDBBackend


class PyQMD:
    """Main entry point for the pyqmd local search engine.

    Manages configuration, storage, embeddings, and delegates to
    IndexingPipeline and RetrievalPipeline.
    """

    def __init__(self, data_dir: pathlib.Path | str | None = None):
        if data_dir is None:
            data_dir = pathlib.Path.home() / ".pyqmd"
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.config = PyQMDConfig.load(self.data_dir)
        self.config.data_dir = self.data_dir  # ensure data_dir is set

        # Create embedder
        self._embedder = SentenceTransformerEmbedding(model_name=self.config.embed_model)

        # Create storage backend
        lancedb_dir = self.data_dir / "lancedb"
        self._storage = LanceDBBackend(data_dir=lancedb_dir, dimension=self._embedder.dimension)

        # Reranker and Ollama-based features are lazy-loaded
        self._reranker = None
        self._context_generator = None
        self._hyde_generator = None

    def _get_indexing_pipeline(self, collection_name: str, contextual: bool = False, observer=None) -> IndexingPipeline:
        """Create an IndexingPipeline configured for the given collection."""
        col = self.config.collections.get(collection_name)
        if col is None:
            raise KeyError(f"Collection '{collection_name}' not found")

        chunker = MarkdownChunker(
            target_size=col.config.chunk_size,
            overlap=col.config.chunk_overlap,
        )
        hasher = FileHashRegistry(self.data_dir / "hashes" / f"{collection_name}.json")
        context_gen = self._get_context_generator() if contextual else None
        return IndexingPipeline(
            storage=self._storage,
            embedder=self._embedder,
            chunker=chunker,
            hasher=hasher,
            context_generator=context_gen,
            observer=observer,
        )

    def _get_reranker(self):
        """Lazy-load the cross-encoder reranker."""
        if self._reranker is None:
            from pyqmd.retrieval.rerank import CrossEncoderReranker
            self._reranker = CrossEncoderReranker()
        return self._reranker

    def _get_context_generator(self, model: str = "qwen3.5:9b"):
        """Lazy-load the Ollama context generator for contextual retrieval."""
        if self._context_generator is None:
            from pyqmd.indexing.contextual import OllamaContextGenerator
            gen = OllamaContextGenerator(model=model)
            if gen.is_available():
                self._context_generator = gen
            else:
                from rich.console import Console
                Console().print("[yellow]Ollama not available — indexing without contextual retrieval.[/yellow]")
        return self._context_generator

    def _get_hyde_generator(self, model: str = "qwen3.5:9b"):
        """Lazy-load the HyDE generator for query-time expansion."""
        if self._hyde_generator is None:
            from pyqmd.retrieval.hyde import HyDEGenerator
            gen = HyDEGenerator(model=model)
            if gen.is_available():
                self._hyde_generator = gen
        return self._hyde_generator

    def add_collection(
        self,
        name: str,
        paths: list[str],
        mask: str = "**/*.md",
    ) -> Collection:
        """Add a new collection and persist the config.

        Args:
            name: Unique collection name.
            paths: List of directory paths to index.
            mask: Glob mask for file selection.

        Returns:
            The created Collection object.

        Raises:
            ValueError: If a collection with the given name already exists.
        """
        collection = self.config.add_collection(name, paths=paths, mask=mask)
        self.config.save()
        return collection

    def remove_collection(self, name: str) -> None:
        """Remove a collection and its indexed data.

        Args:
            name: Collection name to remove.

        Raises:
            KeyError: If the collection does not exist.
        """
        self.config.remove_collection(name)
        self.config.save()
        self._storage.delete_collection(name)

    def list_collections(self) -> list[str]:
        """Return list of configured collection names."""
        return list(self.config.collections.keys())

    def index(
        self,
        collection_name: str | None = None,
        force: bool = False,
        contextual: bool = False,
        observer=None,
    ) -> int:
        """Index one or all collections.

        Args:
            collection_name: Name of the collection to index, or None to index all.
            force: If True, re-index all files even if unchanged.
            contextual: If True, generate context prefixes via Ollama before embedding.

        Returns:
            Total number of chunks indexed.
        """
        if collection_name is not None:
            return self._index_one(collection_name, force=force, contextual=contextual, observer=observer)
        total = 0
        for name in self.config.collections:
            total += self._index_one(name, force=force, contextual=contextual, observer=observer)
        return total

    def _index_one(self, collection_name: str, force: bool = False, contextual: bool = False, observer=None) -> int:
        """Index a single collection."""
        col = self.config.collections.get(collection_name)
        if col is None:
            raise KeyError(f"Collection '{collection_name}' not found")

        pipeline = self._get_indexing_pipeline(collection_name, contextual=contextual, observer=observer)
        total = 0
        for path_str in col.paths:
            directory = pathlib.Path(path_str)
            if directory.is_dir():
                total += pipeline.index_directory(
                    directory,
                    collection=collection_name,
                    mask=col.mask,
                    force=force,
                )
            elif directory.is_file():
                total += pipeline.index_file(directory, collection=collection_name, force=force)
        return total

    def search(
        self,
        query: str,
        collections: list[str] | None = None,
        top_k: int = 10,
        rerank: bool = False,
        expand_parent: bool = False,
        hyde: bool = False,
    ) -> list[SearchResult]:
        """Search across collections.

        Args:
            query: Search query string.
            collections: List of collection names to search, or None to search all.
            top_k: Maximum number of results to return.
            rerank: Whether to apply cross-encoder reranking.
            expand_parent: Whether to expand results to parent chunks.

        Returns:
            List of SearchResult objects sorted by descending score.
        """
        if collections is None:
            collections = self.list_collections()

        # Filter to collections that actually exist in storage
        valid_collections = [
            c for c in collections
            if c in (self._storage.list_collections() + list(self.config.collections.keys()))
        ]

        if not valid_collections:
            return []

        reranker = self._get_reranker() if rerank else None
        hyde_gen = self._get_hyde_generator() if hyde else None
        pipeline = RetrievalPipeline(
            storage=self._storage,
            embedder=self._embedder,
            reranker=reranker,
            hyde_generator=hyde_gen,
        )
        return pipeline.search(
            query,
            collections=valid_collections,
            top_k=top_k,
            rerank=rerank,
            expand_parent=expand_parent,
            hyde=hyde,
        )

    def status(self, collection_name: str) -> dict:
        """Return status information for a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Dict with keys: name, chunk_count, paths, mask, embed_model.

        Raises:
            KeyError: If the collection does not exist.
        """
        col = self.config.collections.get(collection_name)
        if col is None:
            raise KeyError(f"Collection '{collection_name}' not found")

        chunk_count = self._storage.count(collection_name)
        return {
            "name": collection_name,
            "chunk_count": chunk_count,
            "paths": col.paths,
            "mask": col.mask,
            "embed_model": col.config.embed_model,
        }
