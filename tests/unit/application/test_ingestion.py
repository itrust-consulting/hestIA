from __future__ import annotations

import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hestia.application.ingestion import IngestionPipeline, IngestionRequest
from hestia.domain.rag.chunk import Chunk
from hestia.domain.rag.classification import Classification
from hestia.domain.rag.types import DenseVector, SparseVector
from hestia.domain.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_dense_encoder():
    enc = MagicMock()
    enc.encode.return_value = DenseVector(vector=[0.1, 0.2, 0.3])
    enc.encode_batch.return_value = [DenseVector(vector=[0.1, 0.2, 0.3])]
    return enc


@pytest.fixture
def mock_sparse_encoder():
    enc = MagicMock()
    enc.encode_documents.return_value = [SparseVector(indices=[0, 1], values=[0.5, 0.3])]
    return enc


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def pipeline(mock_dense_encoder, mock_sparse_encoder, mock_db):
    return IngestionPipeline(
        dense_encoder=mock_dense_encoder,
        sparse_encoder=mock_sparse_encoder,
        db=mock_db,
    )


# ---------------------------------------------------------------------------
# IngestionPipeline._get_parser — extension dispatch
# ---------------------------------------------------------------------------

class TestGetParser:

    def test_docx_extension_returns_docx_parser(self, pipeline, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"")
        # _get_parser imports parsers lazily; patch on the source module so the
        # `from ... import` inside the function picks up the mock.
        with patch("hestia.infrastructure.parsers.docx.DOCXParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()

    def test_pdf_extension_returns_pdf_parser(self, pipeline, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.pdf.PDFParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()

    def test_itrust_docx_returns_itr_parser(self, pipeline, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.docx.ITRDOCXParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=True, selected_sheets=None)
        MockP.assert_called_once()

    def test_unsupported_extension_raises(self, pipeline, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_bytes(b"")
        with pytest.raises(ValidationError, match="not supported"):
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)

    def test_csv_extension_dispatched(self, pipeline, tmp_path):
        f = tmp_path / "data.csv"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.csv.CSVParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()

    def test_itrust_pdf_returns_itr_parser(self, pipeline, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.pdf.ITRPDFParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=True, selected_sheets=None)
        MockP.assert_called_once()

    def test_xlsx_extension_returns_xlsx_parser(self, pipeline, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.xlsx.XLSXParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=["Sheet1"])
        MockP.assert_called_once_with(file=str(f), selected_sheets=["Sheet1"])

    def test_itrust_xlsx_returns_itr_xlsx_parser(self, pipeline, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.xlsx.ITRXLSXParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=True, selected_sheets=None)
        MockP.assert_called_once()

    def test_json_extension_dispatched(self, pipeline, tmp_path):
        f = tmp_path / "data.json"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.json.JSONParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()

    def test_txt_extension_dispatched(self, pipeline, tmp_path):
        f = tmp_path / "data.txt"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.txt.TXTParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()

    def test_md_extension_dispatched(self, pipeline, tmp_path):
        f = tmp_path / "data.md"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.md.MarkdownParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()

    def test_pptx_extension_dispatched(self, pipeline, tmp_path):
        f = tmp_path / "data.pptx"
        f.write_bytes(b"")
        with patch("hestia.infrastructure.parsers.pptx.PPTXParser") as MockP:
            MockP.return_value = MagicMock()
            pipeline._get_parser(f, itrust_template=False, selected_sheets=None)
        MockP.assert_called_once()


# ---------------------------------------------------------------------------
# IngestionPipeline._build_chunks
# ---------------------------------------------------------------------------

class TestBuildChunks:

    def _sections(self, n):
        return [
            {"header": f"H{i}", "path": f"H{i}", "level": 1, "position": i, "content": f"Content {i}"}
            for i in range(n)
        ]

    def test_single_chunk_no_links(self, pipeline):
        sections = self._sections(1)
        chunks = pipeline._build_chunks(sections, "src", "src.pdf", {}, {})
        assert chunks[0].previous is None
        assert chunks[0].next is None

    def test_first_chunk_has_no_previous(self, pipeline):
        chunks = pipeline._build_chunks(self._sections(3), "s", "s.pdf", {}, {})
        assert chunks[0].previous is None

    def test_last_chunk_has_no_next(self, pipeline):
        chunks = pipeline._build_chunks(self._sections(3), "s", "s.pdf", {}, {})
        assert chunks[-1].next is None

    def test_middle_chunk_linked(self, pipeline):
        chunks = pipeline._build_chunks(self._sections(3), "s", "s.pdf", {}, {})
        assert chunks[1].previous == chunks[0].id
        assert chunks[1].next == chunks[2].id

    def test_consecutive_chunks_linked(self, pipeline):
        chunks = pipeline._build_chunks(self._sections(3), "s", "s.pdf", {}, {})
        assert chunks[0].next == chunks[1].id

    def test_chunking_strategy_included_in_chunk_info_not_doc_info(self, pipeline):
        doc_info = {"title": "Doc"}
        chunks = pipeline._build_chunks(self._sections(1), "s", "s.pdf", doc_info, {}, chunking_strategy="block")
        assert chunks[0].info["chunking_strategy"] == "block"
        assert "chunking_strategy" not in chunks[0].doc_info


# ---------------------------------------------------------------------------
# IngestionPipeline._embed_chunks
# ---------------------------------------------------------------------------

class TestEmbedChunks:

    def _chunk(self, content="Hello world"):
        return Chunk(
            content=content,
            source="doc",
            source_uri="doc.pdf",
            info={"path": "Intro"},
            doc_info={"title": "Doc"},
            access={},
        )

    def test_returns_one_vector_per_chunk(self, pipeline, mock_dense_encoder):
        mock_dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        chunks = [self._chunk()]
        vecs = pipeline._embed_chunks(chunks, {"title": "T"})
        assert len(vecs) == 1

    def test_truncates_long_text(self, pipeline, mock_dense_encoder):
        mock_dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        long_content = "X" * (IngestionPipeline._MAX_EMBED_CHARS + 1000)
        chunks = [self._chunk(content=long_content)]
        pipeline._embed_chunks(chunks, {"title": "T"})
        call_arg = mock_dense_encoder.encode_batch.call_args[0][0][0]
        assert len(call_arg) <= IngestionPipeline._MAX_EMBED_CHARS


# ---------------------------------------------------------------------------
# IngestionPipeline.ingest — integration with mocks
# ---------------------------------------------------------------------------

class TestIngest:

    def test_ingest_returns_result_with_collection(self, pipeline, tmp_path):
        # Create a minimal markdown file so SectionSplitter has something to split
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Section\nSome content here.")

        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = "# Section\nSome content."
        mock_parser.get_metadata.return_value = {"source": "doc", "source_uri": "doc.md"}
        mock_parser.close.return_value = None

        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1, 0.2])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]

        req = IngestionRequest(
            file_path=str(md_file),
            collection="test-col",
            tenants=["org1"],
        )

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            result = pipeline.ingest(req)

        assert result.collection == "test-col"
        assert result.n_chunks > 0
        mock_parser.close.assert_called_once()

    def test_closes_parser_even_when_reading_it_fails(self, pipeline, tmp_path):
        # Parsers can hold OS-level file locks (e.g. PDF/XLSX libraries); close()
        # must still run if to_markdown()/get_metadata() raises, so the temp
        # file can be deleted afterward (Windows locks files that are open).
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Section\nSome content here.")

        mock_parser = MagicMock()
        mock_parser.to_markdown.side_effect = RuntimeError("parse boom")
        mock_parser.close.return_value = None

        req = IngestionRequest(
            file_path=str(md_file),
            collection="test-col",
            tenants=["org1"],
        )

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            with pytest.raises(RuntimeError, match="parse boom"):
                pipeline.ingest(req)

        mock_parser.close.assert_called_once()

    def test_original_filename_overrides_temp_path_source(self, pipeline, tmp_path):
        # Sync Folder / upload flows may write to a temp path; the *original*
        # filename must end up in source / source_uri, not the temp one.
        tmp_file = tmp_path / "tmp_upload_ab12.md"
        tmp_file.write_text("# Section\nSome content.")

        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = "# Section\nSome content."
        mock_parser.get_metadata.return_value = {
            "source": "tmp_upload_ab12", "source_uri": str(tmp_file),
        }
        mock_parser.close.return_value = None

        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]

        req = IngestionRequest(
            file_path=str(tmp_file),
            collection="test-col",
            tenants=["org1"],
            original_filename="Real Report.md",
        )

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            result = pipeline.ingest(req)

        assert result.source == "Real Report"
        payload = pipeline.db.upsert.call_args[0][1][0]["payload"]
        assert payload["source"] == "Real Report"
        assert payload["source_uri"] == "Real Report.md"

    def test_metadata_overrides_are_applied_and_empty_values_ignored(self, pipeline, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Section\nSome content.")

        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = "# Section\nSome content."
        mock_parser.get_metadata.return_value = {
            "source": "doc", "source_uri": "doc.md", "title": "Original Title",
        }
        mock_parser.close.return_value = None

        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]

        req = IngestionRequest(
            file_path=str(md_file),
            collection="test-col",
            tenants=["org1"],
            metadata_overrides={"title": "User Edited Title", "author": ""},
        )

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            pipeline.ingest(req)

        payload = pipeline.db.upsert.call_args[0][1][0]["payload"]
        assert payload["doc_info"]["title"] == "User Edited Title"
        # An override with an empty-string value must not stomp existing metadata.
        assert "author" not in payload["doc_info"] or payload["doc_info"]["author"] != ""


