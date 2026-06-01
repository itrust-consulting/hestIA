from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pandas.api.types as pdt

from hestia.domain.exceptions import ValidationError
from hestia.infrastructure.parsers.base import BaseParser, MetadataFilter

_log = logging.getLogger("hestia.system")


class CSVParser(BaseParser):

    def __init__(self, file=None):
        self._loader_map = {".csv": self._load_csv}
        super().__init__(file=file)

    def _load_csv(self, file) -> pd.DataFrame:
        df = pd.read_csv(file, header=0)
        df = df.dropna(how="all").dropna(axis=1, how="all")
        df.columns = (
            df.columns
            .astype(str)
            .str.normalize("NFKC")
            .str.replace(r"[\r\n]+", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )
        string_cols = [
            col for col in df.columns
            if pdt.is_string_dtype(df[col]) or pdt.is_object_dtype(df[col])
        ]
        for col in string_cols:
            df[col] = (
                df[col]
                .astype("string")
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
        df = df.replace(to_replace=pd.NA, value="NaN")
        _log.debug("csv_loaded", extra={"file": str(file), "rows": len(df), "cols": len(df.columns)})
        return df

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        metadata: dict = {"source": stem, "source_uri": str(self.filepath)}

        if self.doc is not None:
            metadata["columns"] = list(self.doc.columns)
            metadata["row_count"] = len(self.doc)

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        _log.debug("csv_get_metadata", extra={"file": self.filepath, "keys": list(metadata.keys()), "mask": mask_name})
        return metadata

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        if self.doc is None:
            raise ValidationError("Empty document. Parse a file first.")

        md = self.doc.to_markdown(index=False)
        self.body = md
        _log.debug("csv_to_markdown", extra={"file": self.filepath, "rows": len(self.doc)})
        return md
