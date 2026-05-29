from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path

import frontmatter

from hestia.domain.exceptions import NotFoundError, ValidationError

_log = logging.getLogger("hestia.system")


class Mask:

    def __init__(self, name: str, keys: set | list | tuple, is_whitelist: bool = True):
        self.name = name
        self.keys = set(keys) if isinstance(keys, (list, tuple)) else keys
        self.is_whitelist = is_whitelist

    def filter(self, metadata: dict) -> dict:
        if self.is_whitelist:
            return {k: v for k, v in metadata.items() if k in self.keys}
        return {k: v for k, v in metadata.items() if k not in self.keys}


class MetadataFilter:

    DEFAULT_METADATA_MASKS = [
        Mask(
            name="rag_default",
            keys={
                "title", "subject", "source", "source_uri", "reference",
                "tags", "lang", "modified", "description", "classification",
                "category", "owner", "author", "version",
            },
            is_whitelist=True,
        ),
        Mask(
            name="ui_display",
            keys={"title", "author", "source", "source_uri", "created_at", "modified_at"},
            is_whitelist=True,
        ),
        Mask(
            name="internal_full",
            keys=set(),
            is_whitelist=False,
        ),
    ]

    def __init__(self):
        self._masks: dict[str, Mask] = {}
        for mask in self.DEFAULT_METADATA_MASKS:
            self.add_mask(mask)

    def add_mask(self, mask: Mask) -> None:
        self._masks[mask.name] = mask

    def get_mask(self, mask_name: str) -> Mask | None:
        return self._masks.get(mask_name)

    def remove_mask(self, mask_name: str) -> None:
        self._masks.pop(mask_name, None)

    def filter(self, metadata: dict, mask_name: str, strict: bool = False) -> dict:
        mask = self.get_mask(mask_name)
        if not mask:
            if strict:
                raise ValidationError(f"Metadata mask '{mask_name}' not found")
            return metadata
        normalized = {k.lower(): v for k, v in metadata.items()}
        return mask.filter(normalized)

    @property
    def masks(self) -> tuple:
        return tuple(self._masks.keys())


class BaseParser(ABC):

    @abstractmethod
    def __init__(self, file=None):
        self.filepath: str | None = None
        self.doc = None
        self.body: str | None = None
        self.meta: dict = {}

        if file is not None:
            self.parse(file)

    def parse(self, file):
        if not Path(file).exists():
            raise NotFoundError(f"File not found: {file}")

        file_type = Path(file).suffix.lower()
        if file_type not in self._loader_map:
            raise ValidationError(
                f"File type '{file_type}' not supported by '{self.__class__.__name__}'. "
                f"Supported: {', '.join(self._loader_map.keys())}"
            )
        self.doc = self._loader_map[file_type](file)
        self.filepath = str(file)
        return self.doc

    def normalize_key(self, k: str) -> str:
        return k.lower().replace(" ", "_")

    def clean_string(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def dump(self, output_path=None, dump_dir: str = "./dump", builtIn_only: bool = True, **kwargs) -> None:
        mask_name = kwargs.get("mask_name", "internal_full")
        body = self.body or self.to_markdown()
        meta = self.meta or self.get_metadata(builtIn_only=builtIn_only, mask_name=mask_name)

        post = frontmatter.Post(content=body, **meta)
        if not output_path:
            filename = Path(self.filepath).stem
            out_dir = Path(dump_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / f"{filename}.md"

        with open(output_path, "wb") as f:
            frontmatter.dump(post, f)

    def dumps(self, builtIn_only: bool = True, **kwargs) -> frontmatter.Post:
        mask_name = kwargs.get("mask_name", "internal_full")
        body = self.body or self.to_markdown()
        meta = self.meta or self.get_metadata(builtIn_only=builtIn_only, mask_name=mask_name)
        return frontmatter.Post(content=body, **meta)

    def close(self) -> None:
        """Release any open file handles. Override in parsers that hold OS locks."""
        pass

    @abstractmethod
    def get_metadata(self, builtIn_only: bool = True, mask_name: str | None = None) -> dict:
        pass

    @abstractmethod
    def to_markdown(self) -> str:
        pass