# ---------------------------------------------------------------------------
# IngestionPipeline chunking strategy selection ("auto" / "section" / "block")
# ---------------------------------------------------------------------------

class TestChunkingStrategySelection:

    def _req(self, tmp_path, **overrides):
        md_file = tmp_path / "doc.md"
        md_file.write_text("placeholder")
        defaults = dict(file_path=str(md_file), collection="test-col", tenants=["org1"])
        defaults.update(overrides)
        return IngestionRequest(**defaults)

    def _mock_parser(self, body):
        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = body
        mock_parser.get_metadata.return_value = {"source": "doc", "source_uri": "doc.md"}
        mock_parser.close.return_value = None
        return mock_parser

    def _first_chunk_info_from_upsert(self, pipeline):
        points = pipeline.db.upsert.call_args[0][1]
        return points[0]["payload"]["info"]

    def test_auto_falls_back_to_block_for_headingless_document(self, pipeline, tmp_path):
        mock_parser = self._mock_parser("Dear Sir,\n\nThank you for your letter.")
        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]
        req = self._req(tmp_path)

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            result = pipeline.ingest(req)

        assert result.n_chunks > 0
        assert self._first_chunk_info_from_upsert(pipeline)["chunking_strategy"] == "block"

    def test_auto_keeps_section_strategy_when_headings_present(self, pipeline, tmp_path):
        mock_parser = self._mock_parser("# Section\nSome content.")
        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]
        req = self._req(tmp_path)

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            result = pipeline.ingest(req)

        assert result.n_chunks > 0
        assert self._first_chunk_info_from_upsert(pipeline)["chunking_strategy"] == "section"

    def test_forced_section_strategy_yields_zero_for_headingless_document(self, pipeline, tmp_path):
        mock_parser = self._mock_parser("Dear Sir,\n\nThank you for your letter.")
        req = self._req(tmp_path, chunking_strategy="section")

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            result = pipeline.ingest(req)

        assert result.n_chunks == 0

    def test_forced_block_strategy_used_even_when_headings_present(self, pipeline, tmp_path):
        mock_parser = self._mock_parser("# Section\nSome content.")
        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]
        req = self._req(tmp_path, chunking_strategy="block")

        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            result = pipeline.ingest(req)

        assert result.n_chunks > 0
        assert self._first_chunk_info_from_upsert(pipeline)["chunking_strategy"] == "block"

    def test_invalid_strategy_raises_validation_error(self, pipeline, tmp_path):
        req = self._req(tmp_path, chunking_strategy="nope")
        with pytest.raises(ValidationError, match="Unknown chunking strategy"):
            pipeline.ingest(req)


