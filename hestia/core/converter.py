import argparse
from pathlib import Path

from hestia.core.parsers.docx_parser import ITRDOCXParser
from hestia.core.parsers.pdf_parser import PDFParser

SUPPPORTED_EXTENSIONS = [".docx", ".pdf"]

class MarkdownConverter:
    EXTENSION_MAP = {
        ".docx": ITRDOCXParser,
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

    def get_parser(self, path):

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
    
    def dump(self, output_path=None, builtIn_only=True, mask_name=None):
        """
        Dump documents as markdown with yaml frontmatter.

        Have to add check if docs_to_convert > 1, to properly handle output_path
        """
        for doc in self.docs_to_convert:
            parser = self.get_parser(doc)
            parser.dump(output_path=output_path, builtIn_only=builtIn_only, mask_name=mask_name)
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
        help="Only include built-in metadata (ignores custom metadata)."
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
    converter.dump(output_path=args.output, builtIn_only=True, mask_name="rag_default")#args.builtIn_only)