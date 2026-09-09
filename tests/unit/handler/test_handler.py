from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hestia.handler import (
    PersistChat,
    RequestHandler,
    Runner,
    _build_prompt,
    _extract_used_citekeys,
    _format_citations,
    _normalize_citekey,
)
from hestia.domain.exceptions import ConfigurationError, ForbiddenError
from hestia.domain.policies.guard import PolicyDecision, PolicyResult
from hestia.domain.rag.graph import ExecutionGraph, ExecutionRequest, Node
from hestia.domain.rag.types import DenseVector, HybridQuery, SparseVector
from tests.unit.conftest import _make_user


def _generator_double(chat_return=None, default_model="test-model"):
    """A Generator connection double with no per-connection compaction
    overrides set, so context-budget math falls back to whatever settings
    are configured on the container -- matching a real Generator's unset
    compaction_context_window/compaction_summary_length/compaction_model."""
    g = MagicMock()
    g.compaction_enabled = True
    g.compaction_context_window = None
    g.compaction_summary_length = None
    g.compaction_model = None
    g.default_model = default_model
    g.chat = AsyncMock(return_value=chat_return)
    return g


# ---------------------------------------------------------------------------
# _normalize_citekey
# ---------------------------------------------------------------------------

class TestNormalizeCitekey:

    def test_lowercases(self):
        assert _normalize_citekey("ABC") == "abc"

    def test_strips_non_alphanum(self):
        assert _normalize_citekey("1,2") == "12"

    def test_strips_spaces(self):
        assert _normalize_citekey("key one") == "keyone"

    def test_numeric_only(self):
        assert _normalize_citekey("42") == "42"


# ---------------------------------------------------------------------------
# _extract_used_citekeys
# ---------------------------------------------------------------------------

class TestExtractUsedCitekeys:

    def test_extracts_single_cite(self):
        keys = _extract_used_citekeys(r"See \cite{1} for details.")
        assert "1" in keys

    def test_extracts_multi_key_cite(self):
        keys = _extract_used_citekeys(r"\cite{1,2,3}")
        assert keys == {"1", "2", "3"}

    def test_no_cites_returns_empty(self):
        keys = _extract_used_citekeys("No citations here.")
        assert keys == set()

    def test_deduplicates(self):
        keys = _extract_used_citekeys(r"\cite{1} and \cite{1}")
        assert keys == {"1"}


# ---------------------------------------------------------------------------
# _format_citations
# ---------------------------------------------------------------------------

class TestFormatCitations:

    def _make_point(self, source, content, path="intro", subject="doc"):
        p = MagicMock()
        p.payload = {
            "source": source,
            "content": content,
            "doc_info": {"subject": subject},
            "info": {"path": path},
        }
        return p

    def test_gives_every_chunk_its_own_key_even_when_source_repeats(self):
        # Two chunks from the same document must get DISTINCT keys so the
        # model can cite them individually for different facts -- if both
        # got "1", the model could never point at just one of them.
        hits = [
            self._make_point("docA", "chunk1"),
            self._make_point("docA", "chunk2"),
            self._make_point("docB", "chunk3"),
        ]
        _, cite_list = _format_citations(hits)
        assert len(cite_list) == 3
        keys = [c["key"] for c in cite_list]
        assert keys == ["1", "2", "3"]
        excerpts = [c["excerpt"] for c in cite_list]
        assert excerpts == ["chunk1", "chunk2", "chunk3"]

    def test_keys_are_sequential(self):
        hits = [
            self._make_point("a", "x"),
            self._make_point("b", "y"),
        ]
        _, cite_list = _format_citations(hits)
        keys = [c["key"] for c in cite_list]
        assert keys == ["1", "2"]

    def test_retrieved_data_contains_content(self):
        hits = [self._make_point("docA", "important text")]
        formatted, _ = _format_citations(hits)
        assert "important text" in formatted["retrieved_data"]

    def test_source_map_contains_key(self):
        hits = [self._make_point("docA", "x")]
        formatted, _ = _format_citations(hits)
        assert "1: docA" in formatted["source_map"]


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:

    def test_no_hits_renders_template_with_empty_retrieved_sections(self):
        prompt, cites = _build_prompt("original", [], "{user_prompt}{retrieved_data}{source_map}")
        assert prompt == "original"
        assert cites == []

    def test_no_hits_with_attachments_goes_through_template_placeholder(self):
        template = "{user_prompt} | attachments=[{attached_documents}] | data=[{retrieved_data}]"
        prompt, cites = _build_prompt("original", [], template, attachments="doc.txt")
        assert prompt == "original | attachments=[doc.txt] | data=[]"
        assert cites == []

    def test_with_hits_augments_prompt(self):
        point = MagicMock()
        point.payload = {
            "source": "doc", "content": "chunk",
            "doc_info": {}, "info": {},
        }
        template = "{user_prompt}\n{retrieved_data}\n{source_map}"
        prompt, cites = _build_prompt("user question", [point], template)
        assert "user question" in prompt
        assert "chunk" in prompt
        assert len(cites) == 1


# ---------------------------------------------------------------------------
# Runner._linear_order
# ---------------------------------------------------------------------------

