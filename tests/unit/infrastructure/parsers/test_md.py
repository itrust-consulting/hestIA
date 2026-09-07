from __future__ import annotations

import pytest

from hestia.infrastructure.parsers.md import MarkdownParser


@pytest.fixture
def md_file(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("---\ntitle: My Document\nauthor: Bob\n---\n# Intro\n\nHello world.\n")
    return f


@pytest.fixture
def md_no_frontmatter(tmp_path):
    f = tmp_path / "plain.md"
    f.write_text("# Just a heading\n\nSome text.\n")
    return f


class TestMarkdownParser:

    def test_loads_without_error(self, md_file):
        p = MarkdownParser(file=str(md_file))
        assert p.doc is not None

    def test_extracts_frontmatter_title(self, md_file):
        p = MarkdownParser(file=str(md_file))
        meta = p.get_metadata()
        assert meta["title"] == "My Document"

    def test_extracts_frontmatter_author(self, md_file):
        p = MarkdownParser(file=str(md_file))
        meta = p.get_metadata()
        assert meta["author"] == "Bob"

    def test_source_uri_set(self, md_file):
        p = MarkdownParser(file=str(md_file))
        meta = p.get_metadata()
        assert meta["source_uri"] == str(md_file)

    def test_to_markdown_returns_body_without_frontmatter(self, md_file):
        p = MarkdownParser(file=str(md_file))
        body = p.to_markdown()
        assert "# Intro" in body
        assert "title:" not in body

    def test_no_frontmatter_metadata_has_only_source(self, md_no_frontmatter):
        p = MarkdownParser(file=str(md_no_frontmatter))
        meta = p.get_metadata()
        assert "source" in meta
        assert "title" not in meta

    def test_no_frontmatter_body_returned(self, md_no_frontmatter):
        p = MarkdownParser(file=str(md_no_frontmatter))
        body = p.to_markdown()
        assert "Just a heading" in body

    def test_get_metadata_applies_mask(self, md_file):
        p = MarkdownParser(file=str(md_file))
        meta = p.get_metadata(mask_name="rag_default")
        assert "title" in meta


class TestMarkdownParserEmptyDoc:

    def test_to_markdown_raises_when_doc_is_none(self):
        from hestia.domain.exceptions import ValidationError
        p = MarkdownParser.__new__(MarkdownParser)
        p.doc = None
        with pytest.raises(ValidationError, match="Empty document"):
            p.to_markdown()
