from abc import ABC, abstractmethod
import frontmatter
import re
from pathlib import Path

DUMP_DIR = "./dump"


class Mask:

    def __init__(self, name, keys, is_whitelist=True):
        self.name = name
        self.keys = set(keys) if isinstance(keys, (list, tuple)) else keys
        self.is_whitelist = is_whitelist

    def filter(self, metadata):
        if self.is_whitelist:
            # Include only keys in the whitelist
            return {k: v for k, v in metadata.items() if k in self.keys}
        else:
            # Exclude keys in the blacklist
            return {k: v for k, v in metadata.items() if k not in self.keys}

class MetadataFilter:
    """
    Docstring for MetadataFilter

    TODO:
    - define default masks for PDF, DOCX metadata attributes
    
    :var DEFAULT_METADATA_MASKS: Description
    :vartype DEFAULT_METADATA_MASKS: list[Mask]
    """
    DEFAULT_METADATA_MASKS = [
        Mask(
            name="rag_default",
            keys={
                "title",
                "subject",
                "source",
                "reference",
                "tags",
                "lang",
                "modified",
                "description",
                "classification",
                "category",
                "owner"
            },
            is_whitelist=True,
        ),
        Mask(
            name="ui_display",
            keys={
                "title",
                "author",
                "created_at",
                "modified_at",
            },
            is_whitelist=True,
        ),
        Mask(
            name="internal_full",
            keys=set(),   # ignored for whitelist=False
            is_whitelist=False,  # blacklist mode
        ),
    ]
    def __init__(self):
        self._masks = {}

        for mask in self.DEFAULT_METADATA_MASKS:
            self.add_mask(mask)

    def add_mask(self, mask: Mask):
        self._masks[mask.name] = mask

    def get_mask(self, mask_name):
        return self._masks.get(mask_name, None)
    
    def remove_mask(self, mask_name):
        self._masks.pop(mask_name, None)
    
    def filter(self, metadata, mask_name, strict=False):

        mask = self.get_mask(mask_name)
        if not mask:
            if strict:
                raise KeyError(f"Metadata mask '{mask_name}' not found")
            return metadata
        
        normalized = {k.lower(): v for k, v in metadata.items()}
        return mask.filter(normalized)

    @property
    def masks(self):
        return tuple(self._masks.keys())

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
    
    def dump(self, output_path=None, builtIn_only=True, **kwargs):
        """Dump document as markdown with yaml frontmatter."""
        mask_name = kwargs.get('mask_name', 'internal_full')

        body = self.body or self.to_markdown()
        meta = self.meta or self.get_metadata(builtIn_only=builtIn_only, mask_name=mask_name)

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
    def get_metadata(self, builtIn_only=True, mask_name=None) -> str:
        """Get metadata from the document"""
        pass

    @abstractmethod
    def to_markdown(self) -> str:
        """Convert document to markdown"""
        pass