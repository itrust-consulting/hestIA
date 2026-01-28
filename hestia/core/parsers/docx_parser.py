
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree
import zipfile
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import warnings

from hestia.core.parsers.baseparser import BaseParser, MetadataFilter

try:
    import pypandoc
    PANDOC_AVAILABLE = True
except ModuleNotFoundError:
    PANDOC_AVAILABLE = False

# Rather a converter than a Parser.
class DOCXParser(BaseParser):

    NAMESPACES = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                  "dcelem": "http://purl.org/dc/elements/1.1/",
                  "dcterm": "http://purl.org/dc/terms/",
                  "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
                  "ep":"http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
                  "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
                  "dgm": "http://schemas.openxmlformats.org/package/2006/relationships",
                  "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}

    def __init__(self, file = None):
        self._style_levels = None
        self._loader_map = {
            ".docx": self._load_doc
        }
        super().__init__(file=file)

    def _load_doc(self, file):
        self._style_levels = self.get_list_styles_from_styles_xml(file)
        self._footnotes = self.get_footnotes_from_footnotes_xml(file)
        self._rels = self.get_rels_from_xml(file)
        return Document(file)
        
    def get_list_styles_from_styles_xml(self, file):
        """Return {styleId: ilvl} for list styles defined in styles.xml."""
        style_levels = {}
        with zipfile.ZipFile(file) as zf:
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
                return ilvl.val

        # 2. Custom style-based lists
        if pPr.pStyle is not None:
            style_id = pPr.pStyle.val
            if style_id in style_levels:
                return style_levels[style_id]

        return None

    def get_footnotes_from_footnotes_xml(self, file):
        footnotes = {}
        with zipfile.ZipFile(file) as zf:
            if "word/footnotes.xml" not in zf.namelist():
                return footnotes
            xml_data = zf.read("word/footnotes.xml")
        root = etree.fromstring(xml_data)
        for footnote in root.findall("w:footnote", self.NAMESPACES):
            footnote_ref = footnote.get("{%s}id" % self.NAMESPACES["w"])
            footnote_text = [t.text for t in footnote.findall(".//w:t", self.NAMESPACES) if t.text]
            footnotes[footnote_ref] = "".join(footnote_text)
        return footnotes

    def get_rels_from_xml(self, file):
        rels = {}
        with zipfile.ZipFile(file) as zf:
            if "word/_rels/document.xml.rels" not in zf.namelist():
                return rels
            xml_data = zf.read("word/_rels/document.xml.rels")
        root = etree.fromstring(xml_data)
        for rel in root.iter("{%s}Relationship" % self.NAMESPACES["dgm"]):
            ref = rel.get("Id")
            target = rel.get("Target")
            rels[ref] = target
        return rels

    def omml_to_md_latex(self, omml_elem):
        
        try:
            tmp_doc = Document()
            p = tmp_doc.add_paragraph()
            p._p.append(omml_elem)

            with NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                tmp_doc.save(tmp_path)
                md_latex = pypandoc.convert_file(tmp_file.name, to="markdown")
            return md_latex.strip()
        
        except OSError as e:
            warnings.warn(
                f"OMML conversion failed: Pandoc is not installed. OMML conversion skipped. Math environments will not be parsed.",
                UserWarning
            )
            return "<--OMML conversion failed. See logs.-->"

        except RuntimeError as e:
            warnings.warn(f"OMML conversion failed: {e}", UserWarning)
            return "<--OMML conversion failed. See logs.-->"
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    def render_hyperlink(self, hyperlink_elem):
        
        label = hyperlink_elem.text

        rel_id = hyperlink_elem.get(f"{{{self.NAMESPACES['r']}}}id")
        if rel_id and rel_id in self._rels:
            return f"[{label}]({self._rels[rel_id]})"

        return label
    
    def handle_footnotes(self, para):
        tmp = ""
        footnotes = ""
        for elem in para.iter_inner_content():
            tmp += elem.text
            footnote_ref = elem._r.find(".//w:footnoteReference", self.NAMESPACES)
            if footnote_ref is not None:
                ref = footnote_ref.get("{%s}id" % self.NAMESPACES["w"])
                footnote_text = self._footnotes[ref]
                tmp += f"[^{ref}]"
                footnotes += f"[^{ref}] {footnote_text}\n\n"
        return (tmp + "\n\n" + footnotes).strip()

    def get_para_prefix(self, para, style_levels):
        style_name = para.style.name or ""

        # Handle Heading
        if style_name.startswith("Heading"):
            level = int(style_name.split()[-1])
            return f"{'#' * level} "
        
        # Handle List item
        ilvl = self.get_list_level_from_paragraph(para, style_levels)
        if ilvl is not None:
            indent = "\t" * ilvl
            return f"{indent}- "

        return ""

    def render_para_runs(self, para):
        parts = []
        footnotes = []

        for child in para._p.iterchildren():
            tag = child.tag
            # Handle Runs            
            if tag == f"{{{self.NAMESPACES['w']}}}r":
                if child.text:
                    parts.append(child.text)
                # Handle Footnotes
                for fn in child.iter(f"{{{self.NAMESPACES['w']}}}footnoteReference"):
                    ref = fn.get(f"{{{self.NAMESPACES['w']}}}id")
                    parts.append(f"[^{ref}]")
                    footnotes.append(f"[^{ref}] {self._footnotes[ref]}")

            # Handle Hyperlinks
            elif tag == f"{{{self.NAMESPACES['w']}}}hyperlink":
                parts.append(self.render_hyperlink(child))

            # Handle OMML (Math Env)
            elif tag in (
                f"{{{self.NAMESPACES['m']}}}oMath",
                f"{{{self.NAMESPACES['m']}}}oMathPara",
            ):
                parts.append(self.omml_to_md_latex(child))

        

        return "".join(parts), "".join(footnotes)

    def para_to_markdown(self, para: Paragraph, style_levels: dict):
        

        prefix = self.get_para_prefix(para, style_levels)
        body, footnotes = self.render_para_runs(para)
        if not body.strip():
            return ""
        
        if footnotes:
             return f"{prefix}{body}\n{footnotes}".rstrip()

        return f"{prefix}{body}".rstrip()

    def format_cell_text(self, cell_text):
        def normalize(t: str) -> str:
            return (
                t.replace("\n", "<br>")
                .replace("\t", "&nbsp; ")
            )

        return "<br>".join(normalize(t) for t in cell_text if t).strip()

    def extract_table_text(self, table: Table):
        """Return table as list of rows of strings."""
        rows = []
        for row in table.rows:
            row_cells = []
            for cell in row.cells:
                cell_text = [self.para_to_markdown(para, self._style_levels) for para in cell.paragraphs]
                #print(cell_text)
                md_cell_text = self.format_cell_text(cell_text)
                #print(md_cell_text)
                row_cells.append(md_cell_text)
            rows.append(row_cells)
        return rows

    def extract_table_text_pandoc(self, table: Table):
        if not PANDOC_AVAILABLE:
            raise ModuleNotFoundError("pypandoc is not installed")
        
        tmp_doc = Document()
        tmp_doc._body._element.append(table._tbl)  # clone paragraph

        with NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
            tmp_doc.save(tmp_file.name)
            md_latex = pypandoc.convert_file(tmp_file.name, to="markdown")
            
        return md_latex.strip()
        
    def table_to_markdown(self, table: Table):
        #try:
        #   return self.extract_table_text_pandoc(table)
        #except (ModuleNotFoundError, OSError, RuntimeError) as e:
        #    warnings.warn(
        #        f"{e}. Using fallback table extraction. Install Pandoc for improved results.",
        #        UserWarning
        #    )

        rows = self.extract_table_text(table)
        md_rows = ["| " + " | ".join(r) + " |" for r in rows]
        if rows:
            header_sep = "| " + " | ".join(["---"] * len(rows[0])) + " |"
            md_rows.insert(1, header_sep)
        md_table = "\n".join(md_rows)

        return md_table

    def get_builtin_metadata(self, file: str) -> dict:
        """get document builtin metadata (core + custom)"""
        metadata = {}
        with zipfile.ZipFile(file) as zf:
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
    
    def get_metadata(self, mask_name=None):
        stem = Path(self.filepath).stem
        builtIn = self.get_builtin_metadata(self.filepath) 
        metadata = {**builtIn, "source": stem}

        if mask_name:
            # "global" call to the MetadataFilter instance. change in futuer
            metadata = MetadataFilter().filter(metadata, mask_name)
        
        self.meta = metadata
        return metadata
    
    def to_markdown(self):
        lines=[]
        for body in self.doc.iter_inner_content():
            if isinstance(body, Paragraph):
                md = self.para_to_markdown(body, self._style_levels)
                if md:
                    lines.append(md)
            if isinstance(body, Table):
                md = self.table_to_markdown(body)
                if md:
                    lines.append(md)
        md_text = "\n\n".join(lines) 
        self.body = md_text

        return md_text
    
