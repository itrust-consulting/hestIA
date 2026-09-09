from __future__ import annotations

import pytest

from hestia.domain.exceptions import ValidationError
from hestia.domain.rag.graph import has_query_text, validate_workflow_graph


def _generate_node(node_id="gen", inputs=None, outputs=None):
    return {
        "type": "Generate",
        "id": node_id,
        "inputs": inputs if inputs is not None else {"prompt": None, "model": None, "options": None},
        "outputs": outputs if outputs is not None else {"response": "final"},
    }


def _chat_node(node_id="chat", inputs=None):
    return {
        "type": "Chat",
        "id": node_id,
        "inputs": inputs if inputs is not None else {"history": "${history}", "last_user_message": "${last_user_message}"},
        "outputs": {"response": "final"},
    }


def _single_node_graph(**kwargs):
    node = _chat_node(**kwargs)
    return {"nodes": [node], "entrypoint": node["id"]}


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------

class TestNodesPresence:

    def test_missing_nodes_key_raises(self):
        with pytest.raises(ValidationError, match="at least one node"):
            validate_workflow_graph({})

    def test_empty_nodes_list_raises(self):
        with pytest.raises(ValidationError, match="at least one node"):
            validate_workflow_graph({"nodes": []})


class TestNodeShape:

    def test_valid_single_node_passes(self):
        validate_workflow_graph(_single_node_graph())  # no exception

    def test_unknown_fragment_raises(self):
        graph = {
            "nodes": [{"use": "not_a_real_fragment.yaml", "with": {"id": "n1"}}],
            "entrypoint": "n1",
        }
        with pytest.raises(ValidationError, match="unknown fragment"):
            validate_workflow_graph(graph)

    def test_known_fragment_resolves_to_node_type(self):
        graph = {
            "nodes": [{"use": "chat.yaml", "with": {"id": "n1", "inputs": {}, "outputs": {}}}],
            "entrypoint": "n1",
        }
        validate_workflow_graph(graph)  # no exception -- 'chat.yaml' -> Chat is a known type

    def test_unknown_type_raises(self):
        graph = {"nodes": [{"type": "NotARealType", "id": "n1"}], "entrypoint": "n1"}
        with pytest.raises(ValidationError, match="unknown type"):
            validate_workflow_graph(graph)

    def test_node_without_use_or_type_raises(self):
        graph = {"nodes": [{"id": "n1"}], "entrypoint": "n1"}
        with pytest.raises(ValidationError, match="'use'.*'type'"):
            validate_workflow_graph(graph)

    def test_missing_id_raises(self):
        graph = {"nodes": [{"type": "Chat", "inputs": {}, "outputs": {}}], "entrypoint": None}
        with pytest.raises(ValidationError, match="missing 'id'"):
            validate_workflow_graph(graph)

    def test_duplicate_id_raises(self):
        graph = {
            "nodes": [_chat_node("dup"), _generate_node("dup")],
            "entrypoint": "dup",
        }
        with pytest.raises(ValidationError, match="Duplicate node id"):
            validate_workflow_graph(graph)


# ---------------------------------------------------------------------------
# Context-field / slot references
# ---------------------------------------------------------------------------

class TestContextAndSlotReferences:

    def test_known_context_field_reference_passes(self):
        node = _chat_node(inputs={"history": "${history}", "last_user_message": "${last_user_message}"})
        validate_workflow_graph({"nodes": [node], "entrypoint": node["id"]})

    def test_unknown_context_field_reference_raises(self):
        node = _chat_node(inputs={"history": "${totally_unknown_field}"})
        with pytest.raises(ValidationError, match="unknown context field"):
            validate_workflow_graph({"nodes": [node], "entrypoint": node["id"]})

    def test_dotted_reference_checks_only_the_base_name(self):
        # Only the part before the first "." is validated against
        # CONTEXT_FIELDS -- "model" is a known field, so an arbitrary
        # dotted suffix on it is not itself an error.
        node = _chat_node(inputs={"history": "${model.some_attr}"})
        validate_workflow_graph({"nodes": [node], "entrypoint": node["id"]})

    def test_dotted_reference_with_unknown_base_raises(self):
        node = _chat_node(inputs={"history": "${totally_unknown.some_attr}"})
        with pytest.raises(ValidationError, match="unknown context field"):
            validate_workflow_graph({"nodes": [node], "entrypoint": node["id"]})

    def test_slot_reference_to_earlier_output_passes(self):
        retrieve = {
            "type": "Retrieve", "id": "r1",
            "inputs": {"dense": None, "sparse": None, "collection": "${collection}", "options": {}},
            "outputs": {"hits": "hits1"},
        }
        augment = {
            "type": "Augment", "id": "a1",
            "inputs": {"prompt": None, "hits": "?hits1", "template": None, "attachments": None},
            "outputs": {"prompt": "augmented"},
        }
        graph = {"nodes": [retrieve, augment], "entrypoint": "r1", "edges": [("r1", "a1")]}
        validate_workflow_graph(graph)  # no exception

    def test_slot_reference_to_not_yet_produced_output_raises(self):
        node = _chat_node(inputs={"history": "?never_produced"})
        with pytest.raises(ValidationError, match="no earlier node produces"):
            validate_workflow_graph({"nodes": [node], "entrypoint": node["id"]})

    def test_nested_dict_input_values_are_checked(self):
        # Retrieve's "options" is a dict of literal/ref values, not a bare string
        retrieve = {
            "type": "Retrieve", "id": "r1",
            "inputs": {"dense": None, "sparse": None, "collection": "${collection}",
                       "options": {"filters": {"max_classification": "${bogus_field}"}}},
            "outputs": {"hits": "hits1"},
        }
        with pytest.raises(ValidationError, match="unknown context field"):
            validate_workflow_graph({"nodes": [retrieve], "entrypoint": "r1"})

    def test_nested_list_input_values_are_checked(self):
        node = _chat_node(inputs={"history": ["${history}", "${bogus_field}"]})
        with pytest.raises(ValidationError, match="unknown context field"):
            validate_workflow_graph({"nodes": [node], "entrypoint": node["id"]})


