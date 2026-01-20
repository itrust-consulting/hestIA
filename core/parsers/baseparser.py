from abc import ABC, abstractmethod
import frontmatter
import re
from pathlib import Path

DUMP_DIR = "./dump"

class BaseParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def __init__(self, file = None):
        self.filepath = None
        self.doc = None
        self.body = None # markdown body
        self.meta = {}

        if file is not None:
            self.parse(file)

    def parse(self, file):
        
        if not Path(file).exists():
            raise ValueError(f"{file} does not exist.")
        
        # check if file type is supported
        file_type = Path(file).suffix.lower()
        try:
            loader = self._loader_map[file_type]
            self.doc = loader(file)
            self.filepath = file
        except KeyError:
            raise KeyError(f"File type '{file_type}' not supported by '{self.__class__.__name__}'."
                           f"Supported: {', '.join(self._loader_map.keys())}")
        
        return self.doc

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