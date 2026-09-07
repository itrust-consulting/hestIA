from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from hestia.domain.rag.graph import ExecutionGraph, ExecutionRequest, Node
from hestia.domain.rag.templater import TemplatePlanBuilder, TemplateRepository, _format_attachments, chain
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


# ---------------------------------------------------------------------------
# _format_attachments
# ---------------------------------------------------------------------------

class TestFormatAttachments:

    def test_empty_or_none_returns_empty_string(self):
        assert _format_attachments([], True) == ""
        assert _format_attachments(None, True) == ""

    def test_with_question_uses_with_question_prefix(self):
        result = _format_attachments([{"name": "a.txt", "markdown": "content"}], True)
        assert result.startswith("The user attached the following document(s) as extra context")
        assert '<document name="a.txt">\ncontent\n</document>' in result

    def test_without_question_uses_no_question_prefix(self):
        result = _format_attachments([{"name": "a.txt", "markdown": "content"}], False)
        assert result.startswith("The user attached the following document(s) without asking")

    def test_multiple_attachments_joined_with_blank_line(self):
        attachments = [
            {"name": "a.txt", "markdown": "A"},
            {"name": "b.txt", "markdown": "B"},
        ]
        result = _format_attachments(attachments, True)
        assert '<document name="a.txt">\nA\n</document>' in result
        assert '<document name="b.txt">\nB\n</document>' in result
        # blocks are separated by a blank line
        assert "</document>\n\n<document" in result

    def test_missing_name_and_markdown_default_to_empty(self):
        result = _format_attachments([{}], True)
        assert '<document name="">\n\n</document>' in result


# ---------------------------------------------------------------------------
# TemplateRepository -- caching / invalidation
# ---------------------------------------------------------------------------

class TestLoadYamlCaching:

    def test_second_load_uses_cache_not_disk(self, tmp_path):
        path = _write_yaml(str(tmp_path), "cached.yaml", {"key": "original"})
        repo = TemplateRepository(templates_dir=str(tmp_path))
        first = repo.load_yaml("cached.yaml")
        assert first["key"] == "original"

        # Overwrite the file directly -- a genuine cache hit must not
        # notice this until invalidate() is called.
        with open(path, "w") as f:
            yaml.dump({"key": "changed"}, f)

        second = repo.load_yaml("cached.yaml")
        assert second["key"] == "original"
        assert second is first

    def test_invalidate_forces_reread(self, tmp_path):
        path = _write_yaml(str(tmp_path), "cached.yaml", {"key": "original"})
        repo = TemplateRepository(templates_dir=str(tmp_path))
        repo.load_yaml("cached.yaml")

        with open(path, "w") as f:
            yaml.dump({"key": "changed"}, f)
        repo.invalidate()

        result = repo.load_yaml("cached.yaml")
        assert result["key"] == "changed"

    def test_invalidate_on_empty_cache_is_a_noop(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        repo.invalidate()  # must not raise


# ---------------------------------------------------------------------------
# TemplatePlanBuilder.preload
# ---------------------------------------------------------------------------

class TestPreload:

    def test_preload_caches_root_and_included_fragments(self, tmp_path):
        _write_yaml(str(tmp_path), "base/frag.yaml", {
            "id": "${id}", "type": "Generate", "inputs": {}, "outputs": {},
        })
        _write_yaml(str(tmp_path), "workflows/wf.yaml", {
            "entrypoint": "N1",
            "include": ["../base/frag.yaml"],
            "nodes": [{"use": "frag.yaml", "with": {"id": "N1"}}],
        })
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)

        builder.preload(["workflows/wf.yaml"])

        cache_keys_norm = {os.path.normpath(p) for p in repo._cache}
        assert os.path.normpath(os.path.join(str(tmp_path), "workflows", "wf.yaml")) in cache_keys_norm
        assert os.path.normpath(os.path.join(str(tmp_path), "base", "frag.yaml")) in cache_keys_norm

    def test_preload_handles_multiple_paths(self, tmp_path):
        _write_yaml(str(tmp_path), "a.yaml", {"nodes": []})
        _write_yaml(str(tmp_path), "b.yaml", {"nodes": []})
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)

        builder.preload(["a.yaml", "b.yaml"])

        cache_keys_norm = {os.path.normpath(p) for p in repo._cache}
        assert os.path.normpath(os.path.join(str(tmp_path), "a.yaml")) in cache_keys_norm
        assert os.path.normpath(os.path.join(str(tmp_path), "b.yaml")) in cache_keys_norm

    def test_preload_populates_cache_used_by_later_build(self, tmp_path):
        # After preload(), a subsequent build() for the same template should
        # not need to touch disk again -- verified indirectly by deleting
        # the on-disk file and confirming build() still succeeds.
        path = _write_yaml(str(tmp_path), "workflows/wf.yaml", {
            "entrypoint": "N1",
            "nodes": [{"id": "N1", "type": "Generate", "inputs": {}, "outputs": {}}],
        })
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)
        builder.preload(["workflows/wf.yaml"])

        os.remove(path)

        graph = builder.build(_make_request(), "workflows/wf.yaml")
        assert graph.entrypoint == "N1"


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._build_ctx
# ---------------------------------------------------------------------------

