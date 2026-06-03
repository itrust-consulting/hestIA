from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hestia.domain.rag.services import (
    DenseEncoder,
    Generator,
    Retriever,
    SparseEncoder,
    _CorpusStats,
)
from hestia.domain.rag.types import DenseVector, SparseVector


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class TestGenerator:

    def test_uses_default_model_when_none_given(self):
        provider = MagicMock()
        provider.generate.return_value = "response"
        gen = Generator(provider=provider, model="default-model")
        gen.generate("hello")
        provider.generate.assert_called_once()
        _, kwargs = provider.generate.call_args
        assert kwargs["model"] == "default-model"

    def test_explicit_model_overrides_default(self):
        provider = MagicMock()
        provider.generate.return_value = "r"
        gen = Generator(provider=provider, model="default")
        gen.generate("hi", model="override")
        _, kwargs = provider.generate.call_args
        assert kwargs["model"] == "override"

    def test_chat_uses_default_model(self):
        provider = MagicMock()
        provider.chat.return_value = "msg"
        gen = Generator(provider=provider, model="chat-model")
        gen.chat([{"role": "user", "content": "hi"}])
        _, kwargs = provider.chat.call_args
        assert kwargs["model"] == "chat-model"


# ---------------------------------------------------------------------------
# DenseEncoder
# ---------------------------------------------------------------------------

class TestDenseEncoder:

    def _provider(self, vectors=None):
        p = MagicMock()
        p.embed.return_value = vectors or [[0.1, 0.2, 0.3]]
        return p

    def test_encode_single_string_returns_dense_vector(self):
        enc = DenseEncoder(provider=self._provider(), model="emb")
        vec = enc.encode("hello world")
        assert isinstance(vec, DenseVector)
        assert vec.vector == [0.1, 0.2, 0.3]

    def test_encode_normalizes_str_to_list(self):
        p = self._provider()
        enc = DenseEncoder(provider=p, model="emb")
        enc.encode("single")
        call_args = p.embed.call_args[0][0]
        assert isinstance(call_args, list)

    def test_encode_batch_returns_list_of_dense_vectors(self):
        p = self._provider(vectors=[[0.1], [0.2]])
        enc = DenseEncoder(provider=p, model="emb")
        result = enc.encode_batch(["a", "b"])
        assert len(result) == 2
        assert all(isinstance(v, DenseVector) for v in result)


# ---------------------------------------------------------------------------
# SparseEncoder — pure logic (no filesystem)
# ---------------------------------------------------------------------------

class TestSparseEncoderCacheKey:

    def test_strips_whitespace(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        assert enc._cache_key(" my corpus ") == "my_corpus"

    def test_replaces_spaces_with_underscores(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        assert enc._cache_key("my corpus name") == "my_corpus_name"


class TestSparseEncoderTokenize:

    @pytest.fixture
    def enc(self, tmp_path):
        return SparseEncoder(corpus_dir=tmp_path)

    def test_builds_vocabulary(self, enc):
        ids, vocab = enc._tokenize(["hello world"])
        assert "hello" in vocab
        assert "world" in vocab

    def test_unique_ids_per_token(self, enc):
        ids, vocab = enc._tokenize(["hello world"])
        assert vocab["hello"] != vocab["world"]

    def test_repeated_token_same_id(self, enc):
        ids, vocab = enc._tokenize(["hello hello"])
        assert ids[0].count(vocab["hello"]) == 2

    def test_multitext_shares_vocab(self, enc):
        ids, vocab = enc._tokenize(["hello world", "world foo"])
        assert "world" in vocab


class TestSparseEncoderTokenizeExtend:

    @pytest.fixture
    def enc(self, tmp_path):
        return SparseEncoder(corpus_dir=tmp_path)

    def test_extends_existing_vocab(self, enc):
        import Stemmer
        stemmer = Stemmer.Stemmer("english")
        vocab = {"hello": 0}
        enc._tokenize_extend(["world"], vocab, stemmer)
        assert len(vocab) > 1

    def test_does_not_overwrite_existing_ids(self, enc):
        import Stemmer
        stemmer = Stemmer.Stemmer("english")
        vocab = {"hello": 42}
        enc._tokenize_extend(["hello"], vocab, stemmer)
        assert vocab["hello"] == 42


class TestSparseEncoderLoadOrEmpty:

    def test_returns_empty_stats_when_no_file(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        stats = enc._load_or_empty("nonexistent")
        assert stats.N == 0
        assert stats.total_tokens == 0
        assert stats.vocab == {}


class TestSparseEncoderBuildQueryVector:

    def test_returns_sparse_vector(self, tmp_path):
        import Stemmer
        enc = SparseEncoder(corpus_dir=tmp_path)
        stemmer = Stemmer.Stemmer("english")
        stats = _CorpusStats(vocab={"hello": 0, "world": 1}, N=10, total_tokens=100,
                             df={0: 3, 1: 5})
        vec = enc._build_query_vector("hello world", stats, stemmer)
        assert isinstance(vec, SparseVector)
        assert len(vec.indices) > 0
        assert len(vec.values) == len(vec.indices)

    def test_unknown_tokens_excluded(self, tmp_path):
        import Stemmer
        enc = SparseEncoder(corpus_dir=tmp_path)
        stemmer = Stemmer.Stemmer("english")
        stats = _CorpusStats(vocab={}, N=10, total_tokens=100, df={})
        vec = enc._build_query_vector("unknown token", stats, stemmer)
        assert vec.indices == []
        assert vec.values == []


class TestSparseEncoderEncodeDocuments:

    def test_round_trip_encode_decode(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        vecs = enc.encode_documents(
            ["hello world", "foo bar baz"],
            corpus_name="test_col",
            source_uri="doc.pdf",
        )
        assert len(vecs) == 2
        assert all(isinstance(v, SparseVector) for v in vecs)
        # File should have been created
        assert (tmp_path / "test_col.json").exists()

    def test_updates_corpus_stats(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        enc.encode_documents(["hello world"], corpus_name="test_col", source_uri="doc.pdf")
        stats = enc._load("test_col")
        assert stats.N == 1
        assert "hello" in stats.vocab or any("hello" in k for k in stats.vocab)


class TestSparseEncoderRemoveDocument:

    def test_remove_reduces_chunk_count(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        enc.encode_documents(["hello world"], corpus_name="col", source_uri="doc.pdf")
        enc.remove_document("doc.pdf", "col")
        stats = enc._load("col")
        assert stats.N == 0

    def test_remove_nonexistent_doc_is_noop(self, tmp_path):
        enc = SparseEncoder(corpus_dir=tmp_path)
        enc.encode_documents(["hello"], corpus_name="col", source_uri="real.pdf")
        # Should not raise
        enc.remove_document("missing.pdf", "col")


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class TestRetriever:

    def test_delegates_to_provider(self):
        provider = MagicMock()
        mock_result = MagicMock()
        mock_result.points = [MagicMock()]
        provider.search.return_value = mock_result

        retriever = Retriever(provider=provider)
        result = retriever.retrieve("my-col", MagicMock())
        provider.search.assert_called_once()
        assert result is mock_result