# ---------------------------------------------------------------------------
# IngestionPipeline.ingest — configurable chunk size (max_chars) / heading
# depth (max_depth)
# ---------------------------------------------------------------------------

class TestChunkSizeConfig:

    def _req(self, tmp_path, **overrides):
        md_file = tmp_path / "doc.md"
        md_file.write_text("placeholder")
        defaults = dict(file_path=str(md_file), collection="test-col", tenants=["org1"])
        defaults.update(overrides)
        return IngestionRequest(**defaults)

    def _mock_parser(self, body):
        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = body
        mock_parser.get_metadata.return_value = {"source": "doc", "source_uri": "doc.md"}
        mock_parser.close.return_value = None
        return mock_parser

    def _ingest(self, pipeline, tmp_path, body, req, n_vectors=1):
        mock_parser = self._mock_parser(body)
        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])] * n_vectors
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])] * n_vectors
        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            return pipeline.ingest(req)

    def test_max_chars_below_minimum_raises_validation_error(self, pipeline, tmp_path):
        req = self._req(tmp_path, max_chars=100)
        with pytest.raises(ValidationError, match="max_chars"):
            pipeline.ingest(req)

    def test_max_chars_above_maximum_raises_validation_error(self, pipeline, tmp_path):
        req = self._req(tmp_path, max_chars=1_000_000)
        with pytest.raises(ValidationError, match="max_chars"):
            pipeline.ingest(req)

    def test_max_depth_below_minimum_raises_validation_error(self, pipeline, tmp_path):
        req = self._req(tmp_path, max_depth=0)
        with pytest.raises(ValidationError, match="max_depth"):
            pipeline.ingest(req)

    def test_max_depth_above_maximum_raises_validation_error(self, pipeline, tmp_path):
        req = self._req(tmp_path, max_depth=7)
        with pytest.raises(ValidationError, match="max_depth"):
            pipeline.ingest(req)

    def test_small_max_chars_forces_additional_split(self, pipeline, tmp_path):
        body = "# Section\n" + ("A" * 150 + "\n\n" + "B" * 150)
        req = self._req(tmp_path, max_chars=210)

        result = self._ingest(pipeline, tmp_path, body, req, n_vectors=2)

        assert result.n_chunks == 2

    def test_default_max_chars_keeps_single_chunk(self, pipeline, tmp_path):
        body = "# Section\n" + ("A" * 150 + "\n\n" + "B" * 150)
        req = self._req(tmp_path)

        result = self._ingest(pipeline, tmp_path, body, req)

        assert result.n_chunks == 1

    def test_max_depth_override_collapses_nested_section(self, pipeline, tmp_path):
        body = "# H1\ncontent\n## H2\ncontent2"
        req = self._req(tmp_path, max_depth=1)

        result = self._ingest(pipeline, tmp_path, body, req)

        assert result.n_chunks == 1

    def test_default_max_depth_keeps_nested_sections_separate(self, pipeline, tmp_path):
        body = "# H1\ncontent\n## H2\ncontent2"
        req = self._req(tmp_path)

        result = self._ingest(pipeline, tmp_path, body, req, n_vectors=2)

        assert result.n_chunks == 2