class TestRunnerLinearOrder:

    def _graph(self, node_ids, edges=None):
        nodes = [Node(id=nid, type="Generate", inputs={}, outputs={}) for nid in node_ids]
        if edges is None and len(node_ids) > 1:
            edges = [(node_ids[i], node_ids[i + 1]) for i in range(len(node_ids) - 1)]
        elif edges is None:
            edges = []
        return ExecutionGraph(
            nodes=nodes, edges=edges,
            entrypoint=node_ids[0], exitpoints=[node_ids[-1]],
        )

    def test_linear_three_nodes(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["A", "B", "C"])
        order = runner._linear_order(graph)
        assert order == ["A", "B", "C"]

    def test_single_node(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["X"])
        order = runner._linear_order(graph)
        assert order == ["X"]

    def test_no_edges_uses_node_list_order(self):
        runner = Runner(container=MagicMock())
        nodes = [Node(id=nid, type="Generate", inputs={}, outputs={}) for nid in ["A", "B"]]
        graph = ExecutionGraph(nodes=nodes, edges=[], entrypoint="A", exitpoints=["B"])
        order = runner._linear_order(graph)
        assert order == ["A", "B"]


# ---------------------------------------------------------------------------
# Runner._resolve
# ---------------------------------------------------------------------------

class TestRunnerResolve:

    runner = Runner(container=MagicMock())

    def test_literal_value_returned_unchanged(self):
        assert self.runner._resolve("hello", {}) == "hello"

    def test_slot_reference_resolved(self):
        assert self.runner._resolve("?mykey", {"mykey": "value"}) == "value"

    def test_missing_slot_returns_none(self):
        assert self.runner._resolve("?missing", {}) is None

    def test_none_value_returned_unchanged(self):
        assert self.runner._resolve(None, {}) is None


# ---------------------------------------------------------------------------
# Runner._next_of
# ---------------------------------------------------------------------------

class TestRunnerNextOf:

    runner = Runner(container=MagicMock())

    def _graph(self, edges):
        nodes = [Node(id=nid, type="Generate", inputs={}, outputs={}) for nid in ["A", "B", "C"]]
        return ExecutionGraph(nodes=nodes, edges=edges, entrypoint="A", exitpoints=["C"])

    def test_finds_successor(self):
        graph = self._graph([("A", "B"), ("B", "C")])
        assert self.runner._next_of(graph, "A") == "B"
        assert self.runner._next_of(graph, "B") == "C"

    def test_returns_none_at_end(self):
        graph = self._graph([("A", "B")])
        assert self.runner._next_of(graph, "B") is None


# ---------------------------------------------------------------------------
# Runner.run — node orchestration
# ---------------------------------------------------------------------------

class TestRunnerRun:

    def _graph(self, node_ids, edges=None):
        nodes = [Node(id=nid, type=nid, inputs={}, outputs={}) for nid in node_ids]
        if edges is None and len(node_ids) > 1:
            edges = [(node_ids[i], node_ids[i + 1]) for i in range(len(node_ids) - 1)]
        elif edges is None:
            edges = []
        return ExecutionGraph(nodes=nodes, edges=edges, entrypoint=node_ids[0], exitpoints=[node_ids[-1]])

    def test_calls_all_but_last_node_with_stream_false(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["A", "B", "C"])
        handler_a, handler_b, handler_c = AsyncMock(), AsyncMock(), AsyncMock()
        runner.node_handlers = {"A": handler_a, "B": handler_b, "C": handler_c}

        asyncio.run(runner.run(graph, stream=True))

        assert handler_a.call_args.kwargs["stream"] is False
        assert handler_b.call_args.kwargs["stream"] is False

    def test_returns_slot_final_when_not_streaming(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["A"])

        async def _set_final(node, slot, stream):
            slot["final"] = "answer"

        runner.node_handlers = {"A": _set_final}

        result, slot = asyncio.run(runner.run(graph, stream=False))
        assert result == "answer"
        assert slot["final"] == "answer"

    def test_streaming_returns_final_handler_result_directly(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["A"])
        sentinel = object()
        handler_a = AsyncMock(return_value=sentinel)
        runner.node_handlers = {"A": handler_a}

        result, _ = asyncio.run(runner.run(graph, stream=True))
        assert result is sentinel
        assert handler_a.call_args.kwargs["stream"] is True

    def test_raises_configuration_error_for_unknown_middle_node_type(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["A", "B"])
        runner.node_handlers = {"B": AsyncMock()}  # "A" (middle) missing
        with pytest.raises(ConfigurationError):
            asyncio.run(runner.run(graph, stream=False))

    def test_raises_configuration_error_for_unknown_final_node_type(self):
        runner = Runner(container=MagicMock())
        graph = self._graph(["A", "B"])
        runner.node_handlers = {"A": AsyncMock()}  # "B" (final) missing
        with pytest.raises(ConfigurationError):
            asyncio.run(runner.run(graph, stream=False))


# ---------------------------------------------------------------------------
# Runner._run_encode_dense / _run_encode_sparse
# ---------------------------------------------------------------------------

class TestRunEncodeDense:

    def _runner(self, svc):
        container = MagicMock()
        container.services = {"encDense": svc}
        return Runner(container=container)

    def test_writes_result_to_default_output_key(self):
        svc = MagicMock()
        svc.encode = AsyncMock(return_value=DenseVector(vector=[0.1]))
        runner = self._runner(svc)
        node = Node(id="n1", type="EncodeDense", inputs={"data": "hello"}, outputs={})
        slot = {}

        asyncio.run(runner._run_encode_dense(node, slot, stream=False))

        assert slot["vector"] == DenseVector(vector=[0.1])
        svc.encode.assert_awaited_once_with("hello", model=None, options=None)

    def test_writes_result_to_custom_output_key(self):
        svc = MagicMock()
        svc.encode = AsyncMock(return_value=DenseVector(vector=[0.2]))
        runner = self._runner(svc)
        node = Node(id="n1", type="EncodeDense", inputs={"data": "hi"}, outputs={"vector": "dense_out"})
        slot = {}

        asyncio.run(runner._run_encode_dense(node, slot, stream=False))

        assert slot["dense_out"] == DenseVector(vector=[0.2])

    def test_resolves_slot_reference_input(self):
        svc = MagicMock()
        svc.encode = AsyncMock(return_value=DenseVector(vector=[0.3]))
        runner = self._runner(svc)
        node = Node(id="n1", type="EncodeDense", inputs={"data": "?raw"}, outputs={})
        slot = {"raw": "resolved text"}

        asyncio.run(runner._run_encode_dense(node, slot, stream=False))

        svc.encode.assert_awaited_once_with("resolved text", model=None, options=None)