# ---------------------------------------------------------------------------
# Augment template validation
# ---------------------------------------------------------------------------

class TestAugmentTemplateValidation:

    _VALID_TEMPLATE = "{retrieved_data} {source_map} {user_prompt}"

    def _augment_node(self, template):
        return {
            "type": "Augment", "id": "a1",
            "inputs": {"prompt": None, "hits": None, "template": template, "attachments": None},
            "outputs": {"prompt": "out"},
        }

    def test_valid_template_passes(self):
        node = self._augment_node(self._VALID_TEMPLATE)
        validate_workflow_graph({"nodes": [node], "entrypoint": "a1"})

    def test_template_with_attached_documents_placeholder_passes(self):
        node = self._augment_node(self._VALID_TEMPLATE + " {attached_documents}")
        validate_workflow_graph({"nodes": [node], "entrypoint": "a1"})

    @pytest.mark.parametrize("missing", ["{retrieved_data}", "{source_map}"])
    def test_missing_optional_placeholder_passes(self, missing):
        # {retrieved_data}/{source_map} are just how this template happens to
        # surface retrieved context/citations -- an admin is free to omit or
        # restructure those, so only {user_prompt} is a hard requirement.
        template = self._VALID_TEMPLATE.replace(missing, "")
        node = self._augment_node(template)
        validate_workflow_graph({"nodes": [node], "entrypoint": "a1"})

    def test_missing_required_placeholder_raises(self):
        template = self._VALID_TEMPLATE.replace("{user_prompt}", "")
        node = self._augment_node(template)
        with pytest.raises(ValidationError, match="missing required placeholder"):
            validate_workflow_graph({"nodes": [node], "entrypoint": "a1"})

    def test_invalid_format_syntax_raises(self):
        # An unmatched brace breaks str.format() even though the required
        # placeholder is textually present.
        template = self._VALID_TEMPLATE + " {unbalanced"
        node = self._augment_node(template)
        with pytest.raises(ValidationError, match="invalid formatting syntax"):
            validate_workflow_graph({"nodes": [node], "entrypoint": "a1"})

    def test_non_string_template_is_not_validated_as_a_template(self):
        # e.g. a ${...} reference to an admin-configured template, resolved
        # at runtime rather than authored inline -- not validated here.
        node = self._augment_node({"not": "a string"})
        validate_workflow_graph({"nodes": [node], "entrypoint": "a1"})


# ---------------------------------------------------------------------------
# entrypoint / edges (DAG shape)
# ---------------------------------------------------------------------------

class TestEntrypointAndEdges:

    def test_entrypoint_must_be_first_node(self):
        graph = {"nodes": [_chat_node("n1"), _generate_node("n2")], "entrypoint": "n2"}
        with pytest.raises(ValidationError, match="entrypoint must be"):
            validate_workflow_graph(graph)

    def test_no_edges_key_skips_chain_validation(self):
        graph = {"nodes": [_chat_node("n1")], "entrypoint": "n1"}
        validate_workflow_graph(graph)  # no exception

    def test_valid_single_chain_passes(self):
        graph = {
            "nodes": [_chat_node("n1"), _generate_node("n2")],
            "entrypoint": "n1",
            "edges": [("n1", "n2")],
        }
        validate_workflow_graph(graph)

    def test_cycle_raises(self):
        graph = {
            "nodes": [_chat_node("n1"), _generate_node("n2")],
            "entrypoint": "n1",
            "edges": [("n1", "n2"), ("n2", "n1")],
        }
        with pytest.raises(ValidationError, match="Cycle detected"):
            validate_workflow_graph(graph)

    def test_unreachable_node_raises(self):
        graph = {
            "nodes": [_chat_node("n1"), _generate_node("n2"), _generate_node("n3")],
            "entrypoint": "n1",
            "edges": [("n1", "n2")],  # n3 never reached
        }
        with pytest.raises(ValidationError, match="would never run"):
            validate_workflow_graph(graph)


# ---------------------------------------------------------------------------
# has_query_text
# ---------------------------------------------------------------------------

class TestHasQueryText:

    def test_display_content_authoritative_when_present_and_non_blank(self):
        assert has_query_text("hello", None) is True

    def test_display_content_blank_is_false_even_if_message_has_text(self):
        assert has_query_text("   ", "ignored since display content is authoritative") is False

    def test_string_message_used_when_no_display_content(self):
        assert has_query_text(None, "typed text") is True
        assert has_query_text(None, "   ") is False

    def test_multimodal_message_with_text_part(self):
        parts = [{"type": "image", "url": "x"}, {"type": "text", "text": "hi"}]
        assert has_query_text(None, parts) is True

    def test_multimodal_message_without_text_part(self):
        parts = [{"type": "image", "url": "x"}]
        assert has_query_text(None, parts) is False

    def test_multimodal_message_with_blank_text_part(self):
        parts = [{"type": "text", "text": "   "}]
        assert has_query_text(None, parts) is False

    def test_falls_back_to_bool_for_other_types(self):
        assert has_query_text(None, None) is False
