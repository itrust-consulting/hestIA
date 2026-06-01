from __future__ import annotations

import logging
from pathlib import Path

import frontmatter

from hestia.domain.exceptions import ValidationError
from hestia.infrastructure.parsers.base import BaseParser, MetadataFilter

_log = logging.getLogger("hestia.system")


class MarkdownParser(BaseParser):

    def __init__(self, file=None):
        self._loader_map = {".md": self._load_md, ".markdown": self._load_md}
        super().__init__(file=file)

    def _load_md(self, file) -> frontmatter.Post:
        with open(file, encoding="utf-8", errors="replace") as fh:
            post = frontmatter.load(fh)
        _log.debug("md_loaded", extra={"file": str(file), "has_frontmatter": bool(post.metadata)})
        return post

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        metadata: dict = {"source": stem, "source_uri": str(self.filepath)}

        if self.doc is not None and self.doc.metadata:
            for k, v in self.doc.metadata.items():
                metadata[self.normalize_key(k)] = v

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        _log.debug("md_get_metadata", extra={"file": self.filepath, "keys": list(metadata.keys()), "mask": mask_name})
        return metadata

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        if self.doc is None:
            raise ValidationError("Empty document. Parse a file first.")
        self.body = self.doc.content
        _log.debug("md_to_markdown", extra={"file": self.filepath})
        return self.body
