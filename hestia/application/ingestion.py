from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hestia.domain.exceptions import ConfigurationError, ValidationError
from hestia.domain.rag.chunk import BlockSplitter, Chunk, SectionSplitter
from hestia.domain.rag.classification import Classification
from hestia.infrastructure.db.protocol import DBProvider
from hestia.infrastructure.parsers.base import BaseParser

_log = logging.getLogger("hestia.system")

_EMBED_TEMPLATE = "# {title}\n\n## {path}\n\n{content}"

CHUNKING_STRATEGIES = ("auto", "section", "block")

# Guardrails on the user-configurable chunk-size override: below MIN_CHUNK_CHARS
# a chunk is barely useful content for retrieval; above MAX_CHUNK_CHARS mostly
# just wastes embedding truncation headroom (see _MAX_EMBED_CHARS below).
MIN_CHUNK_CHARS = 200
MAX_CHUNK_CHARS = 500_000

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".docx": "docx",
    ".pdf": "pdf",
    ".xlsx": "xlsx",
    ".xlsm": "xlsm",
    ".json": "json",
    ".csv": "csv",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
    ".pptx": "pptx",
}


@dataclass
class IngestionRequest:
    file_path: str | Path
    collection: str
    tenants: list[str]
    uploaded_by: str = ""
    classification_labels: list[str] = field(default_factory=list)
    mask_name: str = "rag_default"
    itrust_template: bool = False
    original_filename: str | None = None
    metadata_overrides: dict | None = None
    language: str = "english"
    selected_sheets: list[str] | None = None
    chunking_strategy: str = "auto"
    max_chars: int | None = None
    max_depth: int | None = None


@dataclass
class IngestionResult:
    collection: str
    source: str
    n_chunks: int
    n_upserted: int
    elapsed_ms: float


