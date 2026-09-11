from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pandas.api.types as pdt
from lxml import etree

from hestia.domain.exceptions import ValidationError
from hestia.infrastructure.parsers.base import BaseParser, MetadataFilter

_log = logging.getLogger("hestia.system")

_NAMESPACES = {
    "dcelem": "http://purl.org/dc/elements/1.1/",
    "dcterm": "http://purl.org/dc/terms/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
}


# @MRS-075
class XLSXParser(BaseParser):

    def __init__(self, file=None, selected_sheets: list[str] | None = None):
        self._selected_sheets = selected_sheets
        self._loader_map = {".xlsx": self._load_xlsx, ".xlsm": self._load_xlsx}
        super().__init__(file=file)

    def _load_xlsx(self, file) -> Dict[str, pd.DataFrame]:
        df = pd.read_excel(file, sheet_name=None, header=None)
        if self._selected_sheets:
            df = {k: v for k, v in df.items() if k in self._selected_sheets}
        for name, sheet in df.items():
            sheet = sheet.dropna(how="all").dropna(axis=1, how="all")
            sheet.columns = (
                sheet.columns
                .astype(str)
                .str.normalize("NFKC")
                .str.replace(r"[\r\n]+", " ", regex=True)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
            string_cols = [
                col for col in sheet.columns
                if pdt.is_string_dtype(sheet[col]) or pdt.is_object_dtype(sheet[col])
            ]
            for col in string_cols:
                sheet[col] = (
                    sheet[col]
                    .astype("string")
                    .str.replace(r"\s+", " ", regex=True)
                    .str.strip()
                )
            sheet = sheet.replace(to_replace=pd.NA, value="NaN")
            df[name] = sheet
        _log.debug("xlsx_loaded", extra={"file": str(file), "n_sheets": len(df)})
        return df

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_builtin_metadata(self) -> dict:
        metadata = {}
        with zipfile.ZipFile(self.filepath) as zf:
            xml_data = zf.read("docProps/core.xml")
            root = etree.fromstring(xml_data)
            for elem in root:
                tag = etree.QName(elem).localname
                metadata[self.normalize_key(tag)] = self.clean_string(elem.text or "")

            if "docProps/custom.xml" in zf.namelist():
                xml_data = zf.read("docProps/custom.xml")
                root = etree.fromstring(xml_data)
                for prop in root.findall("ep:property", _NAMESPACES):
                    name = prop.get("name")
                    val_elem = next(iter(prop), None)
                    val = self.clean_string(val_elem.text or "") if val_elem is not None else ""
                    metadata[self.normalize_key(name)] = val
        return metadata

    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        stem = Path(self.filepath).stem
        builtin = self.get_builtin_metadata()
        metadata = {**builtin, "source": stem, "source_uri": str(self.filepath)}

        if not builtIn_only:
            try:
                custom = self.get_metadata_from_cover_page()
                metadata = {**metadata, **custom}
            except (IndexError, KeyError, AttributeError, ValidationError) as e:
                _log.warning("cover_page_metadata_failed", extra={"file": self.filepath, "error": str(e)})

        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        return metadata

    def get_metadata_from_cover_page(self) -> dict:
        return {}

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        sheets = self.to_markdown_sheets()
        md = "\n\n".join(sheets.values())
        self.body = md
        _log.debug("xlsx_to_markdown", extra={"file": self.filepath, "n_sheets": len(sheets)})
        return md

    # @MRS-017
    def to_markdown_sheets(self) -> Dict[str, str]:
        if self.doc is None:
            raise ValidationError("Empty document. Parse a file first.")
        return {name: f"## {name}\n\n{sheet.to_markdown(index=False)}\n"
                for name, sheet in self.doc.items()}

    def to_csv(
        self,
        sheet_ids: int | List[int] | None = None,
        output_path: str | None = None,
    ) -> Dict[str, str]:
        if self.doc is None:
            raise ValidationError("Empty document. Parse a file first.")

        sheets_list = list(self.doc.items())
        if sheet_ids is None:
            indices = list(range(len(sheets_list)))
        elif isinstance(sheet_ids, int):
            indices = [sheet_ids]
        else:
            indices = list(sheet_ids)

        results = {}
        for idx in indices:
            name, sheet = sheets_list[idx]
            if output_path:
                file_path = f"{output_path.rstrip('/')}/{name}.csv"
                sheet.to_csv(file_path, index=False, encoding="utf-8")
                results[name] = file_path
            else:
                results[name] = sheet.to_csv(index=False)
        return results