# ---------------------------------------------------------------------------
# IngestionPipeline.ingest — default classification when unresolved
# ---------------------------------------------------------------------------

class TestClassificationDefault:
    """A Qdrant range filter (access.classification <= max_cls) excludes
    points where the field is null, so a document with no resolvable
    classification label must never be stored with classification=None --
    it would become silently invisible to every classification-filtered
    search. It defaults to Internal (not Public) so unclassified content
    isn't exposed until someone consciously marks it Public. doc_info.
    classification (read by the metadata overview) must carry the same
    default, since it's a separate string field from access.classification."""

    def _req(self, tmp_path, **overrides):
        md_file = tmp_path / "doc.md"
        md_file.write_text("placeholder")
        defaults = dict(file_path=str(md_file), collection="test-col", tenants=["org1"])
        defaults.update(overrides)
        return IngestionRequest(**defaults)

    def _ingest(self, pipeline, tmp_path, metadata, req=None):
        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = "# Section\nSome content."
        mock_parser.get_metadata.return_value = metadata
        mock_parser.close.return_value = None
        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]
        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            pipeline.ingest(req or self._req(tmp_path))
        return pipeline.db.upsert.call_args[0][1][0]["payload"]

    def test_defaults_to_internal_when_no_label_matches(self, pipeline, tmp_path):
        metadata = {"source": "doc", "source_uri": "doc.md", "title": "Untitled"}
        payload = self._ingest(pipeline, tmp_path, metadata)
        assert payload["access"]["classification"] == Classification.INTERNAL.level
        assert payload["doc_info"]["classification"] == "internal"

    def test_explicit_label_still_wins_over_default(self, pipeline, tmp_path):
        metadata = {"source": "doc", "source_uri": "doc.md", "classification": "confidential"}
        payload = self._ingest(pipeline, tmp_path, metadata)
        assert payload["access"]["classification"] == Classification.CONFIDENTIAL.level
        assert payload["doc_info"]["classification"] == "confidential"

    def test_explicit_public_label_is_respected(self, pipeline, tmp_path):
        metadata = {"source": "doc", "source_uri": "doc.md", "classification": "public"}
        payload = self._ingest(pipeline, tmp_path, metadata)
        assert payload["access"]["classification"] == Classification.PUBLIC.level
        assert payload["doc_info"]["classification"] == "public"