class IngestionPipeline:

    def __init__(self, dense_encoder, sparse_encoder, db: DBProvider):
        self.dense_encoder = dense_encoder
        self.sparse_encoder = sparse_encoder
        self.db = db

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def ingest(self, req: IngestionRequest) -> IngestionResult:
        if req.chunking_strategy not in CHUNKING_STRATEGIES:
            raise ValidationError(
                f"Unknown chunking strategy '{req.chunking_strategy}'. "
                f"Supported: {', '.join(CHUNKING_STRATEGIES)}"
            )
        if req.max_chars is not None and not (MIN_CHUNK_CHARS <= req.max_chars <= MAX_CHUNK_CHARS):
            raise ValidationError(f"max_chars must be between {MIN_CHUNK_CHARS} and {MAX_CHUNK_CHARS}.")
        if req.max_depth is not None and not (1 <= req.max_depth <= 6):
            raise ValidationError("max_depth must be between 1 and 6.")

        t0 = time.perf_counter()
        file_path = Path(req.file_path)

        _log.info("ingestion_start", extra={
            "file": str(file_path),
            "collection": req.collection,
            "tenants": req.tenants,
        })

        parser = self._get_parser(file_path, req.itrust_template, req.selected_sheets)
        try:
            body = parser.to_markdown()
            metadata = parser.get_metadata(builtIn_only=not req.itrust_template, mask_name=req.mask_name)
        finally:
            parser.close()

        # If the file was written to a temp path, restore the original name so it
        # doesn't leak into source / source_uri / document_id.
        if req.original_filename:
            original_stem = Path(req.original_filename).stem
            metadata["source"] = original_stem
            metadata["source_uri"] = req.original_filename

        # Apply user-provided metadata edits (from the review step in the UI).
        # @MRS-014
        if req.metadata_overrides:
            metadata.update({k: v for k, v in req.metadata_overrides.items() if v != ""})

        matched_levels = [
            c.level
            for v in metadata.values()
            if isinstance(v, str) and (c := Classification.from_label(v)) is not None
        ]
        # Documents with no resolvable classification label default to
        # Internal, not Public: a Qdrant range filter (access.classification
        # <= max_cls) excludes points where the field is null, so an
        # unclassified document would otherwise be silently invisible to
        # every classification-filtered search. Internal keeps it out of
        # Public view until someone consciously marks it Public. doc_info
        # (the metadata overview) reads its own "classification" string
        # separately from access.classification, so it needs the same
        # default -- otherwise the overview shows "—" while access
        # control silently treats the document as Internal.
        if not matched_levels:
            metadata["classification"] = Classification.INTERNAL.aliases[0]
        access = {"classification": max(matched_levels) if matched_levels else Classification.INTERNAL.level}

        # The interactive upload flow always resolves a language (required
        # field); Sync Folder auto-ingestion can send an empty one. Default
        # both the stemmer language and the displayed doc_info.lang so
        # neither ends up silently blank.
        language = req.language or "english"
        metadata["lang"] = metadata.get("lang") or language

        max_chars = req.max_chars if req.max_chars is not None else SectionSplitter.DEFAULT_MAX_CHARS
        max_depth = req.max_depth if req.max_depth is not None else SectionSplitter.DEFAULT_MAX_DEPTH
        sections, strategy_used = self._split_document(body, req.chunking_strategy, max_chars, max_depth)

        source = metadata["source"]
        source_uri = metadata["source_uri"]
        uploaded_at = datetime.now(timezone.utc).isoformat()
        doc_info = {
            **metadata,
            "document_id": f"{req.tenants[0] if req.tenants else 'unknown'}-{metadata['source']}",
        }

        if not sections:
            _log.warning("ingestion_no_sections", extra={"file": str(file_path)})
            return IngestionResult(
                collection=req.collection, source=source,
                n_chunks=0, n_upserted=0,
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
            )

        chunks = self._build_chunks(
            sections, source, source_uri, doc_info, access, req.uploaded_by, uploaded_at, strategy_used,
        )
        _log.debug("ingestion_chunks", extra={"n": len(chunks), "collection": req.collection})

        dense_vecs = self._embed_chunks(chunks, doc_info)
        dense_dim = len(dense_vecs[0])

        sparse_vecs = self.sparse_encoder.encode_documents(
            [c.content for c in chunks], req.collection,
            source_uri=source_uri, language=language,
        )

        self.db.initialize(req.collection, {"dense_dim": dense_dim, "create_indexes": True})

        points = [
            {
                "id": str(c.id),
                "payload": c.to_payload(),
                "dense": d,
                "sparse": {"indices": s.indices, "values": s.values},
            }
            for c, d, s in zip(chunks, dense_vecs, sparse_vecs)
        ]
        self.db.upsert(req.collection, points)

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        _log.info("ingestion_done", extra={
            "collection": req.collection, "source": source,
            "n_chunks": len(chunks), "elapsed_ms": elapsed,
        })
        return IngestionResult(
            collection=req.collection, source=source,
            n_chunks=len(chunks), n_upserted=len(chunks),
            elapsed_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_parser(self, file_path: Path, itrust_template: bool, selected_sheets: list[str] | None = None) -> BaseParser:
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"File type '{ext}' not supported for ingestion. "
                f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        if ext == ".docx":
            if itrust_template:
                from hestia.infrastructure.parsers.docx import ITRDOCXParser
                return ITRDOCXParser(file=str(file_path))
            from hestia.infrastructure.parsers.docx import DOCXParser
            return DOCXParser(file=str(file_path))
        if ext == ".pdf":
            if itrust_template:
                from hestia.infrastructure.parsers.pdf import ITRPDFParser
                return ITRPDFParser(file=str(file_path))
            from hestia.infrastructure.parsers.pdf import PDFParser
            return PDFParser(file=str(file_path))
        if ext in (".xlsx", ".xlsm"):
            if itrust_template:
                from hestia.infrastructure.parsers.xlsx import ITRXLSXParser
                return ITRXLSXParser(file=str(file_path), selected_sheets=selected_sheets)
            from hestia.infrastructure.parsers.xlsx import XLSXParser
            return XLSXParser(file=str(file_path), selected_sheets=selected_sheets)
        if ext == ".json":
            from hestia.infrastructure.parsers.json import JSONParser
            return JSONParser(file=str(file_path))
        if ext == ".csv":
            from hestia.infrastructure.parsers.csv import CSVParser
            return CSVParser(file=str(file_path))
        if ext == ".txt":
            from hestia.infrastructure.parsers.txt import TXTParser
            return TXTParser(file=str(file_path))
        if ext in (".md", ".markdown"):
            from hestia.infrastructure.parsers.md import MarkdownParser
            return MarkdownParser(file=str(file_path))
        if ext == ".pptx":
            from hestia.infrastructure.parsers.pptx import PPTXParser
            return PPTXParser(file=str(file_path))
        raise ConfigurationError(f"No parser registered for '{ext}'")

    def _split_document(
        self, body: str, strategy: str, max_chars: int, max_depth: int,
    ) -> tuple[list[dict[str, Any]], str]:
        """Chunk ``body`` per ``strategy`` ('auto' | 'section' | 'block').

        'auto' tries section-based (heading) chunking first — unchanged
        behavior for every document that already chunks correctly — and
        only falls back to the block-based strategy when that yields no
        chunks (documents with no heading structure: letters, invoices,
        CSV/plain-text uploads, etc.). ``max_depth`` is inapplicable to the
        block strategy and silently ignored there.
        """
        if strategy in ("auto", "section"):
            sections = SectionSplitter(max_depth=max_depth, max_chars=max_chars).split(body)
            if sections or strategy == "section":
                return sections, "section"
        return BlockSplitter(max_chars=max_chars).split(body), "block"

    def _build_chunks(
        self,
        sections: list[dict[str, Any]],
        source: str,
        source_uri: str,
        doc_info: dict,
        access: dict,
        uploaded_by: str = "",
        uploaded_at: str = "",
        chunking_strategy: str = "",
    ) -> list[Chunk]:
        chunks = [
            Chunk(
                content=s["content"],
                source=source,
                source_uri=source_uri,
                info={
                    **{k: v for k, v in s.items() if k != "content"},
                    "chunking_strategy": chunking_strategy,
                },
                doc_info=doc_info,
                access=access,
                uploaded_by=uploaded_by,
                uploaded_at=uploaded_at,
                token_count=len(s["content"].split()),
            )
            for s in sections
        ]
        for i, chunk in enumerate(chunks):
            chunk.previous = chunks[i - 1].id if i > 0 else None
            chunk.next = chunks[i + 1].id if i < len(chunks) - 1 else None
        return chunks

    # Conservative character limit: ~100 k chars ≈ 25 k tokens at 4 chars/token.
    # Keeps every embed text safely within typical 32 768-token model limits.
    _MAX_EMBED_CHARS = 100_000

    def _embed_chunks(self, chunks: list[Chunk], doc_info: dict) -> list[list[float]]:
        texts = []
        for chunk in chunks:
            t = _EMBED_TEMPLATE.format(
                title=doc_info.get("title", ""),
                path=chunk.info.get("path", ""),
                content=chunk.content.strip(),
            )
            if len(t) > self._MAX_EMBED_CHARS:
                _log.warning("embed_text_truncated", extra={
                    "source": doc_info.get("source", ""),
                    "original_chars": len(t),
                    "truncated_to": self._MAX_EMBED_CHARS,
                })
                t = t[:self._MAX_EMBED_CHARS]
            texts.append(t)
        return [dv.vector for dv in self.dense_encoder.encode_batch(texts)]
