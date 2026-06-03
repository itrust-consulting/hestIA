from __future__ import annotations

import uuid

import pytest

from hestia.domain.rag.chunk import Chunk, SectionSplitter


# ---------------------------------------------------------------------------
# Chunk.to_payload
# ---------------------------------------------------------------------------

class TestChunkToPayload:

    def _make_chunk(self, **overrides):
        defaults = dict(
            content="Some content",
            source="doc",
            source_uri="doc.pdf",
            info={"header": "Intro", "path": "Intro", "level": 1, "position": 0},
            doc_info={"title": "Doc", "version": "1.0"},
            access={"classification": None},
        )
        defaults.update(overrides)
        return Chunk(**defaults)

    def test_contains_required_fields(self):
        chunk = self._make_chunk()
        payload = chunk.to_payload()
        for key in ("id", "content", "source", "source_uri", "info", "doc_info", "access"):
            assert key in payload

    def test_id_is_string(self):
        chunk = self._make_chunk()
        payload = chunk.to_payload()
        assert isinstance(payload["id"], str)

    def test_previous_serialized_as_string(self):
        prev = uuid.uuid4()
        chunk = self._make_chunk(previous=prev)
        payload = chunk.to_payload()
        assert payload["previous"] == str(prev)

    def test_none_previous_stays_none(self):
        chunk = self._make_chunk(previous=None)
        assert chunk.to_payload()["previous"] is None

    def test_next_serialized_as_string(self):
        nxt = uuid.uuid4()
        chunk = self._make_chunk(next=nxt)
        assert chunk.to_payload()["next"] == str(nxt)


# ---------------------------------------------------------------------------
# SectionSplitter.__init__
# ---------------------------------------------------------------------------

class TestSectionSplitterInit:

    def test_rejects_depth_zero(self):
        with pytest.raises(ValueError):
            SectionSplitter(max_depth=0)

    def test_rejects_depth_seven(self):
        with pytest.raises(ValueError):
            SectionSplitter(max_depth=7)

    def test_accepts_depth_one(self):
        s = SectionSplitter(max_depth=1)
        assert s._max_depth == 1

    def test_accepts_depth_six(self):
        s = SectionSplitter(max_depth=6)
        assert s._max_depth == 6


# ---------------------------------------------------------------------------
# SectionSplitter.split
# ---------------------------------------------------------------------------

class TestSectionSplitterSplit:

    def test_empty_text_returns_empty(self):
        assert SectionSplitter().split("") == []

    def test_splits_on_h1(self):
        text = "# Section A\nContent A\n# Section B\nContent B"
        sections = SectionSplitter().split(text)
        assert len(sections) == 2
        assert sections[0]["header"] == "Section A"
        assert sections[1]["header"] == "Section B"

    def test_drops_empty_sections(self):
        text = "# Header\n\n# NonEmpty\nsome text"
        sections = SectionSplitter().split(text)
        assert len(sections) == 1
        assert sections[0]["header"] == "NonEmpty"

    def test_respects_max_depth(self):
        text = "# H1\ncontent\n## H2\ncontent2\n### H3\ncontent3"
        sections = SectionSplitter(max_depth=2).split(text)
        headers = [s["header"] for s in sections]
        assert "H3" not in headers
        assert "H2" in headers

    def test_content_included_in_section(self):
        text = "# Intro\nHello world"
        sections = SectionSplitter().split(text)
        assert "Hello world" in sections[0]["content"]

    def test_path_reflects_heading_ancestry(self):
        text = "# Parent\ncontent\n## Child\nchild content"
        sections = SectionSplitter().split(text)
        child = next(s for s in sections if s["header"] == "Child")
        assert "Parent" in child["path"]


# ---------------------------------------------------------------------------
# SectionSplitter._split_paragraphs
# ---------------------------------------------------------------------------

class TestSplitParagraphs:

    def test_single_small_paragraph_stays_single(self):
        splitter = SectionSplitter(max_chars=1000)
        parts = splitter._split_paragraphs("Hello world")
        assert len(parts) == 1

    def test_splits_on_double_newline(self):
        splitter = SectionSplitter(max_chars=20)
        text = "AAAAAAAAAA\n\nBBBBBBBBBB"
        parts = splitter._split_paragraphs(text)
        assert len(parts) == 2

    def test_hard_cuts_oversized_paragraph(self):
        splitter = SectionSplitter(max_chars=5)
        text = "ABCDEFGHIJ"
        parts = splitter._split_paragraphs(text)
        assert all(len(p) <= 5 for p in parts)
        assert "".join(parts) == text
