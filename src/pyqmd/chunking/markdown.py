"""Markdown-aware chunker using break-point scoring."""

import hashlib
import pathlib

from pyqmd.chunking.frontmatter import parse_frontmatter
from pyqmd.chunking.scoring import (
    CODE_FENCE_PATTERN,
    HEADING_PATTERN,
    BreakPoint,
    score_line,
)
from pyqmd.models import Chunk


class MarkdownChunker:
    """Splits markdown files into chunks using break-point scoring.

    Respects document structure: never splits inside code blocks or tables,
    preserves heading hierarchy, and establishes parent-child relationships.
    """

    def __init__(self, target_size: int = 800, overlap: float = 0.15):
        self.target_size = target_size
        self.overlap = overlap

    def chunk_file(self, path: pathlib.Path, collection: str) -> list[Chunk]:
        """Parse and chunk a markdown file."""
        text = path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(text)
        return self._chunk_body(
            body=body,
            metadata=metadata,
            source_file=str(path),
            collection=collection,
        )

    def _chunk_body(
        self,
        body: str,
        metadata: dict,
        source_file: str,
        collection: str,
    ) -> list[Chunk]:
        lines = body.split("\n")
        segments = self._find_segments(lines)
        chunks = self._merge_segments(segments)

        result = []
        heading_chunks: dict[int, str] = {}

        for chunk_lines, start_line, end_line in chunks:
            content = "\n".join(chunk_lines).strip()
            if not content:
                continue

            heading_path = self._extract_heading_path(chunk_lines, lines, start_line)
            chunk_id = hashlib.sha256(
                f"{source_file}:{start_line}:{content}".encode()
            ).hexdigest()[:16]

            current_level = self._get_heading_level(chunk_lines)
            parent_id = None
            if current_level is not None:
                for level in range(current_level - 1, 0, -1):
                    if level in heading_chunks:
                        parent_id = heading_chunks[level]
                        break
                heading_chunks[current_level] = chunk_id
                for level in list(heading_chunks.keys()):
                    if level > current_level:
                        del heading_chunks[level]
            elif heading_chunks:
                parent_id = heading_chunks[max(heading_chunks.keys())]

            chunk = Chunk(
                id=chunk_id,
                content=content,
                context=None,
                source_file=source_file,
                collection=collection,
                heading_path=heading_path,
                parent_id=parent_id,
                start_line=start_line,
                end_line=end_line,
                metadata=dict(metadata),
            )
            result.append(chunk)

        return result

    def _find_segments(self, lines: list[str]) -> list[tuple[list[str], int, int, int]]:
        """Find natural segments with their break scores."""
        segments: list[tuple[list[str], int, int, int]] = []
        current_lines: list[str] = []
        current_start = 0
        in_code_block = False
        prev_line = ""

        for i, line in enumerate(lines):
            stripped = line.strip()

            if CODE_FENCE_PATTERN.match(stripped):
                if in_code_block:
                    current_lines.append(line)
                    in_code_block = False
                    prev_line = line
                    continue
                else:
                    in_code_block = True
                    current_lines.append(line)
                    prev_line = line
                    continue

            if in_code_block:
                current_lines.append(line)
                prev_line = line
                continue

            bp = score_line(line, prev_line, in_code_block=False)
            if bp is not None and bp.score >= 50 and current_lines:
                segments.append((
                    current_lines,
                    current_start,
                    i - 1,
                    bp.score,
                ))
                current_lines = [line]
                current_start = i
            else:
                current_lines.append(line)

            prev_line = line

        if current_lines:
            segments.append((current_lines, current_start, len(lines) - 1, 0))

        return segments

    def _merge_segments(
        self, segments: list[tuple[list[str], int, int, int]]
    ) -> list[tuple[list[str], int, int]]:
        """Merge small segments together until they approach target_size."""
        if not segments:
            return []

        merged: list[tuple[list[str], int, int]] = []
        current_lines: list[str] = []
        current_start = 0
        current_size = 0

        for seg_lines, start, end, break_score in segments:
            seg_size = sum(len(line) for line in seg_lines)

            if current_size == 0:
                current_lines = list(seg_lines)
                current_start = start
                current_size = seg_size
                continue

            combined_size = current_size + seg_size
            if (combined_size > self.target_size and current_size > self.target_size * 0.3) or \
               (break_score >= 90 and current_size > self.target_size * 0.3):
                merged.append((current_lines, current_start, start - 1))
                current_lines = list(seg_lines)
                current_start = start
                current_size = seg_size
            else:
                current_lines.extend(seg_lines)
                current_size = combined_size

        if current_lines:
            last_end = segments[-1][2] if segments else 0
            merged.append((current_lines, current_start, last_end))

        if self.overlap > 0 and len(merged) > 1:
            merged = self._apply_overlap(merged)

        return merged

    def _apply_overlap(
        self, chunks: list[tuple[list[str], int, int]]
    ) -> list[tuple[list[str], int, int]]:
        """Add overlap between adjacent chunks."""
        result = []
        for i, (chunk_lines, start, end) in enumerate(chunks):
            if i > 0:
                prev_lines = chunks[i - 1][0]
                overlap_count = max(1, int(len(prev_lines) * self.overlap))
                overlap_lines = prev_lines[-overlap_count:]
                new_lines = overlap_lines + chunk_lines
                new_start = max(0, start - overlap_count)
                result.append((new_lines, new_start, end))
            else:
                result.append((chunk_lines, start, end))
        return result

    def _extract_heading_path(
        self, chunk_lines: list[str], all_lines: list[str], start_line: int
    ) -> list[str]:
        """Extract the heading hierarchy for a chunk by scanning backwards."""
        path: list[str] = []
        seen_levels: set[int] = set()

        for line in chunk_lines:
            match = HEADING_PATTERN.match(line)
            if match:
                level = len(match.group(1))
                title = line[match.end():].strip()
                if level not in seen_levels:
                    path.append(title)
                    seen_levels.add(level)

        for i in range(start_line - 1, -1, -1):
            match = HEADING_PATTERN.match(all_lines[i])
            if match:
                level = len(match.group(1))
                if level not in seen_levels and (not seen_levels or level < min(seen_levels)):
                    title = all_lines[i][match.end():].strip()
                    path.insert(0, title)
                    seen_levels.add(level)

        return path

    def _get_heading_level(self, chunk_lines: list[str]) -> int | None:
        """Get the heading level if this chunk starts with a heading."""
        for line in chunk_lines:
            stripped = line.strip()
            if not stripped:
                continue
            match = HEADING_PATTERN.match(stripped)
            if match:
                return len(match.group(1))
            return None
        return None
