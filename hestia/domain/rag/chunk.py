from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, NamedTuple, Protocol
from uuid import UUID, uuid4

_HEADING_RE = re.compile(r"^(#{1,5})\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$")

# ~100 k chars ≈ 25 k tokens at 4 chars/token — well within 32 768-token limits.
_DEFAULT_MAX_CHARS = 100_000


class ChunkingStrategy(Protocol):
    """Common interface for splitting a parsed document's markdown body into
    chunk-shaped dicts (see ``SectionSplitter.split`` / ``BlockSplitter.split``
    for the exact shape). Every chunk carries a ``block_type`` ("prose" or
    "table") and an optional 0-based ``part`` index when its source unit
    (a section or the whole document) produced more than one chunk."""

    def split(self, text: str) -> list[dict[str, Any]]: ...


def _pack_blocks(blocks: list[str], max_chars: int) -> list[str]:
    """Pack already-split ``blocks`` into parts up to ``max_chars``, joined
    with blank lines. A single block that alone exceeds ``max_chars`` is
    hard-cut at that limit as a last resort."""
    parts: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if current_len + len(block) + 2 > max_chars and current_parts:
            parts.append("\n\n".join(current_parts))
            current_parts = []
            current_len = 0
        if len(block) > max_chars:
            for i in range(0, len(block), max_chars):
                parts.append(block[i:i + max_chars])
            continue
        current_parts.append(block)
        current_len += len(block) + 2

    if current_parts:
        parts.append("\n\n".join(current_parts))
    return parts


def _is_table_block(block: str) -> bool:
    """True if ``block`` looks like a markdown table: a header row followed
    by a separator row (e.g. ``|---|---|``)."""
    lines = [line for line in block.splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].lstrip().startswith("|"):
        return False
    return bool(_TABLE_SEP_RE.match(lines[1].strip()))


def _split_table_rows(block: str, max_chars: int) -> list[str]:
    """Split a markdown table by row groups, repeating the header + separator
    row as a prefix on each part so every chunk stays a valid, self-contained
    table."""
    lines = block.splitlines()
    header, sep, rows = lines[0], lines[1], lines[2:]
    prefix = f"{header}\n{sep}\n"

    parts: list[str] = []
    current_rows: list[str] = []
    current_len = len(prefix)

    for row in rows:
        row_len = len(row) + 1
        if current_len + row_len > max_chars and current_rows:
            parts.append(prefix + "\n".join(current_rows))
            current_rows = []
            current_len = len(prefix)
        current_rows.append(row)
        current_len += row_len

    if current_rows:
        parts.append(prefix + "\n".join(current_rows))
    return parts or [block]


class _TypedBlock(NamedTuple):
    """One semantic unit within a body of text, in source order. ``parts``
    has length 1 for an intact unit, and length > 1 only when that unit
    alone exceeded ``max_chars`` (a prose run got packed/hard-cut, or a
    table got split by row group)."""
    block_type: str  # "prose" | "table"
    parts: list[str]


def _split_typed_blocks(text: str, max_chars: int) -> list[_TypedBlock]:
    """Split ``text`` into blank-line-delimited blocks, classify each as
    prose or a markdown table, pack consecutive prose blocks into runs up to
    ``max_chars``, and keep tables row-intact (splitting a single table by
    row group, header repeated, only if it alone exceeds ``max_chars``).
    Shared by ``SectionSplitter`` (applied within one section's body) and
    ``BlockSplitter`` (applied to a whole headerless document)."""
    blocks = [b.strip() for b in re.split(r"\n{2,}", text)]
    blocks = [b for b in blocks if b]
    if not blocks:
        return []

    result: list[_TypedBlock] = []
    pending_prose: list[str] = []

    def flush_prose():
        if not pending_prose:
            return
        packed = _pack_blocks(pending_prose, max_chars)
        if packed:
            result.append(_TypedBlock("prose", packed))
        pending_prose.clear()

    for block in blocks:
        if not _is_table_block(block):
            pending_prose.append(block)
            continue
        flush_prose()
        parts = [block] if len(block) <= max_chars else _split_table_rows(block, max_chars)
        result.append(_TypedBlock("table", [p.strip() for p in parts]))

    flush_prose()
    return result


# doc_info keys computed by the ingestion pipeline itself (never sent by the
# post-ingestion metadata-edit endpoint). update_document_metadata must
# always preserve these when the edit payload omits them, while treating
# every other key (fixed fields like title/author, plus any custom key) as
# fully replaced by the payload -- so removing a custom field client-side
# actually deletes it instead of leaving it stranded forever.
RESERVED_DOC_INFO_KEYS = frozenset({"document_id", "source", "source_uri"})


