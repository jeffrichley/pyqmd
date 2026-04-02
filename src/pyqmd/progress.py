"""Progress observer for pyqmd operations.

Pipelines emit events to an observer. The default observer does nothing.
The RichProgressObserver renders Rich progress bars. Consumers can implement
their own observers for logging, JSON output, etc.
"""

from typing import Protocol


class ProgressObserver(Protocol):
    """Protocol for observing progress of pyqmd operations."""

    def on_start(self, operation: str, total: int) -> None:
        """Called when an operation begins."""
        ...

    def on_advance(self, count: int = 1) -> None:
        """Called when progress advances."""
        ...

    def on_message(self, message: str) -> None:
        """Called for status messages."""
        ...

    def on_complete(self, operation: str, total: int) -> None:
        """Called when an operation finishes."""
        ...


class SilentObserver:
    """Default observer that does nothing."""

    def on_start(self, operation: str, total: int) -> None:
        pass

    def on_advance(self, count: int = 1) -> None:
        pass

    def on_message(self, message: str) -> None:
        pass

    def on_complete(self, operation: str, total: int) -> None:
        pass


class RichProgressObserver:
    """Observer that renders Rich progress bars.

    Each on_start/on_complete cycle shows a single progress bar that
    disappears when done, replaced by a one-line summary.
    """

    def __init__(self):
        from rich.console import Console
        self._console = Console()
        self._progress = None
        self._task_id = None

    def _make_progress(self):
        from rich.progress import (
            Progress, SpinnerColumn, TextColumn, BarColumn,
            MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn,
        )
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._console,
            transient=True,  # progress bar disappears when done
        )

    def on_start(self, operation: str, total: int) -> None:
        self._progress = self._make_progress()
        self._progress.start()
        self._task_id = self._progress.add_task(operation, total=total)

    def on_advance(self, count: int = 1) -> None:
        if self._task_id is not None and self._progress is not None:
            self._progress.advance(self._task_id, count)

    def on_message(self, message: str) -> None:
        self._console.print(message)

    def on_complete(self, operation: str, total: int) -> None:
        if self._progress is not None and self._progress.live.is_started:
            self._progress.stop()
        self._console.print(f"  [green]{operation}[/green] — {total}")
        self._progress = None
        self._task_id = None
