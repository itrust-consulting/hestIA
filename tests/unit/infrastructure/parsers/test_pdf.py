from __future__ import annotations

import pathlib
import pytest

PDF_FILE = pathlib.Path(__file__).parents[4] / "tests" / "test_inputs" / "Test-Document.pdf"
PDF_ITR = pathlib.Path(__file__).parents[4] / "tests" / "test_inputs" / "Test-Document-ITR.pdf"

skip_if_missing = pytest.mark.skipif(not PDF_FILE.exists(), reason="Test PDF not found")
skip_if_itr_missing = pytest.mark.skipif(not PDF_ITR.exists(), reason="ITR PDF not found")

from hestia.infrastructure.parsers.pdf import PDFParser, ITRPDFParser


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


@skip_if_itr_missing
class TestITRPDFParser:

    @pytest.fixture(scope="class")
    def parser(self):
        p = ITRPDFParser(file=str(PDF_ITR))
        yield p
        p.close()

    def test_loads_without_error(self, parser):
        assert parser.doc is not None

    def test_metadata_returned(self, parser):
        meta = parser.get_metadata(builtIn_only=False)
        assert isinstance(meta, dict)

    def test_to_markdown_non_empty(self, parser):
        md = parser.to_markdown()
        assert len(md) > 0
