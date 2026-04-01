"""Break-point scoring algorithm for markdown chunking."""

import re
from dataclasses import dataclass


BREAK_SCORES: dict[str, int] = {
    "h1": 100,
    "h2": 90,
    "h3": 80,
    "h4": 70,
    "code_block_end": 85,
    "hr": 75,
    "blank_line": 50,
    "list_end": 45,
    "blockquote_end": 40,
}

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+")
HR_PATTERN = re.compile(r"^(-{3,}|_{3,}|\*{3,})\s*$")
CODE_FENCE_PATTERN = re.compile(r"^(`{3,}|~{3,})")


@dataclass
class BreakPoint:
    """A potential break point in a markdown document."""

    score: int
    break_type: str
    line_number: int = 0


def score_line(
    line: str, prev_line: str, in_code_block: bool
) -> BreakPoint | None:
    """Score a line as a potential break point.

    Returns a BreakPoint if the line is a viable break point, None otherwise.
    Lines inside code blocks are never break points (except the closing fence).
    """
    stripped = line.strip()

    # Code block fence (closing)
    if in_code_block:
        if CODE_FENCE_PATTERN.match(stripped):
            return BreakPoint(
                score=BREAK_SCORES["code_block_end"], break_type="code_block_end"
            )
        return None

    # Headings
    heading_match = HEADING_PATTERN.match(line)
    if heading_match:
        level = len(heading_match.group(1))
        if level <= 4:
            key = f"h{level}"
            return BreakPoint(score=BREAK_SCORES[key], break_type=key)
        return BreakPoint(score=60, break_type=f"h{level}")

    # Horizontal rule
    if HR_PATTERN.match(stripped) and stripped:
        return BreakPoint(score=BREAK_SCORES["hr"], break_type="hr")

    # Blank line
    if stripped == "":
        return BreakPoint(score=BREAK_SCORES["blank_line"], break_type="blank_line")

    return None