class TestBuildCtx:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_builds_all_context_fields_from_request(self, builder):
        request = _make_request(
            prompt="hi",
            history=[{"role": "user", "content": "hi"}],
            model="gpt-4",
            model_kwargs={"temperature": 0.2},
            collection="my-col",
            query_kwargs={"top_k": 5},
            embedding_model="embed-1",
            embedding_model_kwargs={"dim": 768},
        )
        ctx = builder._build_ctx(request)
        assert ctx["prompt"] == "hi"
        assert ctx["history"] == [{"role": "user", "content": "hi"}]
        assert ctx["model"] == "gpt-4"
        assert ctx["model_kwargs"] == {"temperature": 0.2}
        assert ctx["collection"] == "my-col"
        assert ctx["query_kwargs"] == {"top_k": 5}
        assert ctx["embedding_model"] == "embed-1"
        assert ctx["embedding_model_kwargs"] == {"dim": 768}

    def test_attached_documents_populated_when_attachments_present(self, builder):
        request = _make_request(
            last_user_message="What is this?",
            last_user_display_content="What is this?",
            last_user_attachments=[{"name": "doc.txt", "markdown": "content"}],
        )
        ctx = builder._build_ctx(request)
        assert "doc.txt" in ctx["attached_documents"]
        assert ctx["attached_documents"].startswith(
            "The user attached the following document(s) as extra context"
        )

    def test_attached_documents_empty_without_attachments(self, builder):
        request = _make_request(last_user_message="hi")
        ctx = builder._build_ctx(request)
        assert ctx["attached_documents"] == ""

    def test_attached_documents_uses_no_question_prefix_when_no_query_text(self, builder):
        request = _make_request(
            last_user_message=[{"type": "image", "url": "x"}],
            last_user_display_content=None,
            last_user_attachments=[{"name": "doc.txt", "markdown": "content"}],
        )
        ctx = builder._build_ctx(request)
        assert ctx["attached_documents"].startswith(
            "The user attached the following document(s) without asking"
        )


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._interpolate_strings
# ---------------------------------------------------------------------------

class TestInterpolateStrings:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_slot_reference_returned_unchanged(self, builder):
        assert builder._interpolate_strings("?some_slot", {"some_slot": "ignored"}) == "?some_slot"

    def test_exact_ctx_ref_preserves_non_string_type(self, builder):
        result = builder._interpolate_strings("${model_kwargs}", {"model_kwargs": {"temperature": 0.1}})
        assert result == {"temperature": 0.1}

    def test_exact_ctx_ref_string_value_returned_plain(self, builder):
        result = builder._interpolate_strings("${model}", {"model": "gpt-4"})
        assert result == "gpt-4"

    def test_partial_ctx_ref_stringifies_non_string_value(self, builder):
        result = builder._interpolate_strings("model: ${model_kwargs}", {"model_kwargs": {"a": 1}})
        assert result == "model: {'a': 1}"

    def test_recurses_into_dict(self, builder):
        data = {"a": "${x}", "b": ["${y}", "?slot"]}
        result = builder._interpolate_strings(data, {"x": "1", "y": "2"})
        assert result == {"a": "1", "b": ["2", "?slot"]}

    def test_recurses_into_list(self, builder):
        result = builder._interpolate_strings(["${x}", "static"], {"x": "val"})
        assert result == ["val", "static"]

    def test_non_string_non_container_passthrough(self, builder):
        assert builder._interpolate_strings(42, {}) == 42
        assert builder._interpolate_strings(None, {}) is None


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._inject_raw_ctx
# ---------------------------------------------------------------------------

