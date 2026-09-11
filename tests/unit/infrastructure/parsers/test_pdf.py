from __future__ import annotations

import pathlib
import pytest

PDF_FILE = pathlib.Path(__file__).parents[4] / "tests" / "test_inputs" / "Test-Document.pdf"

skip_if_missing = pytest.mark.skipif(not PDF_FILE.exists(), reason="Test PDF not found")

from hestia.infrastructure.parsers.pdf import PDFParser


@skip_if_missing
class TestPDFParser:

    @pytest.fixture(scope="class")
    def parser(self):
        p = PDFParser(file=str(PDF_FILE))
        yield p
        p.close()

    def test_loads_without_error(self, parser):
        assert parser.doc is not None

    def test_to_markdown_returns_text(self, parser):
        md = parser.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_metadata_has_source(self, parser):
        meta = parser.get_metadata()
        assert "source" in meta

    def test_close_does_not_raise(self):
        p = PDFParser(file=str(PDF_FILE))
        p.close()  # Should not raise

    def test_metadata_with_mask(self, parser):
        meta = parser.get_metadata(mask_name="rag_default")
        assert "source" in meta

    def test_metadata_builtin_only_false_no_cover_table(self, parser):
        # The plain test document has no cover-page table, so this exercises
        # the try branch of get_metadata_from_cover_page succeeding with {}.
        meta = parser.get_metadata(builtIn_only=False)
        assert "source" in meta

    def test_metadata_swallows_cover_page_errors(self, monkeypatch):
        p = PDFParser(file=str(PDF_FILE))
        try:
            def boom():
                raise AttributeError("no cover page")
            monkeypatch.setattr(p, "get_metadata_from_cover_page", boom)
            meta = p.get_metadata(builtIn_only=False)
            assert "source" in meta
        finally:
            p.close()


class TestPDFParserCloseNoDoc:

    def test_close_when_doc_is_none_is_a_noop(self):
        p = PDFParser.__new__(PDFParser)
        p.doc = None
        assert p.close() is None


class TestPDFParserCoverPageHelper:

    class _FakeRow:
        def __init__(self, cells):
            self.cells = cells

    class _FakeTable:
        def __init__(self, rows):
            self.rows = rows

    class _FakeTables:
        def __init__(self, tables):
            self.tables = tables

    class _FakePage:
        def __init__(self, tables, text_map):
            self._tables = tables
            self._text_map = text_map

        def find_tables(self):
            return TestPDFParserCoverPageHelper._FakeTables(self._tables)

        def get_text(self, kind, clip=None):
            return self._text_map.get(id(clip), "")

    def test_no_tables_returns_empty_dict(self):
        p = PDFParser.__new__(PDFParser)
        p.doc = [self._FakePage([], {})]
        result = p.get_metadata_from_cover_page()
        assert result == {}

    def test_skips_rows_with_too_few_or_empty_first_cell(self):
        cell_a, cell_b, cell_c, cell_d = object(), object(), object(), object()
        text_map = {
            id(cell_a): "Field",
            id(cell_b): "Value",
            id(cell_c): "",  # empty first cell -> row skipped
            id(cell_d): "Ignored",
        }
        row_valid = self._FakeRow([cell_a, cell_b])
        row_empty_first = self._FakeRow([cell_c, cell_d])
        row_single_cell = self._FakeRow([cell_a])
        table = self._FakeTable([row_valid, row_empty_first, row_single_cell])

        p = PDFParser.__new__(PDFParser)
        p.doc = [self._FakePage([table], text_map)]
        result = p.get_metadata_from_cover_page()
        assert result == {"field": "Value"}


@skip_if_missing
class TestPDFParserIgnoreImages:

    @pytest.fixture(scope="class")
    def parser(self):
        p = PDFParser(file=str(PDF_FILE))
        yield p
        p.close()

    def test_image_placeholder_absent_when_ignored(self, parser):
        md = parser.to_markdown(ignore_images=True)
        # pymupdf4llm uses markers like "![img-N.jpeg]" — should be absent
        assert "![" not in md
