from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from hestia.domain.rag.graph import ExecutionGraph, ExecutionRequest, Node
from hestia.domain.rag.templater import TemplatePlanBuilder, TemplateRepository, chain
from hestia.domain.exceptions import ConfigurationError
from tests.unit.conftest import _make_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(directory: str, rel_path: str, data: dict) -> str:
    full = os.path.join(directory, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        yaml.dump(data, f)
    return full


def _make_request(**overrides):
    defaults = dict(
        user=_make_user(),
        exec_type="chat",
        prompt="Hello",
        model="test-model",
        collection=None,
    )
    defaults.update(overrides)
    return ExecutionRequest(**defaults)


# ---------------------------------------------------------------------------
# TemplateRepository
# ---------------------------------------------------------------------------

class TestTemplateRepository:

    def test_raises_on_missing_directory(self, tmp_path):
        with pytest.raises(ConfigurationError):
            TemplateRepository(templates_dir=str(tmp_path / "nonexistent"))

    def test_loads_valid_yaml(self, tmp_path):
        _write_yaml(str(tmp_path), "test.yaml", {"key": "value"})
        repo = TemplateRepository(templates_dir=str(tmp_path))
        data = repo.load_yaml("test.yaml")
        assert data["key"] == "value"

    def test_raises_on_missing_file(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            repo.load_yaml("missing.yaml")


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._interpolate_str
# ---------------------------------------------------------------------------

class TestInterpolateStr:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_replaces_placeholder(self, builder):
        result = builder._interpolate_str("Hello ${name}", {"name": "World"})
        assert result == "Hello World"

    def test_leaves_non_matching_intact(self, builder):
        result = builder._interpolate_str("Static string", {})
        assert result == "Static string"

    def test_missing_key_replaced_with_empty(self, builder):
        result = builder._interpolate_str("${missing}", {})
        assert result == ""


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._resolve_key
# ---------------------------------------------------------------------------

class TestResolveKey:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_resolves_simple_key(self, builder):
        assert builder._resolve_key({"a": 1}, "a") == 1

    def test_resolves_dotted_path(self, builder):
        assert builder._resolve_key({"a": {"b": 42}}, "a.b") == 42

    def test_returns_none_for_missing(self, builder):
        assert builder._resolve_key({}, "missing") is None

    def test_returns_none_for_wrong_path(self, builder):
        assert builder._resolve_key({"a": 1}, "a.b") is None


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._resolve_rel
# ---------------------------------------------------------------------------

class TestResolveRel:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_resolves_same_directory(self, builder):
        result = builder._resolve_rel("base/chat.yaml", "generate.yaml")
        assert result == os.path.normpath("base/generate.yaml")

    def test_resolves_parent_directory(self, builder):
        result = builder._resolve_rel("base/chat.yaml", "../other.yaml")
        assert result == os.path.normpath("other.yaml")


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._merge_fragment
# ---------------------------------------------------------------------------

class TestMergeFragment:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_overrides_top_level_key(self, builder):
        frag = {"id": "old", "type": "Generate"}
        result = builder._merge_fragment(frag, {"id": "new"})
        assert result["id"] == "new"

    def test_merges_inputs_dict(self, builder):
        frag = {"inputs": {"a": 1, "b": 2}}
        result = builder._merge_fragment(frag, {"inputs": {"b": 99, "c": 3}})
        assert result["inputs"] == {"a": 1, "b": 99, "c": 3}

    def test_merges_outputs_dict(self, builder):
        frag = {"outputs": {"x": "?slot"}}
        result = builder._merge_fragment(frag, {"outputs": {"y": "?other"}})
        assert "x" in result["outputs"]
        assert "y" in result["outputs"]


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._to_graph
# ---------------------------------------------------------------------------

class TestToGraph:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_infers_edges_for_linear_nodes(self, builder):
        hydrated = {
            "nodes": [
                {"id": "A", "type": "Generate", "inputs": {}, "outputs": {}},
                {"id": "B", "type": "Chat", "inputs": {}, "outputs": {}},
            ],
            "entrypoint": "A",
            "exitpoints": ["B"],
            "edges": [],
            "context_refs": {},
        }
        graph = builder._to_graph(hydrated)
        assert ("A", "B") in graph.edges

    def test_explicit_edges_preserved(self, builder):
        hydrated = {
            "nodes": [
                {"id": "X", "type": "Generate", "inputs": {}, "outputs": {}},
                {"id": "Y", "type": "Chat", "inputs": {}, "outputs": {}},
            ],
            "entrypoint": "X",
            "exitpoints": ["Y"],
            "edges": [["X", "Y"]],
            "context_refs": {},
        }
        graph = builder._to_graph(hydrated)
        assert ("X", "Y") in graph.edges

    def test_sets_entrypoint_from_first_node(self, builder):
        hydrated = {
            "nodes": [{"id": "first", "type": "Generate", "inputs": {}, "outputs": {}}],
            "entrypoint": None,
            "exitpoints": [],
            "edges": [],
            "context_refs": {},
        }
        graph = builder._to_graph(hydrated)
        assert graph.entrypoint == "first"


# ---------------------------------------------------------------------------
# chain()
# ---------------------------------------------------------------------------

class TestChain:

    def _graph(self, node_ids):
        nodes = [Node(id=nid, type="Generate", inputs={}, outputs={}) for nid in node_ids]
        edges = [(node_ids[i], node_ids[i + 1]) for i in range(len(node_ids) - 1)]
        return ExecutionGraph(
            nodes=nodes,
            edges=edges,
            entrypoint=node_ids[0],
            exitpoints=[node_ids[-1]],
        )

    def test_entrypoint_from_first_graph(self):
        g1 = self._graph(["A", "B"])
        g2 = self._graph(["C", "D"])
        combined = chain(g1, g2)
        assert combined.entrypoint == "A"

    def test_exitpoint_from_second_graph(self):
        g1 = self._graph(["A"])
        g2 = self._graph(["B"])
        combined = chain(g1, g2)
        assert combined.exitpoints == ["B"]

    def test_connecting_edge_created(self):
        g1 = self._graph(["A"])
        g2 = self._graph(["B"])
        combined = chain(g1, g2)
        assert ("A", "B") in combined.edges

    def test_all_nodes_present(self):
        g1 = self._graph(["A", "B"])
        g2 = self._graph(["C", "D"])
        combined = chain(g1, g2)
        node_ids = [n.id for n in combined.nodes]
        assert set(node_ids) == {"A", "B", "C", "D"}