class TestRunEncodeSparse:

    def test_passes_data_and_collection_and_writes_result(self):
        svc = MagicMock()
        svc.encode.return_value = SparseVector(indices=[0, 1], values=[0.5, 0.3])
        container = MagicMock()
        container.services = {"encSparse": svc}
        runner = Runner(container=container)
        node = Node(id="n1", type="EncodeSparse", inputs={"data": "hello", "collection": "col"}, outputs={})
        slot = {}

        asyncio.run(runner._run_encode_sparse(node, slot, stream=False))

        svc.encode.assert_called_once_with("hello", "col")
        assert slot["vector"] == SparseVector(indices=[0, 1], values=[0.5, 0.3])

    def test_writes_result_to_custom_output_key(self):
        svc = MagicMock()
        svc.encode.return_value = SparseVector(indices=[], values=[])
        container = MagicMock()
        container.services = {"encSparse": svc}
        runner = Runner(container=container)
        node = Node(id="n1", type="EncodeSparse", inputs={"data": "hi", "collection": "col"}, outputs={"vector": "sparse_out"})
        slot = {}

        asyncio.run(runner._run_encode_sparse(node, slot, stream=False))

        assert slot["sparse_out"] == SparseVector(indices=[], values=[])

    def test_encode_is_offloaded_to_a_thread_not_run_on_the_event_loop(self):
        # Regression test: svc.encode is synchronous, CPU-bound BM25
        # tokenize+score work and used to run directly on the event loop.
        svc = MagicMock()
        svc.encode.return_value = SparseVector(indices=[0], values=[1.0])
        container = MagicMock()
        container.services = {"encSparse": svc}
        runner = Runner(container=container)
        node = Node(id="n1", type="EncodeSparse", inputs={"data": "hello", "collection": "col"}, outputs={})
        slot = {}

        with patch("hestia.handler.asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
            asyncio.run(runner._run_encode_sparse(node, slot, stream=False))

        mock_to_thread.assert_awaited_once()
        assert mock_to_thread.await_args.args[0] == svc.encode
        assert slot["vector"] == SparseVector(indices=[0], values=[1.0])


# ---------------------------------------------------------------------------
# Runner._run_retrieve
# ---------------------------------------------------------------------------

class TestRunRetrieve:

    def _runner(self, svc):
        container = MagicMock()
        container.services = {"search": svc}
        return Runner(container=container)

    def _mock_result(self, points):
        result = MagicMock()
        result.points = points
        return result

    def test_dense_only_query(self):
        svc = MagicMock()
        points = [MagicMock()]
        svc.retrieve = AsyncMock(return_value=self._mock_result(points))
        runner = self._runner(svc)
        dense = DenseVector(vector=[0.1])
        node = Node(id="n1", type="Retrieve", inputs={"dense": dense, "collection": "col"}, outputs={})
        slot = {}

        asyncio.run(runner._run_retrieve(node, slot, stream=False))

        args, _ = svc.retrieve.call_args
        assert args[0] == "col"
        assert args[1] == dense
        assert slot["hits"] == points

    def test_sparse_only_query(self):
        svc = MagicMock()
        svc.retrieve = AsyncMock(return_value=self._mock_result([]))
        runner = self._runner(svc)
        sparse = SparseVector(indices=[0], values=[1.0])
        node = Node(id="n1", type="Retrieve", inputs={"sparse": sparse, "collection": "col"}, outputs={})
        slot = {}

        asyncio.run(runner._run_retrieve(node, slot, stream=False))

        args, _ = svc.retrieve.call_args
        assert args[1] == sparse

    def test_hybrid_query_when_both_present(self):
        svc = MagicMock()
        svc.retrieve = AsyncMock(return_value=self._mock_result([]))
        runner = self._runner(svc)
        dense = DenseVector(vector=[0.1])
        sparse = SparseVector(indices=[0], values=[1.0])
        node = Node(id="n1", type="Retrieve", inputs={"dense": dense, "sparse": sparse, "collection": "col"}, outputs={})
        slot = {}

        asyncio.run(runner._run_retrieve(node, slot, stream=False))

        args, _ = svc.retrieve.call_args
        assert isinstance(args[1], HybridQuery)
        assert args[1].dense == dense
        assert args[1].sparse == sparse

    def test_raises_configuration_error_when_no_query_vector(self):
        svc = MagicMock()
        runner = self._runner(svc)
        node = Node(id="n1", type="Retrieve", inputs={"collection": "col"}, outputs={})

        with pytest.raises(ConfigurationError):
            asyncio.run(runner._run_retrieve(node, {}, stream=False))

    def test_hits_points_written_to_custom_output_key(self):
        svc = MagicMock()
        points = [MagicMock(), MagicMock()]
        svc.retrieve = AsyncMock(return_value=self._mock_result(points))
        runner = self._runner(svc)
        dense = DenseVector(vector=[0.1])
        node = Node(id="n1", type="Retrieve", inputs={"dense": dense}, outputs={"hits": "results"})
        slot = {}

        asyncio.run(runner._run_retrieve(node, slot, stream=False))

        assert slot["results"] == points


# ---------------------------------------------------------------------------
# Runner._run_augment
# ---------------------------------------------------------------------------

class TestRunAugment:

    def test_no_hits_still_applies_default_template(self):
        runner = Runner(container=MagicMock())
        node = Node(id="n1", type="Augment", inputs={"prompt": "hello", "hits": []}, outputs={})
        slot = {}

        asyncio.run(runner._run_augment(node, slot, stream=False))

        assert "hello" in slot["prompt"]
        assert slot["prompt"] != "hello"  # still wrapped in the default template
        assert slot["_cite_list"] == []

    def test_no_hits_with_custom_non_rag_template_applies_it(self):
        # An Augment node doesn't have to be RAG-flavored -- a template with
        # no {retrieved_data}/{source_map} at all must still render even
        # when there's no Retrieve node feeding hits (see graph.py's
        # _REQUIRED_AUGMENT_PLACEHOLDERS).
        runner = Runner(container=MagicMock())
        node = Node(
            id="n1", type="Augment",
            inputs={"prompt": "hello", "hits": [], "template": "Rewritten: {user_prompt}"},
            outputs={},
        )
        slot = {}

        asyncio.run(runner._run_augment(node, slot, stream=False))

        assert slot["prompt"] == "Rewritten: hello"
        assert slot["_cite_list"] == []

    def test_with_hits_sets_prompt_and_cite_list(self):
        runner = Runner(container=MagicMock())
        point = MagicMock()
        point.payload = {"source": "docA", "content": "chunk text", "doc_info": {}, "info": {}}
        node = Node(id="n1", type="Augment", inputs={"prompt": "question", "hits": [point]}, outputs={})
        slot = {}

        asyncio.run(runner._run_augment(node, slot, stream=False))

        assert "question" in slot["prompt"]
        assert "chunk text" in slot["prompt"]
        assert len(slot["_cite_list"]) == 1


# ---------------------------------------------------------------------------
# Runner._run_generate / _run_chat
# ---------------------------------------------------------------------------

class TestRunGenerate:

    def _runner(self, svc):
        container = MagicMock()
        container.services = {"generate": svc}
        return Runner(container=container)

    def test_non_streaming_writes_response_and_final(self):
        svc = MagicMock()
        svc.generate = AsyncMock(return_value="answer")
        runner = self._runner(svc)
        node = Node(id="n1", type="Generate",
                    inputs={"prompt": "hi", "model": "m1", "options": {"temp": 0.1}}, outputs={})
        slot = {}

        asyncio.run(runner._run_generate(node, slot, stream=False))

        assert slot["response"] == "answer"
        assert slot["final"] == "answer"
        svc.generate.assert_awaited_once_with(prompt="hi", model="m1", options={"temp": 0.1}, stream=False)

    def test_streaming_returns_handler_result_without_touching_slot(self):
        svc = MagicMock()
        sentinel = object()
        svc.generate = AsyncMock(return_value=sentinel)
        runner = self._runner(svc)
        node = Node(id="n1", type="Generate", inputs={"prompt": "hi"}, outputs={})
        slot = {}

        result = asyncio.run(runner._run_generate(node, slot, stream=True))

        assert result is sentinel
        assert "final" not in slot
        assert "response" not in slot
        svc.generate.assert_awaited_once_with(prompt="hi", model=None, options=None, stream=True)


class TestRunChat:

    def _runner(self, svc):
        container = MagicMock()
        container.services = {"generate": svc}
        return Runner(container=container)

    def test_builds_messages_from_history_and_last_message(self):
        svc = MagicMock()
        svc.chat = AsyncMock(return_value="reply")
        runner = self._runner(svc)
        node = Node(id="n1", type="Chat", inputs={"history": "?hist", "last_user_message": "?last"}, outputs={})
        slot = {"hist": [{"role": "user", "content": "prev"}], "last": "current question"}

        asyncio.run(runner._run_chat(node, slot, stream=False))

        svc.chat.assert_awaited_once_with(
            messages=[{"role": "user", "content": "prev"}, {"role": "user", "content": "current question"}],
            model=None, options=None, stream=False,
        )
        assert slot["response"] == "reply"
        assert slot["final"] == "reply"

    def test_streaming_returns_handler_result_directly(self):
        svc = MagicMock()
        sentinel = object()
        svc.chat = AsyncMock(return_value=sentinel)
        runner = self._runner(svc)
        node = Node(id="n1", type="Chat", inputs={"last_user_message": "hi"}, outputs={})
        slot = {}

        result = asyncio.run(runner._run_chat(node, slot, stream=True))

        assert result is sentinel
        assert "final" not in slot


# ---------------------------------------------------------------------------
# Runner._svc
# ---------------------------------------------------------------------------

class TestSvc:

    def test_returns_registered_service(self):
        svc = MagicMock()
        container = MagicMock()
        container.services = {"generate": svc}
        runner = Runner(container=container)
        assert runner._svc("generate") is svc

    def test_raises_configuration_error_when_service_missing(self):
        container = MagicMock()
        container.services = {}
        runner = Runner(container=container)
        with pytest.raises(ConfigurationError):
            runner._svc("generate")


# ---------------------------------------------------------------------------
# PersistChat._wrap_stream — <think> tag stripping
# ---------------------------------------------------------------------------

class TestWrapStream:

    def _make_persist_chat(self, generator=None):
        from hestia.handler import PersistChat
        runner = MagicMock()
        req = MagicMock()
        req.user.id = uuid.uuid4()
        req.conversation_id = None
        req.last_user_message = "hi"
        req.last_user_display_content = None
        req.last_user_attachments = None
        req.conversation_title = None
        req.model_kwargs = {}
        req.freed_tokens = None

        if generator is None:
            generator = _generator_double()

        users_svc = MagicMock()
        users_svc.create_user_conversation.return_value = uuid.uuid4()
        users_svc.append_conversation_message.return_value = uuid.uuid4()
        runner.container.services.get.side_effect = lambda name: {"users": users_svc, "generate": generator}.get(name)
        runner.container.require_service.side_effect = lambda name: {"users": users_svc, "generate": generator}.get(name)

        pc = PersistChat(runner=runner, req=req)
        pc.users = users_svc
        return pc, req

    async def _aiter(self, items):
        for item in items:
            yield item

    async def _collect(self, agen):
        return [chunk async for chunk in agen]

    def test_content_outside_think_tags_yields_content(self):
        pc, req = self._make_persist_chat()
        chunks = ["Hello ", "world"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        # Check that content events were yielded
        import json
        contents = []
        for chunk in output[:-1]:  # last is metadata
            data = json.loads(chunk.decode())
            if "content" in data:
                contents.append(data["content"])
        assert "Hello " in contents or any("Hello" in c for c in contents)

    def test_think_tags_routed_to_thinking_stream(self):
        import json
        pc, req = self._make_persist_chat()
        chunks = ["<think>internal reasoning</think>answer"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        thinking_chunks = []
        for chunk in output[:-1]:
            data = json.loads(chunk.decode())
            if "thinking" in data:
                thinking_chunks.append(data["thinking"])
        assert any("internal reasoning" in t for t in thinking_chunks)

    def test_last_chunk_contains_conversation_id(self):
        import json
        pc, req = self._make_persist_chat()
        chunks = ["hello"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        last = json.loads(output[-1].decode())
        assert "conversation_id" in last

    def test_last_chunk_carries_usage_fields_when_computable(self):
        import json
        pc, req = self._make_persist_chat()
        pc.users.assert_conversation_owner = MagicMock()
        pc.users.get_conversation_context_state.return_value = {}
        pc.users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        pc.runner.container.settings.max_context_tokens = 32000
        pc.runner.container.settings.summary_target_tokens = 6000

        chunks = ["hello"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        last = json.loads(output[-1].decode())

        assert last["used_tokens"] > 0
        assert last["max_tokens"] == 32000
        assert last["needs_compaction"] is False

    def test_usage_fields_absent_but_stream_survives_when_computation_fails(self):
        # pc.users.assert_conversation_owner is left unstubbed here, which
        # raises inside a bare MagicMock (see fail-open comment in handler.py)
        # -- the stream must still complete and yield its final frame.
        import json
        pc, req = self._make_persist_chat()
        chunks = ["hello"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        last = json.loads(output[-1].decode())
        assert "used_tokens" not in last

    def test_over_budget_after_persist_reports_needs_compaction_without_compacting(self):
        # Auto-compaction never runs as part of finishing this turn -- it
        # only fires at the start of a later turn (see
        # RequestHandler._check_and_compact_budget /
        # TestStreamWithBudgetNotice). If this reply pushed the conversation
        # over budget, the final frame must say so (needs_compaction: True)
        # without actually folding anything itself.
        import json
        generator = _generator_double(chat_return="a concise summary")
        pc, req = self._make_persist_chat(generator=generator)
        pc.users.assert_conversation_owner = MagicMock()
        pc.users.get_conversation_context_state.return_value = {}
        big_tail = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 100,
             "created_at": i, "rowid": i}
            for i in range(20)
        ]
        pc.users.get_messages_after_boundary.return_value = big_tail
        pc.runner.container.settings.max_context_tokens = 200
        pc.runner.container.settings.summary_target_tokens = 20

        chunks = ["hello"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        last = json.loads(output[-1].decode())

        generator.chat.assert_not_awaited()
        pc.users.update_conversation_context_summary.assert_not_called()
        assert last["needs_compaction"] is True
        assert "freed_tokens" not in last
        assert last["used_tokens"] > 0

    def test_freed_tokens_from_prior_compaction_surfaces_in_final_frame(self):
        # If this turn started over budget, RequestHandler._stream_with_
        # budget_notice already folded the history and set req.freed_tokens
        # BEFORE generation began. _usage_fields must pass that through
        # verbatim, not recompute or ignore it.
        import json
        pc, req = self._make_persist_chat()
        pc.users.assert_conversation_owner = MagicMock()
        pc.users.get_conversation_context_state.return_value = {}
        pc.users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        pc.runner.container.settings.max_context_tokens = 32000
        pc.runner.container.settings.summary_target_tokens = 6000
        req.freed_tokens = 750

        chunks = ["hello"]
        output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))
        last = json.loads(output[-1].decode())

        assert last["freed_tokens"] == 750
        assert last["needs_compaction"] is False

    def test_final_persist_is_offloaded_to_a_thread(self):
        # Same regression as PersistChat.run's non-streaming path: the final
        # persist inside the stream generator used to call _persist directly
        # on the event loop.
        pc, req = self._make_persist_chat()
        chunks = ["hello"]

        with patch("hestia.handler.asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
            output = asyncio.run(self._collect(pc._wrap_stream(self._aiter(chunks), req, {})))

        mock_to_thread.assert_awaited_once()
        assert mock_to_thread.await_args.args[0] == pc._persist
        assert len(output) > 0  # stream still completes normally


# ---------------------------------------------------------------------------
# PersistChat._persist
# ---------------------------------------------------------------------------

class TestPersistChatPersist:

    def _make(self):
        from hestia.handler import PersistChat
        runner = MagicMock()
        runner.last_slot = {}
        req = MagicMock()
        req.user.id = uuid.uuid4()
        req.conversation_id = None
        req.last_user_message = "test message"
        req.last_user_display_content = None
        req.last_user_attachments = None
        req.conversation_title = "Test"
        req.model_kwargs = {}

        users_svc = MagicMock()
        new_cid = uuid.uuid4()
        users_svc.create_user_conversation.return_value = new_cid
        users_svc.append_conversation_message.return_value = uuid.uuid4()
        runner.container.services.get.return_value = users_svc

        pc = PersistChat(runner=runner, req=req)
        pc.users = users_svc
        return pc, req, users_svc, new_cid

    def test_creates_new_conversation_when_no_id(self):
        pc, req, users_svc, new_cid = self._make()
        c_id, _, _ = pc._persist(req, "assistant reply", {})
        users_svc.create_user_conversation.assert_called_once()
        assert c_id == new_cid

    def test_appends_user_and_assistant_messages(self):
        pc, req, users_svc, _ = self._make()
        pc._persist(req, "assistant reply", {})
        assert users_svc.append_conversation_message.call_count == 2

    def test_uses_existing_conversation_id(self):
        pc, req, users_svc, _ = self._make()
        existing_cid = uuid.uuid4()
        req.conversation_id = str(existing_cid)
        c_id, _, _ = pc._persist(req, "reply", {})
        users_svc.create_user_conversation.assert_not_called()
        assert c_id == existing_cid

    def test_rag_turn_persists_raw_message_not_augmented_prompt(self):
        # A RAG turn's Augment node produces a slot with retrieved chunks
        # baked into slot["prompt"] and citations in slot["_cite_list"], but
        # none of that should ever end up in the persisted user message --
        # only the original, unaugmented user text (history is resent
        # verbatim every turn, so leaking retrieved chunks into it would
        # blow up the context budget on every subsequent turn).
        pc, req, users_svc, _ = self._make()
        rag_slot = {
            "prompt": "<retrieved-data>\nchunk text\n</retrieved-data>\n\ntest message",
            "_cite_list": [{"key": "1", "source": "docA"}],
        }
        pc._persist(req, "assistant reply", rag_slot, citations=rag_slot["_cite_list"])
        user_call = users_svc.append_conversation_message.call_args_list[0]
        assert user_call.kwargs["content"] == req.last_user_message
        assert "retrieved-data" not in user_call.kwargs["content"]


# ---------------------------------------------------------------------------
# PersistChat.run
# ---------------------------------------------------------------------------

class TestPersistChatRun:

    def _make_persist_chat(self):
        runner = MagicMock()
        req = MagicMock()
        req.user.id = uuid.uuid4()
        req.conversation_id = None
        req.last_user_message = "hi"
        req.last_user_display_content = None
        req.last_user_attachments = None
        req.conversation_title = None
        req.model_kwargs = {}

        users_svc = MagicMock()
        users_svc.create_user_conversation.return_value = uuid.uuid4()
        users_svc.append_conversation_message.return_value = uuid.uuid4()
        runner.container.services.get.return_value = users_svc

        pc = PersistChat(runner=runner, req=req)
        pc.users = users_svc
        return pc, runner, req, users_svc

    def test_non_streaming_calls_runner_then_persists(self):
        pc, runner, req, users_svc = self._make_persist_chat()
        runner.run = AsyncMock(return_value=("assistant reply", {}))

        result, slot = asyncio.run(pc.run("plan", stream=False))

        assert result == "assistant reply"
        runner.run.assert_awaited_once_with("plan", stream=False)
        assert users_svc.append_conversation_message.call_count == 2

    def test_streaming_wraps_generator_without_persisting_yet(self):
        pc, runner, req, users_svc = self._make_persist_chat()

        async def _agen():
            yield "chunk"

        runner.run = AsyncMock(return_value=(_agen(), {}))

        result, slot = asyncio.run(pc.run("plan", stream=True))

        # _wrap_stream returns an async generator — persistence happens lazily
        # inside it once consumed (already covered by TestWrapStream), not here.
        assert hasattr(result, "__anext__")
        users_svc.append_conversation_message.assert_not_called()

    def test_persist_is_offloaded_to_a_thread_not_run_on_the_event_loop(self):
        # Regression test: _persist runs synchronous sqlite3 I/O and used to
        # be called directly on the event loop from this async method,
        # blocking every other in-flight request for its duration.
        pc, runner, req, users_svc = self._make_persist_chat()
        runner.run = AsyncMock(return_value=("assistant reply", {}))

        with patch("hestia.handler.asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
            result, slot = asyncio.run(pc.run("plan", stream=False))

        mock_to_thread.assert_awaited_once()
        assert mock_to_thread.await_args.args[0] == pc._persist
        assert result == "assistant reply"  # return value still surfaces through the await


# ---------------------------------------------------------------------------
# RequestHandler.resolve — policy deny path
# ---------------------------------------------------------------------------

class TestRequestHandlerResolve:

    def test_raises_forbidden_when_policy_denies(self):
        policy = MagicMock()
        policy.check.return_value = PolicyResult(decision=PolicyDecision.DENY, msg="No access.")

        handler = RequestHandler.__new__(RequestHandler)
        handler.policy = policy
        handler.container = MagicMock()

        req = MagicMock()
        req.exec_type = "rag_chat"

        with pytest.raises(ForbiddenError):
            asyncio.run(handler.resolve(req))

    # -----------------------------------------------------------------
    # resolve — happy path (build graph -> run -> return response),
    # save_chat branching, and the non-streaming context-budget check.
    # -----------------------------------------------------------------

    def _handler(self, users=None, generator=None):
        if users is not None:
            # MagicMock special-cases any "assert_*" attribute (typo protection
            # for assert_called_with etc.), so a bare MagicMock() raises
            # AttributeError on this real method name unless stubbed explicitly.
            users.assert_conversation_owner = MagicMock()
        settings = MagicMock()
        settings.max_context_tokens = 2000
        settings.summary_target_tokens = 100
        settings.summary_model = None
        settings.default_gen_model = "test-model"

        container = MagicMock()
        container.settings = settings
        container.services.get.side_effect = lambda name: {"users": users, "generate": generator}.get(name)
        container.require_service.side_effect = lambda name: {"users": users, "generate": generator}.get(name)

        policy = MagicMock()
        policy.check.return_value = PolicyResult(decision=PolicyDecision.ALLOW)

        h = RequestHandler.__new__(RequestHandler)
        h.policy = policy
        h.container = container
        h.builder = MagicMock()
        h.builder.build.return_value = "graph"
        h.runner = MagicMock()
        h.runner.run = AsyncMock(return_value=("final answer", {}))
        return h

    def _req(self, exec_type="generate", save_chat=False, conversation_id=None):
        req = MagicMock()
        req.exec_type = exec_type
        req.model = "m"
        req.collection = None
        req.prompt = "hi"
        req.last_user_message = None
        req.user.id = uuid.uuid4()
        req.save_chat = save_chat
        req.conversation_id = conversation_id
        return req

    def test_returns_response_on_success(self):
        h = self._handler()
        req = self._req(exec_type="generate")

        result = asyncio.run(h.resolve(req, stream=False))

        assert result == "final answer"
        h.builder.build.assert_called_once_with(req, RequestHandler.TEMPLATE_MAP["generate"])
        h.runner.run.assert_awaited_once_with("graph", stream=False)

    def test_sets_query_filters_when_policy_decision_is_filter(self):
        h = self._handler()
        h.policy.check.return_value = PolicyResult(
            decision=PolicyDecision.FILTER, filters={"max_classification": 2},
        )
        req = self._req(exec_type="generate")
        req.query_kwargs = None

        asyncio.run(h.resolve(req, stream=False))

        assert req.query_kwargs == {"filters": {"max_classification": 2}}

    def test_stream_true_delegates_to_stream_with_budget_notice(self):
        h = self._handler()
        sentinel = object()
        h._stream_with_budget_notice = MagicMock(return_value=sentinel)
        req = self._req(exec_type="generate")

        result = asyncio.run(h.resolve(req, stream=True))

        assert result is sentinel
        h._stream_with_budget_notice.assert_called_once_with(req, RequestHandler.TEMPLATE_MAP["generate"])
        h.runner.run.assert_not_awaited()

    def test_uses_runner_directly_when_save_chat_false(self):
        h = self._handler()
        req = self._req(save_chat=False)

        asyncio.run(h.resolve(req, stream=False))

        h.runner.run.assert_awaited_once_with("graph", stream=False)

    def test_wraps_runner_in_persist_chat_when_save_chat_true(self):
        h = self._handler()
        req = self._req(save_chat=True)

        with patch("hestia.handler.PersistChat") as MockPersistChat:
            instance = MockPersistChat.return_value
            instance.run = AsyncMock(return_value=("wrapped answer", {}))
            result = asyncio.run(h.resolve(req, stream=False))

        MockPersistChat.assert_called_once_with(h.runner, req)
        assert result == "wrapped answer"

    def test_skips_context_budget_for_generate_exec_type(self):
        users = MagicMock()
        h = self._handler(users=users, generator=_generator_double())
        req = self._req(exec_type="generate", conversation_id=str(uuid.uuid4()))

        asyncio.run(h.resolve(req, stream=False))

        users.get_conversation_context_state.assert_not_called()

    def test_applies_context_budget_for_chat_with_conversation_id(self):
        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        big_tail = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 100,
             "created_at": i, "rowid": i}
            for i in range(20)
        ]
        users.get_messages_after_boundary.return_value = big_tail
        generator = _generator_double(chat_return="a summary")

        h = self._handler(users=users, generator=generator)
        req = self._req(exec_type="chat", conversation_id=str(uuid.uuid4()))

        result = asyncio.run(h.resolve(req, stream=False))

        assert result == "final answer"
        generator.chat.assert_awaited_once()
        users.update_conversation_context_summary.assert_called_once()
        assert req.history is not None
        assert req.history[0]["role"] == "system"

    def test_no_compaction_needed_under_budget(self):
        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        generator = _generator_double()

        h = self._handler(users=users, generator=generator)
        req = self._req(exec_type="chat", conversation_id=str(uuid.uuid4()))

        result = asyncio.run(h.resolve(req, stream=False))

        assert result == "final answer"
        generator.chat.assert_not_awaited()
        users.update_conversation_context_summary.assert_not_called()

    def test_context_budget_failure_fails_open(self):
        users = MagicMock()
        users.get_conversation_context_state.side_effect = RuntimeError("boom")
        h = self._handler(users=users, generator=_generator_double())
        req = self._req(exec_type="chat", conversation_id=str(uuid.uuid4()))

        result = asyncio.run(h.resolve(req, stream=False))

        assert result == "final answer"


# ---------------------------------------------------------------------------
# RequestHandler._stream_with_budget_notice — auto-compaction runs at the
# START of a turn whose incoming history is already over budget, before
# generation begins for that turn. It never runs as a side effect of the
# turn that just finished (that would delay/interrupt content that's
# already streaming); it only ever fires the next time a user submits a
# query while the conversation is over budget.
# ---------------------------------------------------------------------------

class TestStreamWithBudgetNotice:

    def _handler(self, users, generator):
        from hestia.handler import RequestHandler

        users.assert_conversation_owner = MagicMock()
        settings = MagicMock()
        settings.max_context_tokens = 2000
        settings.summary_target_tokens = 100
        settings.summary_model = None
        settings.default_gen_model = "test-model"

        container = MagicMock()
        container.settings = settings
        container.services.get.side_effect = lambda name: {"users": users, "generate": generator}.get(name)
        container.require_service.side_effect = lambda name: {"users": users, "generate": generator}.get(name)

        h = RequestHandler.__new__(RequestHandler)
        h.container = container
        h.builder = MagicMock()
        h.builder.build.return_value = "graph"
        h.runner = MagicMock()
        h.runner.container = container

        async def fake_stream():
            yield b'{"content": "hi"}\n'

        h.runner.run = AsyncMock(return_value=(fake_stream(), {}))
        return h

    def _req(self, save_chat=False):
        req = MagicMock()
        req.conversation_id = str(uuid.uuid4())
        req.exec_type = "chat"
        req.save_chat = save_chat
        req.user.id = uuid.uuid4()
        return req

    async def _collect(self, agen):
        return [chunk async for chunk in agen]

    def test_over_budget_compacts_before_generation_starts(self):
        # This is the only place auto-compaction can fire: the incoming
        # turn's history is already over budget, so it must emit a
        # "compacting" status frame, then fold BEFORE generation starts, and
        # req.freed_tokens must carry the result so the final frame can
        # announce it.
        import json
        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        big_tail = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 100,
             "created_at": i, "rowid": i}
            for i in range(20)
        ]
        users.get_messages_after_boundary.return_value = big_tail
        generator = _generator_double(chat_return="a summary")

        h = self._handler(users, generator)
        req = self._req()

        chunks = asyncio.run(self._collect(h._stream_with_budget_notice(req, "template")))

        assert json.loads(chunks[0].decode()) == {"status": "compacting"}
        assert chunks[1:] == [b'{"content": "hi"}\n']
        generator.chat.assert_awaited_once()
        users.update_conversation_context_summary.assert_called_once()
        assert req.history is not None
        assert len(req.history) < len(big_tail)
        assert req.freed_tokens is not None and req.freed_tokens > 0

    def test_no_status_frame_when_under_budget(self):
        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        generator = _generator_double()

        h = self._handler(users, generator)
        req = self._req()

        chunks = asyncio.run(self._collect(h._stream_with_budget_notice(req, "template")))

        generator.chat.assert_not_awaited()
        assert chunks == [b'{"content": "hi"}\n']

    def test_non_chat_exec_type_skips_budget_check_entirely(self):
        users = MagicMock()
        generator = _generator_double()
        h = self._handler(users, generator)
        req = self._req()
        req.exec_type = "generate"  # not in CONTEXT_BUDGET_EXEC_TYPES

        asyncio.run(self._collect(h._stream_with_budget_notice(req, "template")))

        users.get_conversation_context_state.assert_not_called()

    def test_provider_failure_during_retrieval_degrades_gracefully(self):
        # A provider failure (e.g. Qdrant search) can happen inside
        # runner.run() itself -- before any chunk exists -- not just while
        # iterating the resulting generator. Must still degrade to an
        # in-band ⚠️ frame instead of crashing the stream.
        from hestia.domain.exceptions import ProviderError

        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        generator = MagicMock()
        h = self._handler(users, generator)
        h.runner.run = AsyncMock(side_effect=ProviderError("vector search failed"))
        req = self._req()

        chunks = asyncio.run(self._collect(h._stream_with_budget_notice(req, "template")))

        assert len(chunks) == 1
        assert b"vector search failed" in chunks[0]

    def test_unexpected_non_hestia_exception_during_retrieval_degrades_gracefully(self):
        # Regression test: only HestiaError used to be caught here, so a bug
        # in a node handler (or any un-wrapped third-party exception) would
        # propagate out of an already-started StreamingResponse body instead
        # of surfacing as an in-band error frame.
        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        generator = MagicMock()
        h = self._handler(users, generator)
        h.runner.run = AsyncMock(side_effect=RuntimeError("bug in a node handler"))
        req = self._req()

        chunks = asyncio.run(self._collect(h._stream_with_budget_notice(req, "template")))

        assert len(chunks) == 1
        assert b"Something went wrong" in chunks[0]

    def test_unexpected_exception_mid_stream_degrades_gracefully(self):
        users = MagicMock()
        users.get_conversation_context_state.return_value = {}
        users.get_messages_after_boundary.return_value = [
            {"role": "user", "content": "hi", "created_at": 1, "rowid": 1}
        ]
        generator = MagicMock()
        h = self._handler(users, generator)

        async def broken_stream():
            yield b'{"content": "partial"}\n'
            raise RuntimeError("provider connection dropped mid-chunk")

        h.runner.run = AsyncMock(return_value=(broken_stream(), {}))
        req = self._req()

        chunks = asyncio.run(self._collect(h._stream_with_budget_notice(req, "template")))

        assert chunks[0] == b'{"content": "partial"}\n'
        assert b"Something went wrong" in chunks[1]