class ITRDOCXParser(DOCXParser):
    """
    extend DOCXParser to handle itrust specifics, e.g., builtin-Metadata
    """
    def __init__(self, file=None):
        super().__init__(file)

    def get_builtin_metadata(self, file: str) -> dict:
        """get document builtin metadata (core + custom)"""
        metadata = {}
        with zipfile.ZipFile(file) as zf:
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

    def get_metadata_from_cover_page(self, file: str) -> dict:
        doc = Document(file)
        # assuming itr template
        if len(doc.tables) < 1:
            return {}
        table_data = doc.tables[1]._tbl
        data = self.extract_table_text(table_data)
        if data:
            metadata = {k: v for k, v in data} 
        else:
            metadata = {}
        return metadata

    def get_metadata(self, builtIn_only=True, mask_name=None):
        
        # Get base metadata
        stem = Path(self.filepath).stem
        builtIn = self.get_builtin_metadata(self.filepath)
        metadata = {**builtIn, "source": stem}

        # Get custom metadata if needed
        if not builtIn_only:
            custom = self.get_metadata_from_cover_page(self.filepath)
            # Merge custom metadata, giving custom values precedence
            metadata = {**metadata, **custom}

        # Apply mask once at the end
        if mask_name:
            metadata = MetadataFilter().filter(metadata, mask_name)

        self.meta = metadata
        return metadata

if __name__ == "__main__":
    p = ITRDOCXParser()
    p.parse("../tests/test_inputs/Test-Document.docx")
    p.dump(builtIn_only=True, mask_name="rag_default")