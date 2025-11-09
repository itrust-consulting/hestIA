from abc import ABC, abstractmethod
from typing import Dict, List
import pymupdf
import pymupdf4llm
import frontmatter
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree
import zipfile
from pathlib import Path

import argparse


DUMP_DIR = "./dump"
SUPPPORTED_EXTENSIONS = [".docx", ".pdf"]


class BaseParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def __init__(self, file: str):
        self.filepath = file
        self.body = None # markdown body
        self.meta = {}

    def normalize_key(self, k: str):
        return k.lower().replace(" ", "_")

    def clean_string(self, text: str):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()
    
    def dump(self, output_path=None, builtIn_only=True):
        """Dump document as markdown with yaml frontmatter."""
        body = self.body or self.to_markdown()
        meta = self.meta or self.get_metadata(builtIn_only=builtIn_only)

        post = frontmatter.Post(content=body, **meta)
        if not output_path:
            # Extract just the filename without directories or extension
            filename = Path(self.filepath).stem
            dump_dir = Path(DUMP_DIR)
            dump_dir.mkdir(parents=True, exist_ok=True)  # ensure directory exists
            output_path = dump_dir / f"{filename}.md"

        with open(output_path, "wb") as file:
            frontmatter.dump(post, file)

    @abstractmethod
    def get_metadata(self, builtIn_only=True) -> str:
        """Get metadata from the document"""
        pass

    @abstractmethod
    def to_markdown(self) -> str:
        """Convert document to markdown"""
        pass

    
class PDFParser(BaseParser):

    def __init__(self, file):
        super().__init__(file)
        self.doc = pymupdf.open(file)

    def get_builtin_metadata(self):

        metadata = {}
        for key in self.doc.metadata.keys():
            metadata[self.normalize_key(key)] = self.clean_string(self.doc.metadata[key])
        return metadata

    def get_metadata_from_cover_page(self):

        cover_page = self.doc[0]
        # assuming the itr coverpage
        tables = cover_page.find_tables().tables
        if len(tables) < 1:
            return {}
        table = tables[0]
        table_data = {}
        for row in table.rows:
            # extract cleaned text for all cells
            _row = [self.clean_string(cover_page.get_text("text", clip=cell)) for cell in row.cells]
            # only assign if row has at least 2 cells and key non-empty
            if len(_row) >= 2 and _row[0]:
                table_data[self.normalize_key(_row[0])] = _row[1]
        return table_data

    def get_metadata(self, builtIn_only=True):
        # retrieve builtin document metadata, e.g., format, title, author, ...
        builtIn = self.get_builtin_metadata()        
        if builtIn_only:
            self.meta = builtIn
            return builtIn
        
        custom = self.get_metadata_from_cover_page()
        metadata = {**builtIn, **custom}
        # set meta
        self.meta = metadata
        return metadata

    def to_markdown(self, header=False, footer=False, ignore_graphics=True, ignore_images=True, **kwargs):
        # Generate Markdown from PDF
        md_text = pymupdf4llm.to_markdown(self.doc, header=header, footer=footer, 
                                          ignore_graphics=ignore_graphics, ignore_images=ignore_images,
                                          **kwargs)

        # Clean unwanted image placeholders
        md_text_clean = re.sub(r'\*\*==> picture \[\d+ x \d+\] intentionally omitted <==\*\*', '', md_text)
        md_text_clean = re.sub(r'\n{2,}', '\n\n', md_text_clean)

        self.body = md_text_clean
        return md_text_clean


