from __future__ import annotations

import logging
import re
from pathlib import Path

import pymupdf
import pymupdf4llm

from hestia.infrastructure.parsers.base import BaseParser, MetadataFilter

_log = logging.getLogger("hestia.system")

# Image placeholder patterns emitted by pymupdf4llm
_IMG_PLACEHOLDER = re.compile(
    r"\*\*==> picture \[\d+ x \d+\] intentionally omitted <==\*\*"
)


# @MRS-007
class PDFParser(BaseParser):

    def __init__(self, file=None):
        self._loader_map = {".pdf": self._load_pdf}
        super().__init__(file=file)

    def _load_pdf(self, file):
        doc = pymupdf.open(file)
        _log.debug("pdf_loaded", extra={"file": str(file), "n_pages": doc.page_count})
        return doc

    def close(self) -> None:
        if self.doc is not None:
            self.doc.close()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_builtin_metadata(self) -> dict:
        metadata = {}
        for key, val in self.doc.metadata.items():
            metadata[self.normalize_key(key)] = self.clean_string(str(val) if val else "")
        return metadata

    # @MRS-013
    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        builtin = self.get_builtin_metadata()
        metadata = {**builtin, "source": stem, "source_uri": str(self.filepath)}

        if not builtIn_only:
            try:
                custom = self.get_metadata_from_cover_page()
                metadata = {**metadata, **custom}
            except (IndexError, KeyError, AttributeError) as e:
                _log.warning("cover_page_metadata_failed", extra={"file": self.filepath, "error": str(e)})

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        return metadata

    def get_metadata_from_cover_page(self) -> dict:
        cover = self.doc[0]
        tables = cover.find_tables().tables
        if not tables:
            return {}
        table_data = {}
        for row in tables[0].rows:
            cells = [self.clean_string(cover.get_text("text", clip=cell)) for cell in row.cells]
            if len(cells) >= 2 and cells[0]:
                table_data[self.normalize_key(cells[0])] = cells[1]
        return table_data

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_markdown(
        self,
        header: bool = False,
        footer: bool = False,
        ignore_graphics: bool = True,
        ignore_images: bool = True,
        **kwargs,
    ) -> str:
        md = pymupdf4llm.to_markdown(
            self.doc,
            header=header,
            footer=footer,
            ignore_graphics=ignore_graphics,
            ignore_images=ignore_images,
            **kwargs,
        )
        md = _IMG_PLACEHOLDER.sub("", md)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        self.body = md
        _log.debug("pdf_to_markdown", extra={"file": self.filepath, "length": len(md)})
        return md


class ITRPDFParser(PDFParser):
    """PDFParser extended for iTrust document templates (cover-page metadata)."""

    def __init__(self, file=None):
        super().__init__(file=file)

    # @MRS-013
    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        builtin = self.get_builtin_metadata()
        metadata = {**builtin, "source": stem, "source_uri": str(self.filepath)}

        if not builtIn_only:
            try:
                custom = self.get_metadata_from_cover_page()
                metadata = {**metadata, **custom}
            except (IndexError, KeyError, AttributeError) as e:
                _log.warning("cover_page_metadata_failed", extra={"file": self.filepath, "error": str(e)})

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        return metadata