# ---------------------------------------------------------------------------
# IngestionPipeline.ingest — default language when unresolved
# ---------------------------------------------------------------------------

class TestLanguageDefault:
    """The interactive upload flow always resolves a language (required
    field); Sync Folder auto-ingestion can send an empty one. Both the
    sparse-encoder stemmer language and doc_info.lang (read by the metadata
    overview) must default to 'english' rather than staying blank."""

    def _req(self, tmp_path, **overrides):
        md_file = tmp_path / "doc.md"
        md_file.write_text("placeholder")
        defaults = dict(file_path=str(md_file), collection="test-col", tenants=["org1"])
        defaults.update(overrides)
        return IngestionRequest(**defaults)

    def _ingest(self, pipeline, tmp_path, metadata, req=None):
        mock_parser = MagicMock()
        mock_parser.to_markdown.return_value = "# Section\nSome content."
        mock_parser.get_metadata.return_value = metadata
        mock_parser.close.return_value = None
        pipeline.dense_encoder.encode_batch.return_value = [DenseVector(vector=[0.1])]
        pipeline.sparse_encoder.encode_documents.return_value = [SparseVector(indices=[0], values=[1.0])]
        with patch.object(pipeline, "_get_parser", return_value=mock_parser):
            pipeline.ingest(req or self._req(tmp_path))
        return pipeline.db.upsert.call_args[0][1][0]["payload"]

    def test_defaults_doc_info_lang_when_request_language_empty(self, pipeline, tmp_path):
        metadata = {"source": "doc", "source_uri": "doc.md"}
        payload = self._ingest(pipeline, tmp_path, metadata, req=self._req(tmp_path, language=""))
        assert payload["doc_info"]["lang"] == "english"

    def test_passes_default_language_to_sparse_encoder(self, pipeline, tmp_path):
        metadata = {"source": "doc", "source_uri": "doc.md"}
        self._ingest(pipeline, tmp_path, metadata, req=self._req(tmp_path, language=""))
        assert pipeline.sparse_encoder.encode_documents.call_args.kwargs["language"] == "english"

    def test_parsed_lang_metadata_is_not_overridden(self, pipeline, tmp_path):
        metadata = {"source": "doc", "source_uri": "doc.md", "lang": "german"}
        payload = self._ingest(pipeline, tmp_path, metadata, req=self._req(tmp_path, language=""))
        assert payload["doc_info"]["lang"] == "german"
