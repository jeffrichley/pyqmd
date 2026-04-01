from pyqmd.chunking.frontmatter import parse_frontmatter


class TestFrontmatter:
    def test_parse_with_frontmatter(self):
        text = """---
title: "My Doc"
category: "notes"
tags: ["python", "ml"]
---

# Hello

Content here.
"""
        metadata, body = parse_frontmatter(text)
        assert metadata["title"] == "My Doc"
        assert metadata["category"] == "notes"
        assert metadata["tags"] == ["python", "ml"]
        assert body.strip().startswith("# Hello")

    def test_parse_without_frontmatter(self):
        text = "# Hello\n\nContent here."
        metadata, body = parse_frontmatter(text)
        assert metadata == {}
        assert body == text

    def test_parse_empty_frontmatter(self):
        text = "---\n---\n# Hello"
        metadata, body = parse_frontmatter(text)
        assert metadata == {} or metadata is None
        assert "# Hello" in body

    def test_parse_frontmatter_with_dates(self):
        text = """---
due_date: "2026-03-15"
created: 2026-01-01
---

Content.
"""
        metadata, body = parse_frontmatter(text)
        assert metadata["due_date"] == "2026-03-15"
        assert body.strip() == "Content."
