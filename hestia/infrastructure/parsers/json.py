from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from hestia.domain.exceptions import ValidationError
from hestia.infrastructure.parsers.base import BaseParser, MetadataFilter

_log = logging.getLogger("hestia.system")

# Top-level keys treated as metadata when present in a JSON object.
_META_KEYS = {"title", "description", "author", "version", "lang", "source", "subject", "tags"}


# @MRS-075
class JSONParser(BaseParser):

    def __init__(self, file=None):
        self._loader_map = {".json": self._load_json}
        super().__init__(file=file)

    def _load_json(self, file) -> Any:
        with open(file, encoding="utf-8") as fh:
            data = json.load(fh)
        _log.debug("json_loaded", extra={"file": str(file)})
        return data

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        metadata: dict = {"source": stem, "source_uri": str(self.filepath)}

        if isinstance(self.doc, dict):
            for key in _META_KEYS:
                val = self.doc.get(key)
                if val is not None and val != "":
                    metadata[self.normalize_key(key)] = val

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        _log.debug("json_get_metadata", extra={"file": self.filepath, "keys": list(metadata.keys()), "mask": mask_name})
        return metadata

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        if self.doc is None:
            raise ValidationError("Empty document. Parse a file first.")

        if isinstance(self.doc, dict):
            md = self._dict_to_markdown(self.doc)
        elif isinstance(self.doc, list):
            md = "```json\n" + json.dumps(self.doc, indent=2, ensure_ascii=False) + "\n```"
        else:
            md = str(self.doc)

        self.body = md
        _log.debug("json_to_markdown", extra={"file": self.filepath})
        return md

    def _dict_to_markdown(self, data: dict) -> str:
        lines: list[str] = []
        for key, value in data.items():
            lines.append(f"## {key}")
            if isinstance(value, (dict, list)):
                lines.append("```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```")
            else:
                lines.append(str(value))
            lines.append("")
        return "\n".join(lines).rstrip()