class DOCXParser(BaseParser):

    NAMESPACES = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                  "dcelem": "http://purl.org/dc/elements/1.1/",
                  "dcterm": "http://purl.org/dc/terms/",
                  "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
                  "ep":"http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"}

    def __init__(self, file):
        """
        :param file: Path to a file.
        """
        super().__init__(file)
        self.doc = Document(file)
        self.style_levels = self.get_list_styles_from_styles_xml()

    def get_list_styles_from_styles_xml(self):
        """Return {styleId: ilvl} for list styles defined in styles.xml."""
        style_levels = {}
        with zipfile.ZipFile(self.filepath) as zf:
            if "word/styles.xml" not in zf.namelist():
                return style_levels
            xml_data = zf.read("word/styles.xml")
        root = etree.fromstring(xml_data)
        for style in root.findall("w:style", self.NAMESPACES):
            style_id = style.get("{%s}styleId" % self.NAMESPACES["w"])
            numpr = style.find(".//w:numPr", self.NAMESPACES)
            if numpr is not None:
                ilvl_elem = numpr.find("w:ilvl", self.NAMESPACES)
                ilvl = int(ilvl_elem.get("{%s}val" % self.NAMESPACES["w"])) if ilvl_elem is not None else 0
                style_levels[style_id] = ilvl
        return style_levels

    def get_list_level_from_paragraph(self, para: Paragraph, style_levels: dict):
        """Determine list nesting level from either style or inline numPr."""
        pPr = para._p.pPr
        if pPr is None:
            return None

        # 1. Built-in lists (inline numPr)
        if pPr.numPr is not None:
            ilvl = pPr.numPr.ilvl
            if ilvl is not None:
                return int(ilvl.val)

        # 2. Custom style-based lists
        if pPr.pStyle is not None:
            style_id = pPr.pStyle.val
            if style_id in style_levels:
                return style_levels[style_id]

        return None

    def para_to_markdown(self, para: Paragraph, style_levels: dict):
        text = para.text.strip()
        if not text:
            return ""

        style_name = para.style.name or ""

        # Headings
        if style_name.startswith("Heading"):
            level = int(style_name.split()[-1])
            return f"{'#' * level} {text}"

        # Handle lists (built-in or style-based)
        ilvl = self.get_list_level_from_paragraph(para, style_levels)
        if ilvl is not None:
            indent = "  " * ilvl
            return f"{indent}- {text}"
        
        # Normal paragraph
        return text

    def extract_table_text(self, table: Table):
        """Return table as list of rows of strings, extracting all w:t under w:tc."""
        rows = []
        for row in table.findall(".//w:tr", self.NAMESPACES):
            row_cells = []
            for cell in row.findall(".//w:tc", self.NAMESPACES):
                texts = [t.text for t in cell.findall(".//w:t", self.NAMESPACES) if t.text]
                row_cells.append("".join(texts).strip())
            rows.append(row_cells)
        return rows

    def table_to_markdown(self, table: Table):
        rows = self.extract_table_text(table._tbl)
        md_rows = ["| " + " | ".join(r) + " |" for r in rows]
        if rows:
            header_sep = "| " + " | ".join(["---"] * len(rows[0])) + " |"
            md_rows.insert(1, header_sep)
        md_table = "\n".join(md_rows)
        return md_table

    def get_builtin_metadata(self, docx: str) -> dict:
        """get document builtin metadata (core + custom)"""
        metadata = {}
        with zipfile.ZipFile(docx) as zf:
            """Extract core props first"""
            xml_data = zf.read("docProps/core.xml")
            root = etree.fromstring(xml_data)
            for elem in root:
                tag = etree.QName(elem).localname  # strip namespace
                metadata[self.normalize_key(tag)] = self.clean_string(elem.text)

            """Extract custom props"""
            if "docProps/custom.xml" in zf.namelist():
                xml_data = zf.read("docProps/custom.xml")
                root = etree.fromstring(xml_data)
                for prop in root.findall("ep:property", self.NAMESPACES):
                    name = prop.get("name")
                    val_elem = next(iter(prop))
                    metadata[self.normalize_key(name)] = self.clean_string(val_elem.text)
        return metadata

    def get_metadata_from_cover_page(self, docx: str) -> dict:
        doc = Document(docx)
        # assuming itr template
        if len(doc.tables) < 1:
            return {}
        table_data = doc.tables[1]._tbl
        data = self.extract_table_text(table_data)
        metadata = {k: v for k, v in data} 
        return metadata

    def get_metadata(self, builtIn_only=True):
        builtIn = self.get_builtin_metadata(self.filepath)
        if builtIn_only:
            self.meta = builtIn
            return builtIn
        custom = self.get_metadata_from_cover_page(self.filepath)
        metadata = {**builtIn, **custom}
        self.meta = metadata

        return metadata
    
    def to_markdown(self):

        lines=[]
        for body in self.doc.iter_inner_content():
            if isinstance(body, Paragraph):
                md = self.para_to_markdown(body, self.style_levels)
                if md:
                    lines.append(md)
            if isinstance(body, Table):
                md = self.table_to_markdown(body)
                if md:
                    lines.append(md)
        md_text = "\n\n".join(lines) 
        self.body = md_text

        return md_text


class MarkdownConverter:
    EXTENSION_MAP = {
        ".docx": DOCXParser,
        ".pdf": PDFParser
    }

    def __init__(self, path, recursive=False, pref_type=".docx"):
        """
        :param path: Path to a file or directory
        :param recursive: If True, traverse directories recursively
        :param pref_type: Preferred file type when both .docx and .pdf exist
        """
        self.path = Path(path)
        self.recursive = recursive
        self.pref_type = pref_type
        self.docs_to_convert = []

        self._collect_files()

    def _collect_files(self):
        if self.path.is_file():
            if self.path.suffix.lower() in SUPPPORTED_EXTENSIONS:
                self.docs_to_convert = [self.path]
        elif self.path.is_dir():
            pattern = "**/*" if self.recursive else "*"
            all_files = [f for f in self.path.glob(pattern) if f.suffix.lower() in SUPPPORTED_EXTENSIONS]

            # Index by stem to handle preference
            file_index = {}
            for file in all_files:
                stem = file.stem
                # if file already exists choose preferred file type
                if stem in file_index:
                    if file.suffix.lower() == self.pref_type:
                        file_index[stem] = file
                else:
                    file_index[stem] = file

            self.docs_to_convert = [str(path) for path in sorted(file_index.values())]

    def get_parser(self, path) -> BaseParser:

        path = Path(path)
        file_type = path.suffix.lower()
        parser = self.EXTENSION_MAP[file_type](path)

        return parser

    def convert(self):
        """
        Converts all parsed docs to markdown and returns a list of markdown strings.
        """

        md_files = []
        for doc in self.docs_to_convert:
            parser = self.get_parser(doc)
            md_text = parser.to_markdown()
            md_files.append(md_text)
        
        if len(md_files) <=1:
            return md_files[0]
        
        return md_files
    
    def dump(self, output_path=None, builtIn_only=True):
        """
        Dump documents as markdown with yaml frontmatter.

        Have to add check if docs_to_convert > 1, to properly handle output_path
        """
        for doc in self.docs_to_convert:
            parser = self.get_parser(doc)
            parser.dump(output_path=output_path, builtIn_only=builtIn_only)
        return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Convert DOCX and PDF documents to Markdown."
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to a file or a directory containing documents."
    )
    parser.add_argument(
        "--builtIn-only",
        action="store_true",
        help="Only include built-in metdata (ignores custom metadata)."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Directory or filepath to save the Markdown files (default: ./dump/<filename>.md)"
    )

    args = parser.parse_args()

    file_path = Path(args.path)
    converter = MarkdownConverter(file_path)

    # Call dump with optional builtIn_only argument
    converter.dump(output_path=args.output, builtIn_only=args.builtIn_only)