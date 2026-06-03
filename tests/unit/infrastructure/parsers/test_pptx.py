from __future__ import annotations

import io
import pytest
from pptx import Presentation
from pptx.util import Inches, Pt

from hestia.infrastructure.parsers.pptx import PPTXParser


def _make_pptx(tmp_path, slides=None):
    prs = Presentation()
    if slides is None:
        slides = [("Slide 1 Title", "Body text here")]
    for title_text, body_text in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title_text
        for ph in slide.placeholders:
            if ph.placeholder_format.idx == 1:
                ph.text = body_text
    path = tmp_path / "test.pptx"
    prs.save(str(path))
    return path


class TestPPTXParser:

    def test_loads_without_error(self, tmp_path):
        path = _make_pptx(tmp_path)
        p = PPTXParser(file=str(path))
        assert p.doc is not None

    def test_to_markdown_contains_title(self, tmp_path):
        path = _make_pptx(tmp_path, slides=[("My Slide", "Some content")])
        p = PPTXParser(file=str(path))
        md = p.to_markdown()
        assert "My Slide" in md

    def test_to_markdown_contains_body(self, tmp_path):
        path = _make_pptx(tmp_path, slides=[("Title", "Important body text")])
        p = PPTXParser(file=str(path))
        md = p.to_markdown()
        assert "Important body text" in md

    def test_multiple_slides(self, tmp_path):
        path = _make_pptx(tmp_path, slides=[
            ("Slide A", "Content A"),
            ("Slide B", "Content B"),
        ])
        p = PPTXParser(file=str(path))
        md = p.to_markdown()
        assert "Slide A" in md
        assert "Slide B" in md

    def test_metadata_has_source(self, tmp_path):
        path = _make_pptx(tmp_path)
        p = PPTXParser(file=str(path))
        meta = p.get_metadata()
        assert "source" in meta


class TestSlideTitleHelper:

    def test_returns_title_text(self, tmp_path):
        path = _make_pptx(tmp_path, slides=[("My Title", "Body")])
        p = PPTXParser(file=str(path))
        slide = p.doc.slides[0]
        assert p._slide_title(slide) == "My Title"

    def test_returns_empty_string_for_untitled_slide(self, tmp_path):
        from pptx import Presentation
        prs = Presentation()
        # Use a blank layout (no title placeholder)
        blank_layout = prs.slide_layouts[6]  # "Blank" layout
        prs.slides.add_slide(blank_layout)
        path = tmp_path / "blank.pptx"
        prs.save(str(path))

        p = PPTXParser(file=str(path))
        slide = p.doc.slides[0]
        result = p._slide_title(slide)
        assert result == ""
