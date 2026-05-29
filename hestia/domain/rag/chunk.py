from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

_HEADING_RE = re.compile(r"^(#{1,5})\s+(.*)$")


@dataclass
class Chunk:
    content: str
    source: str
    source_uri: str
    info: dict[str, Any]       # {header, path, level, position}
    doc_info: dict[str, Any]   # {title, version, document_id, ...}
    access: dict[str, Any]     # {classification}
    uploaded_by: str = ""
    uploaded_at: str = ""
    id: UUID = field(default_factory=uuid4)
    token_count: int | None = None
    previous: UUID | None = None
    next: UUID | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "content": self.content,
            "token_count": self.token_count,
            "source": self.source,
            "source_uri": self.source_uri,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at,
            "previous": str(self.previous) if self.previous else None,
            "next": str(self.next) if self.next else None,
            "info": self.info,
            "doc_info": self.doc_info,
            "access": self.access,
        }


class SectionSplitter:
    """Splits markdown text into sections at heading boundaries.

    Sections whose body exceeds ``max_chars`` are further split at paragraph
    boundaries so that no single chunk sent to the embedding model is
    excessively large.
    """

    # ~100 k chars ≈ 25 k tokens at 4 chars/token — well within 32 768-token limits.
    DEFAULT_MAX_CHARS = 100_000

    def __init__(self, max_depth: int = 5, max_chars: int = DEFAULT_MAX_CHARS):
        if not 1 <= max_depth <= 6:
            raise ValueError("max_depth must be between 1 and 6")
        self._max_depth = max_depth
        self._max_chars = max_chars

    def split(self, text: str) -> list[dict[str, Any]]:
        """
        Returns a list of section dicts, each with:
          header, path, level, position, content (str).
        Empty sections are dropped.
        """
        lines = text.splitlines()
        sections: list[dict] = []
        current: dict | None = None
        heading_stack: list[str | None] = [None] * 6

        def _path(level: int) -> str:
            return " > ".join(h for h in heading_stack[:level] if h)

        for i, line in enumerate(lines):
            m = _HEADING_RE.match(line)
            if not m:
                if current is not None:
                    current["content"].append(line)
                continue

            level = len(m.group(1))
            header = m.group(2).strip()

            if level > self._max_depth:
                if current is not None:
                    current["content"].append(line)
                continue

            for j in range(level, 6):
                heading_stack[j] = None
            heading_stack[level - 1] = header

            current = {"header": header, "path": _path(level), "level": level, "content": [], "position": i}
            sections.append(current)

        result = []
        for s in sections:
            body = "\n".join(s["content"]).strip()
            if not body:
                continue
            if len(body) <= self._max_chars:
                result.append({
                    "header": s["header"],
                    "path": s["path"],
                    "level": s["level"],
                    "position": s["position"],
                    "content": body,
                })
            else:
                for part_idx, part in enumerate(self._split_paragraphs(body)):
                    result.append({
                        "header": s["header"],
                        "path": s["path"],
                        "level": s["level"],
                        "position": s["position"],
                        "part": part_idx,
                        "content": part,
                    })
        return result

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split ``text`` at blank-line boundaries, keeping each part under
        ``max_chars``.  A single paragraph that still exceeds ``max_chars`` is
        hard-cut at that limit as a last resort."""
        paragraphs = re.split(r"\n{2,}", text)
        parts: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) + 2 > self._max_chars and current_parts:
                parts.append("\n\n".join(current_parts))
                current_parts = []
                current_len = 0
            # Single paragraph still too large — hard cut
            if len(para) > self._max_chars:
                for i in range(0, len(para), self._max_chars):
                    parts.append(para[i:i + self._max_chars])
                continue
            current_parts.append(para)
            current_len += len(para) + 2

        if current_parts:
            parts.append("\n\n".join(current_parts))
        return parts
