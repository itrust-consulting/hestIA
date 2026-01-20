import re
import os
import pymupdf
import pymupdf4llm

from core.parsers.baseparser import BaseParser

os.environ["TESSDATA_PREFIX"] = "C:/Users/hfries/AppData/Local/Programs/Tesseract-OCR/tessdata"

class PDFParser(BaseParser):

    def __init__(self, file = None):
        self._loader_map = {
            ".pdf": self._load_pdf
        }
        super().__init__(file=file)

    def _load_pdf(self, file):
        return pymupdf.open(file)

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