class TestInjectRawCtx:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_slot_reference_returned_unchanged(self, builder):
        assert builder._inject_raw_ctx("?some_slot", {"some_slot": "ignored"}) == "?some_slot"

    def test_exact_ctx_ref_resolves_raw_value(self, builder):
        result = builder._inject_raw_ctx("${history}", {"history": [{"role": "user"}]})
        assert result == [{"role": "user"}]

    def test_non_exact_string_passthrough_unmodified(self, builder):
        # Unlike _interpolate_str, a partial match is NOT substituted here --
        # the raw literal is returned as-is.
        assert builder._inject_raw_ctx("plain text ${x}", {"x": "1"}) == "plain text ${x}"

    def test_recurses_into_dict_and_list(self, builder):
        data = {"a": "${x}", "b": ["${y}"]}
        result = builder._inject_raw_ctx(data, {"x": 1, "y": [2, 3]})
        assert result == {"a": 1, "b": [[2, 3]]}

    def test_non_string_passthrough(self, builder):
        assert builder._inject_raw_ctx(42, {}) == 42


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._load_fragments
# ---------------------------------------------------------------------------

class TestLoadFragments:

    def test_loads_each_include_keyed_by_basename(self, tmp_path):
        _write_yaml(str(tmp_path), "base/chat.yaml", {"type": "Chat"})
        _write_yaml(str(tmp_path), "base/generate.yaml", {"type": "Generate"})
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)

        root = {"include": ["../base/chat.yaml", "../base/generate.yaml"]}
        fragments = builder._load_fragments(root, "workflows/wf.yaml")

        assert fragments["chat.yaml"]["type"] == "Chat"
        assert fragments["generate.yaml"]["type"] == "Generate"

    def test_no_include_key_returns_empty_dict(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)
        assert builder._load_fragments({}, "workflows/wf.yaml") == {}

    def test_empty_include_list_returns_empty_dict(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)
        assert builder._load_fragments({"include": []}, "workflows/wf.yaml") == {}


# ---------------------------------------------------------------------------
# TemplatePlanBuilder._hydrate_node
# ---------------------------------------------------------------------------

class TestHydrateNode:

    @pytest.fixture
    def builder(self, tmp_path):
        repo = TemplateRepository(templates_dir=str(tmp_path))
        return TemplatePlanBuilder(repo=repo)

    def test_plain_node_interpolated(self, builder):
        entry = {"id": "n1", "type": "Chat", "inputs": {"model": "${model}"}, "outputs": {"response": "out"}}
        result = builder._hydrate_node(entry, {}, {"model": "gpt-4"})
        assert result["inputs"]["model"] == "gpt-4"
        assert result["id"] == "n1"

    def test_use_missing_fragment_raises(self, builder):
        entry = {"use": "missing.yaml", "with": {"id": "n1"}}
        with pytest.raises(ConfigurationError, match="Fragment 'missing.yaml' not found"):
            builder._hydrate_node(entry, {}, {})

    def test_use_merges_fragment_with_overrides(self, builder):
        fragments = {
            "frag.yaml": {"id": "${id}", "type": "Generate", "inputs": {"model": "${model}"}, "outputs": {}},
        }
        entry = {"use": "frag.yaml", "with": {"id": "n1", "inputs": {"model": "override-model"}}}
        result = builder._hydrate_node(entry, fragments, {"model": "unused"})
        assert result["id"] == "n1"
        assert result["inputs"]["model"] == "override-model"
        assert result["type"] == "Generate"

    def test_use_preserves_slot_reference_in_merged_inputs(self, builder):
        fragments = {
            "frag.yaml": {
                "id": "${id}", "type": "Retrieve",
                "inputs": {"dense": "${dense}"}, "outputs": {"hits": "${output_hits}"},
            },
        }
        entry = {
            "use": "frag.yaml",
            "with": {"id": "n1", "inputs": {"dense": "?dense_vector"}, "outputs": {"hits": "points"}},
        }
        result = builder._hydrate_node(entry, fragments, {})
        assert result["inputs"]["dense"] == "?dense_vector"
        assert result["outputs"]["hits"] == "points"

    def test_use_unfilled_fragment_placeholder_resolves_via_ctx(self, builder):
        # A base-fragment key the "with" block doesn't override falls back
        # to whatever the fragment's own placeholder resolves to in ctx.
        fragments = {
            "frag.yaml": {
                "id": "${id}", "type": "Chat",
                "inputs": {"history": "${history}"}, "outputs": {},
            },
        }
        entry = {"use": "frag.yaml", "with": {"id": "n1"}}
        result = builder._hydrate_node(entry, fragments, {"history": [{"role": "user"}]})
        assert result["inputs"]["history"] == [{"role": "user"}]


