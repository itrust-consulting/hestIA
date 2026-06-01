from __future__ import annotations

import logging
from pathlib import Path

from hestia.domain.exceptions import ValidationError
from hestia.infrastructure.parsers.base import BaseParser, MetadataFilter

_log = logging.getLogger("hestia.system")


class TXTParser(BaseParser):

    def __init__(self, file=None):
        self._loader_map = {".txt": self._load_txt}
        super().__init__(file=file)

    def _load_txt(self, file) -> str:
        with open(file, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        _log.debug("txt_loaded", extra={"file": str(file), "chars": len(content)})
        return content

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        metadata: dict = {"source": stem, "source_uri": str(self.filepath)}

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        _log.debug("txt_get_metadata", extra={"file": self.filepath, "keys": list(metadata.keys()), "mask": mask_name})
        return metadata

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        if self.doc is None:
            raise ValidationError("Empty document. Parse a file first.")
        self.body = self.doc
        _log.debug("txt_to_markdown", extra={"file": self.filepath})
        return self.body