@dataclass
class Chunk:
    content: str
    source: str
    source_uri: str
    info: dict[str, Any]       # {header, path, level, position, block_type, chunking_strategy, [part]}
    doc_info: dict[str, Any]   # {title, version, document_id, ...}
    access: dict[str, Any]     # {classification}
    uploaded_by: str = ""
    uploaded_at: str = ""
    id: UUID = field(default_factory=uuid4)
    token_count: int | None = None
    previous: UUID | None = None
    next: UUID | None = None

    # @MRS-013, @MRS-018
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

    Within a section, prose and markdown tables are differentiated rather
    than treated as one blob: a section mixing a paragraph and a table
    yields separate ``block_type``-tagged chunks (sharing the section's
    header/path/level/position, distinguished by a 0-based ``part`` index),
    and a table is only ever split row-safe (by row group, header repeated)
    instead of being hard-cut by character count. A pure-prose section that
    fits under ``max_chars`` stays a single chunk with its content
    unchanged, exactly as before.
    """

    DEFAULT_MAX_CHARS = _DEFAULT_MAX_CHARS
    DEFAULT_MAX_DEPTH = 5

    # @MRS-019
    def __init__(self, max_depth: int = DEFAULT_MAX_DEPTH, max_chars: int = DEFAULT_MAX_CHARS):
        if not 1 <= max_depth <= 6:
            raise ValueError("max_depth must be between 1 and 6")
        self._max_depth = max_depth
        self._max_chars = max_chars

    # @MRS-015, @MRS-016, @MRS-019
    def split(self, text: str) -> list[dict[str, Any]]:
        """
        Returns a list of chunk dicts, each with:
          header, path, level, position, content, block_type
        (+ optional 0-based part when a section produced more than one
        chunk). Empty sections are dropped.
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

            # @MRS-018
            current = {"header": header, "path": _path(level), "level": level, "content": [], "position": i}
            sections.append(current)

        result = []
        for s in sections:
            body = "\n".join(s["content"]).strip()
            if not body:
                continue

            units = _split_typed_blocks(body, self._max_chars)
            flat = [(u.block_type, part) for u in units for part in u.parts] or [("prose", body)]

            if len(flat) == 1:
                block_type, content = flat[0]
                if len(body) <= self._max_chars:
                    content = body
                result.append({
                    "header": s["header"],
                    "path": s["path"],
                    "level": s["level"],
                    "position": s["position"],
                    "content": content,
                    "block_type": block_type,
                })
            else:
                for part_idx, (block_type, content) in enumerate(flat):
                    result.append({
                        "header": s["header"],
                        "path": s["path"],
                        "level": s["level"],
                        "position": s["position"],
                        "part": part_idx,
                        "content": content,
                        "block_type": block_type,
                    })
        return result


class BlockSplitter:
    """Fallback chunking strategy for documents with no heading structure
    (letters, invoices, CSV/plain-text uploads) — anything ``SectionSplitter``
    would otherwise turn into zero chunks.

    Splits the markdown body into blank-line-delimited blocks, classifies
    each as prose or a markdown table, packs consecutive prose blocks up to
    ``max_chars``, and keeps tables row-intact (splitting only by row group,
    repeating the header, if a single table alone exceeds ``max_chars``).
    """

    DEFAULT_MAX_CHARS = _DEFAULT_MAX_CHARS

    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS):
        self._max_chars = max_chars

    def split(self, text: str) -> list[dict[str, Any]]:
        """
        Returns a list of chunk dicts, each with:
          header, path, level (always 0), position, content, block_type
        (+ optional part for a row-split table).
        """
        result: list[dict[str, Any]] = []
        position = 0
        para_count = 0
        table_count = 0

        for unit in _split_typed_blocks(text, self._max_chars):
            if unit.block_type == "prose":
                for part in unit.parts:
                    para_count += 1
                    label = f"Paragraph {para_count}"
                    result.append({
                        "header": label, "path": label, "level": 0,
                        "position": position, "content": part, "block_type": "prose",
                    })
                    position += 1
                continue

            table_count += 1
            table_label = f"Table {table_count}"
            n = len(unit.parts)
            for part_idx, part in enumerate(unit.parts):
                label = table_label if n == 1 else f"{table_label} (rows {part_idx + 1}/{n})"
                entry = {
                    "header": label, "path": label, "level": 0,
                    "position": position, "content": part, "block_type": "table",
                }
                if n > 1:
                    entry["part"] = part_idx
                result.append(entry)
                position += 1

        return result
