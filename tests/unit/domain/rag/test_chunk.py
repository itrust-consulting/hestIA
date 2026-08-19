from __future__ import annotations

import uuid

import pytest

from hestia.domain.rag.chunk import (
    BlockSplitter, Chunk, SectionSplitter, _pack_blocks, _split_typed_blocks,
)


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

    def test_section_mixing_prose_and_table_splits_by_type(self):
        table = "| Item | Qty |\n|------|-----|\n| Widget | 3 |"
        text = f"# Prices\nIntro line.\n\n{table}\n\nOutro line."
        chunks = SectionSplitter().split(text)

        assert [c["block_type"] for c in chunks] == ["prose", "table", "prose"]
        assert all(c["header"] == "Prices" for c in chunks)
        assert len({c["path"] for c in chunks}) == 1
        assert [c["part"] for c in chunks] == [0, 1, 2]

    def test_oversized_table_in_section_splits_by_rows(self):
        header, sep = "| Col1 | Col2 |", "|------|------|"
        rows = [f"| r{i} | v{i} |" for i in range(10)]
        table = "\n".join([header, sep, *rows])
        text = f"# Data\n{table}"

        chunks = SectionSplitter(max_chars=60).split(text)

        assert len(chunks) > 1
        assert all(c["block_type"] == "table" for c in chunks)
        for c in chunks:
            assert c["content"].startswith(header)
            assert sep in c["content"]
        all_content = "\n".join(c["content"] for c in chunks)
        for row in rows:
            assert row in all_content

    def test_plain_prose_section_has_no_part_key_and_verbatim_content(self):
        text = "# Intro\nLine one\n\n\nLine two"
        chunks = SectionSplitter().split(text)

        assert len(chunks) == 1
        assert "part" not in chunks[0]
        assert chunks[0]["content"] == "Line one\n\n\nLine two"
        assert chunks[0]["block_type"] == "prose"

    def test_fenced_code_block_with_internal_blank_line_survives(self):
        text = "# Snippet\n```\nline1\n\nline2\n```"
        chunks = SectionSplitter().split(text)

        assert len(chunks) == 1
        assert chunks[0]["content"] == "```\nline1\n\nline2\n```"

    def test_pure_table_section_is_typed(self):
        text = "## Sheet1\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        chunks = SectionSplitter().split(text)

        assert len(chunks) == 1
        assert chunks[0]["block_type"] == "table"
        assert "part" not in chunks[0]


# ---------------------------------------------------------------------------
# _pack_blocks — shared prose-packing helper used by both splitters
# ---------------------------------------------------------------------------

class TestPackBlocks:

    def test_single_small_block_stays_single(self):
        parts = _pack_blocks(["Hello world"], 1000)
        assert len(parts) == 1

    def test_packs_until_max_chars(self):
        parts = _pack_blocks(["A" * 10, "B" * 10], 20)
        assert len(parts) == 2

    def test_hard_cuts_oversized_block(self):
        parts = _pack_blocks(["ABCDEFGHIJ"], 5)
        assert all(len(p) <= 5 for p in parts)
        assert "".join(parts) == "ABCDEFGHIJ"


# ---------------------------------------------------------------------------
# _split_typed_blocks — shared prose/table differentiation, used within a
# SectionSplitter section and across a whole BlockSplitter document
# ---------------------------------------------------------------------------

class TestSplitTypedBlocks:

    _TABLE = "| Item | Qty |\n|------|-----|\n| Widget | 3 |"

    def test_empty_returns_empty(self):
        assert _split_typed_blocks("", 100) == []

    def test_splits_on_blank_lines(self):
        units = _split_typed_blocks("A" * 10 + "\n\n" + "B" * 10, 15)
        assert all(u.block_type == "prose" for u in units)
        assert sum(len(u.parts) for u in units) == 2

    def test_prose_and_table_separated(self):
        text = f"Intro text.\n\n{self._TABLE}\n\nOutro text."
        units = _split_typed_blocks(text, 1000)
        assert [u.block_type for u in units] == ["prose", "table", "prose"]

    def test_consecutive_prose_blocks_merge_into_one_unit(self):
        units = _split_typed_blocks("First.\n\nSecond.", 1000)
        assert len(units) == 1
        assert units[0].block_type == "prose"
        assert len(units[0].parts) == 1

    def test_oversized_table_yields_multiple_parts(self):
        header, sep = "| Col1 | Col2 |", "|------|------|"
        rows = [f"| r{i} | v{i} |" for i in range(10)]
        table = "\n".join([header, sep, *rows])

        units = _split_typed_blocks(table, 60)

        assert len(units) == 1
        assert units[0].block_type == "table"
        assert len(units[0].parts) > 1
        assert all(p.startswith(header) for p in units[0].parts)

    def test_leading_blank_line_in_table_block_not_corrupted(self):
        block = "   \n" + self._TABLE
        units = _split_typed_blocks(block, 1000)
        assert units[0].block_type == "table"
        assert units[0].parts[0].startswith("| Item | Qty |")


# ---------------------------------------------------------------------------
# BlockSplitter.split — fallback strategy for heading-less documents
# ---------------------------------------------------------------------------

class TestBlockSplitter:

    _TABLE = "| Item | Qty |\n|------|-----|\n| Widget | 3 |"

    def test_empty_text_returns_empty(self):
        assert BlockSplitter().split("") == []

    def test_plain_prose_single_chunk(self):
        text = "Dear Sir,\n\nThank you for your letter."
        chunks = BlockSplitter(max_chars=1000).split(text)
        assert len(chunks) == 1
        assert chunks[0]["block_type"] == "prose"
        assert "Dear Sir" in chunks[0]["content"]

    def test_packs_prose_blocks_up_to_max_chars(self):
        text = "AAAAAAAAAA\n\nBBBBBBBBBB"
        chunks = BlockSplitter(max_chars=15).split(text)
        assert len(chunks) == 2
        assert all(c["block_type"] == "prose" for c in chunks)

    def test_small_table_stays_intact(self):
        chunks = BlockSplitter(max_chars=1000).split(self._TABLE)
        assert len(chunks) == 1
        assert chunks[0]["block_type"] == "table"
        assert "| Widget | 3 |" in chunks[0]["content"]

    def test_oversized_table_splits_by_rows_with_repeated_header(self):
        header, sep = "| Col1 | Col2 |", "|------|------|"
        rows = [f"| r{i} | v{i} |" for i in range(10)]
        table = "\n".join([header, sep, *rows])

        chunks = BlockSplitter(max_chars=60).split(table)

        assert len(chunks) > 1
        assert all(c["block_type"] == "table" for c in chunks)
        for c in chunks:
            assert c["content"].startswith(header)
            assert sep in c["content"]
        all_content = "\n".join(c["content"] for c in chunks)
        for row in rows:
            assert row in all_content

    def test_mixed_prose_and_table_content_ordered(self):
        text = (
            "Dear Customer,\n\nPlease find your invoice below.\n\n"
            f"{self._TABLE}\n\nThank you for your business."
        )
        chunks = BlockSplitter(max_chars=1000).split(text)

        assert [c["block_type"] for c in chunks] == ["prose", "table", "prose"]
        positions = [c["position"] for c in chunks]
        assert positions == list(range(len(chunks)))

    def test_all_chunks_have_nonempty_header_and_path(self):
        text = f"Some prose.\n\n{self._TABLE}\n\nMore prose."
        chunks = BlockSplitter(max_chars=1000).split(text)
        assert chunks
        assert all(c["header"] and c["path"] for c in chunks)
