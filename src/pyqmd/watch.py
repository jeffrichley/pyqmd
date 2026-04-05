"""File watcher for automatic re-indexing on changes."""

from __future__ import annotations

import fnmatch
import logging
import pathlib
import signal
import sys
import threading
import time
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class WatchService:
    """Watches a collection directory and auto-indexes on file changes.

    Supports dual-mode detection:
    - Filesystem events via watchdog (default, instant)
    - Polling via FileHashRegistry (optional, catches edge cases)
    """

    def __init__(
        self,
        collection_name: str,
        directory: pathlib.Path,
        mask: str,
        index_fn: Callable,
        poll_fn: Callable | None = None,
        debounce: float = 2.0,
        poll_interval: float = 0.0,
        ignore_patterns: list[str] | None = None,
    ):
        self.collection_name = collection_name
        self.directory = directory
        self.mask = mask
        self.index_fn = index_fn
        self.poll_fn = poll_fn
        self.debounce = debounce
        self.poll_interval = poll_interval
        self.ignore_patterns = ignore_patterns or [
            ".obsidian/", ".git/", "*.lock", "*.tmp", "~*"
        ]

        self._pending: set[pathlib.Path] = set()
        self._pending_deletes: set[pathlib.Path] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._running = False

    def _should_ignore(self, path: pathlib.Path) -> bool:
        """Check if a path matches any ignore pattern."""
        path_str = str(path)
        name = path.name
        for pattern in self.ignore_patterns:
            # Directory pattern (ends with /)
            if pattern.endswith("/"):
                dir_name = pattern.rstrip("/")
                if dir_name in pathlib.Path(path_str).parts:
                    return True
            # Glob pattern
            elif fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _add_pending(self, path: pathlib.Path) -> None:
        """Add a file to the pending set for batch re-indexing."""
        self._pending.add(path)

    def _add_pending_delete(self, path: pathlib.Path) -> None:
        """Add a file to the pending deletes set."""
        self._pending_deletes.add(path)

    def _schedule_flush(self) -> None:
        """Schedule a debounced flush of pending files."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        """Process all pending file changes."""
        with self._lock:
            pending = set(self._pending)
            pending_deletes = set(self._pending_deletes)
            self._pending.clear()
            self._pending_deletes.clear()

        if pending_deletes:
            for path in pending_deletes:
                logger.info("Deleted: %s", path)

        if pending:
            file_list = sorted(pending)
            logger.info(
                "Re-indexing %d file(s) in '%s': %s",
                len(file_list),
                self.collection_name,
                ", ".join(p.name for p in file_list),
            )
            try:
                count = self.index_fn(file_list)
                logger.info("Indexed %d chunks.", count)
            except Exception:
                logger.exception("Error during re-indexing")

    def _poll_loop(self) -> None:
        """Periodic polling loop using FileHashRegistry."""
        while self._running:
            time.sleep(self.poll_interval)
            if not self._running:
                break
            try:
                if self.poll_fn:
                    changed = self.poll_fn()
                    if changed:
                        logger.info(
                            "Poll detected %d changed file(s).", len(changed)
                        )
                        with self._lock:
                            self._pending.update(changed)
                        self._schedule_flush()
            except Exception:
                logger.exception("Error during poll")

    def run(self) -> None:
        """Start watching. Blocks until SIGINT/SIGTERM."""
        self._running = True

        # Set up signal handlers for graceful shutdown
        def shutdown(signum, frame):
            logger.info("Shutting down watcher...")
            self._running = False

        signal.signal(signal.SIGINT, shutdown)
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, shutdown)

        # Start watchdog observer
        handler = _ChangeHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.directory), recursive=True)
        observer.start()
        logger.info(
            "Watching '%s' (%s) — debounce=%.1fs",
            self.collection_name,
            self.directory,
            self.debounce,
        )

        # Start poll thread if enabled
        poll_thread = None
        if self.poll_interval > 0 and self.poll_fn:
            poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            poll_thread.start()
            logger.info("Polling enabled — interval=%.1fs", self.poll_interval)

        try:
            while self._running:
                time.sleep(0.5)
        finally:
            observer.stop()
            observer.join()
            if self._timer:
                self._timer.cancel()
            logger.info("Watcher stopped.")


class _ChangeHandler(FileSystemEventHandler):
    """Watchdog event handler that feeds into WatchService."""

    def __init__(self, service: WatchService):
        self.service = service

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = pathlib.Path(event.src_path)

        if self.service._should_ignore(path):
            return

        # Only care about files matching the collection mask
        if not fnmatch.fnmatch(path.name, self.service.mask.split("/")[-1]):
            return

        if event.event_type == "deleted":
            self.service._add_pending_delete(path)
        else:
            self.service._add_pending(path)

        self.service._schedule_flush()