# ---------------------------------------------------------------------------
# TemplatePlanBuilder.build -- end-to-end
# ---------------------------------------------------------------------------

class TestBuild:

    def test_build_hydrates_use_node_with_ctx_and_slots(self, tmp_path):
        _write_yaml(str(tmp_path), "base/chat.yaml", {
            "id": "${id}", "type": "Chat",
            "inputs": {
                "history": "${history}", "last_user_message": "${last_user_message}",
                "model": "${model}", "options": "${model_kwargs}",
            },
            "outputs": {"response": "${response}"},
        })
        _write_yaml(str(tmp_path), "workflows/wf.yaml", {
            "entrypoint": "Retrieve1",
            "exitpoints": ["Chat1"],
            "include": ["../base/chat.yaml"],
            "nodes": [
                {
                    "id": "Retrieve1", "type": "Retrieve",
                    "inputs": {"dense": None, "sparse": None, "collection": "${collection}", "options": {}},
                    "outputs": {"hits": "points"},
                },
                {
                    "use": "chat.yaml",
                    "with": {
                        "id": "Chat1",
                        "inputs": {
                            "last_user_message": "?points", "model": "${model}", "options": "${model_kwargs}",
                        },
                        "outputs": {"response": "final"},
                    },
                },
            ],
        })
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)
        request = _make_request(collection="my-col", model="gpt-4", model_kwargs={"temperature": 0.5})

        graph = builder.build(request, "workflows/wf.yaml")

        assert [n.id for n in graph.nodes] == ["Retrieve1", "Chat1"]
        retrieve_node, chat_node = graph.nodes
        assert retrieve_node.inputs["collection"] == "my-col"
        assert chat_node.type == "Chat"
        assert chat_node.inputs["last_user_message"] == "?points"  # unresolved slot preserved
        assert chat_node.inputs["model"] == "gpt-4"
        assert chat_node.inputs["options"] == {"temperature": 0.5}
        assert chat_node.outputs["response"] == "final"
        assert graph.entrypoint == "Retrieve1"
        assert graph.exitpoints == ["Chat1"]
        assert graph.edges == [("Retrieve1", "Chat1")]

    def test_build_raises_for_use_without_matching_include(self, tmp_path):
        _write_yaml(str(tmp_path), "workflows/wf.yaml", {
            "entrypoint": "N1",
            "nodes": [{"use": "nope.yaml", "with": {"id": "N1"}}],
        })
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)

        with pytest.raises(ConfigurationError, match="Fragment 'nope.yaml' not found"):
            builder.build(_make_request(), "workflows/wf.yaml")

    def test_build_passes_through_context_refs(self, tmp_path):
        _write_yaml(str(tmp_path), "workflows/wf.yaml", {
            "entrypoint": "N1",
            "nodes": [{"id": "N1", "type": "Generate", "inputs": {}, "outputs": {}}],
            "context_refs": {"foo": "bar"},
        })
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)

        graph = builder.build(_make_request(), "workflows/wf.yaml")
        assert graph.context_refs == {"foo": "bar"}

    def test_build_caches_template_across_calls(self, tmp_path):
        # A second build() for the same template must come from cache, not
        # a second disk read -- verified by deleting the file in between.
        path = _write_yaml(str(tmp_path), "workflows/wf.yaml", {
            "entrypoint": "N1",
            "nodes": [{"id": "N1", "type": "Generate", "inputs": {}, "outputs": {}}],
        })
        repo = TemplateRepository(templates_dir=str(tmp_path))
        builder = TemplatePlanBuilder(repo=repo)
        builder.build(_make_request(), "workflows/wf.yaml")

        os.remove(path)

        graph = builder.build(_make_request(), "workflows/wf.yaml")
        assert graph.entrypoint == "N1"
