"""YAML frontmatter parser for markdown files."""

import yaml


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown string.

    Returns (metadata_dict, body_without_frontmatter).
    If no frontmatter is found, returns ({}, original_text).
    """
    if not text.startswith("---"):
        return {}, text

    end_idx = text.find("---", 3)
    if end_idx == -1:
        return {}, text

    frontmatter_str = text[3:end_idx].strip()
    body = text[end_idx + 3:].lstrip("\n")

    if not frontmatter_str:
        return {}, body

    try:
        metadata = yaml.safe_load(frontmatter_str)
        if not isinstance(metadata, dict):
            return {}, text
        for key, value in metadata.items():
            if hasattr(value, "isoformat"):
                metadata[key] = value.isoformat()
        return metadata, body
    except yaml.YAMLError:
        return {}, text
