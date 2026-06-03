from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from hestia.handler import (
    Runner,
    _build_prompt,
    _extract_used_citekeys,
    _format_citations,
    _normalize_citekey,
)
from hestia.domain.rag.graph import ExecutionGraph, ExecutionRequest, Node
from tests.unit.conftest import _make_user


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

    def test_deduplicates_by_source(self):
        hits = [
            self._make_point("docA", "chunk1"),
            self._make_point("docA", "chunk2"),
            self._make_point("docB", "chunk3"),
        ]
        _, cite_list = _format_citations(hits)
        assert len(cite_list) == 2

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

    def test_no_hits_returns_original_prompt(self):
        prompt, cites = _build_prompt("original", [])
        assert prompt == "original"
        assert cites == []

    def test_with_hits_augments_prompt(self):
        point = MagicMock()
        point.payload = {
            "source": "doc", "content": "chunk",
            "doc_info": {}, "info": {},
        }
        prompt, cites = _build_prompt("user question", [point])
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
# PersistChat._wrap_stream — <think> tag stripping
# ---------------------------------------------------------------------------

class TestWrapStream:

    def _make_persist_chat(self, cite_list=None):
        from hestia.handler import PersistChat
        runner = MagicMock()
        runner.last_slot = {"_cite_list": cite_list or []}
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
        return pc, req

    def test_content_outside_think_tags_yields_content(self):
        from hestia.handler import PersistChat
        pc, req = self._make_persist_chat()
        chunks = ["Hello ", "world"]
        output = list(pc._wrap_stream(iter(chunks), req))
        # Check that content events were yielded
        import json
        contents = []
        for chunk in output[:-1]:  # last is metadata
            data = json.loads(chunk.decode())
            if "content" in data:
                contents.append(data["content"])
        assert "Hello " in contents or any("Hello" in c for c in contents)

    def test_think_tags_routed_to_thinking_stream(self):
        from hestia.handler import PersistChat
        import json
        pc, req = self._make_persist_chat()
        chunks = ["<think>internal reasoning</think>answer"]
        output = list(pc._wrap_stream(iter(chunks), req))
        thinking_chunks = []
        for chunk in output[:-1]:
            data = json.loads(chunk.decode())
            if "thinking" in data:
                thinking_chunks.append(data["thinking"])
        assert any("internal reasoning" in t for t in thinking_chunks)

    def test_last_chunk_contains_conversation_id(self):
        from hestia.handler import PersistChat
        import json
        pc, req = self._make_persist_chat()
        chunks = ["hello"]
        output = list(pc._wrap_stream(iter(chunks), req))
        last = json.loads(output[-1].decode())
        assert "conversation_id" in last


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
        c_id, _, _ = pc._persist(req, "assistant reply")
        users_svc.create_user_conversation.assert_called_once()
        assert c_id == new_cid

    def test_appends_user_and_assistant_messages(self):
        pc, req, users_svc, _ = self._make()
        pc._persist(req, "assistant reply")
        assert users_svc.append_conversation_message.call_count == 2

    def test_uses_existing_conversation_id(self):
        pc, req, users_svc, _ = self._make()
        existing_cid = uuid.uuid4()
        req.conversation_id = str(existing_cid)
        c_id, _, _ = pc._persist(req, "reply")
        users_svc.create_user_conversation.assert_not_called()
        assert c_id == existing_cid


# ---------------------------------------------------------------------------
# RequestHandler.resolve — policy deny path
# ---------------------------------------------------------------------------

class TestRequestHandlerResolve:

    def test_raises_forbidden_when_policy_denies(self):
        from hestia.handler import RequestHandler
        from hestia.domain.policies.guard import PolicyDecision, PolicyResult
        from hestia.domain.exceptions import ForbiddenError

        policy = MagicMock()
        policy.check.return_value = PolicyResult(decision=PolicyDecision.DENY, msg="No access.")

        handler = RequestHandler.__new__(RequestHandler)
        handler.policy = policy
        handler.container = MagicMock()

        req = MagicMock()
        req.exec_type = "rag_chat"

        with pytest.raises(ForbiddenError):
            handler.resolve(req)
