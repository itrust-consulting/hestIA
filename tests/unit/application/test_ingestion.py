from __future__ import annotations

import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hestia.application.ingestion import IngestionPipeline, IngestionRequest
from hestia.domain.rag.chunk import Chunk
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
        assert chunks[1].previous == chunks[0].id


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
