from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from hestia.domain.auth.models import User
from hestia.domain.exceptions import ValidationError


class ExecutionRequest(BaseModel):
    user: User
    exec_type: str
    history: Optional[List[Dict[str, Any]]] = None
    last_user_message: Optional[Union[str, List[Any]]] = None
    last_user_display_content: Optional[str] = None
    last_user_attachments: Optional[List[Dict[str, Any]]] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    save_chat: bool = False
    stream: bool = False
    # Set by RequestHandler._check_and_compact_budget when this turn's
    # incoming history was over budget and got folded before generation
    # started -- carried through so the final stream frame can announce it.
    freed_tokens: Optional[int] = None
    # Set by RequestHandler.resolve() from the currently-configured
    # 'embedding' LLM connection -- never sent by the client and never
    # per-request-overridable, unlike model/model_kwargs. Retrieval only
    # works if the query is embedded with the same model used at ingestion
    # time, so this always reflects the admin-configured connection, not
    # anything the request could influence.
    embedding_model: Optional[str] = None
    embedding_model_kwargs: Optional[Dict[str, Any]] = None


class Node(BaseModel):
    id: str
    type: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]


# @MRS-058
class ExecutionGraph(BaseModel):
    nodes: List[Node]
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    entrypoint: str
    exitpoints: List[str] = Field(default_factory=list)
    context_refs: Dict[str, str] = Field(default_factory=dict)


# The six node types Runner (hestia/handler.py) actually implements, and the
# inputs/outputs keys each one really reads/writes -- used to validate
# admin-authored workflow YAML before it's written to disk (see
# hestia/api/routers/workflow_settings.py) and mirrored on the frontend
# (hestia-ui/src/lib/workflowNodeSpecs.ts) so the editor can show what each
# type needs without cross-referencing Python.
NODE_TYPE_SPECS: Dict[str, Dict[str, List[str]]] = {
    "EncodeDense":  {"inputs": ["data", "model", "model_kwargs"], "outputs": ["vector"]},
    "EncodeSparse": {"inputs": ["data", "collection"], "outputs": ["vector"]},
    "Retrieve":     {"inputs": ["dense", "sparse", "collection", "options"], "outputs": ["hits"]},
    "Augment":      {"inputs": ["prompt", "hits", "template", "attachments"], "outputs": ["prompt"]},
    "Generate":     {"inputs": ["prompt", "model", "options"], "outputs": ["response"]},
    "Chat":         {"inputs": ["history", "last_user_message", "model", "options"], "outputs": ["response"]},
}

# hestia/templates/base/*.yaml fragment filenames -> the node type they back.
FRAGMENT_TO_TYPE: Dict[str, str] = {
    "encode_dense.yaml":  "EncodeDense",
    "encode_sparse.yaml": "EncodeSparse",
    "retrieve.yaml":      "Retrieve",
    "augment.yaml":       "Augment",
    "generate.yaml":      "Generate",
    "chat.yaml":          "Chat",
}

# The fixed set of ${...} context fields TemplatePlanBuilder._build_ctx
# actually populates from an ExecutionRequest.
def has_query_text(last_user_display_content, last_user_message) -> bool:
    """Whether a turn carries any user-typed text, as opposed to only file
    attachments -- used both to decide whether retrieval should run at all
    (see api/routers/chat.py) and to choose how attachments are framed for
    the LLM (see templater.py's _format_attachments). last_user_display_content
    is authoritative when present -- it's exactly the typed text, with any
    attachment markdown excluded. Falls back to inspecting the raw message
    content for callers that don't set it."""
    if last_user_display_content is not None:
        return bool(last_user_display_content.strip())
    if isinstance(last_user_message, str):
        return bool(last_user_message.strip())
    if isinstance(last_user_message, list):
        return any(
            isinstance(part, dict) and part.get("type") == "text" and (part.get("text") or "").strip()
            for part in last_user_message
        )
    return bool(last_user_message)


CONTEXT_FIELDS = frozenset({
    "prompt", "history", "last_user_message", "attached_documents", "model", "model_kwargs", "collection",
    "query_kwargs", "embedding_model", "embedding_model_kwargs",
})

_CTX_REF = re.compile(r"^\$\{([A-Za-z0-9_.]+)\}$")
_SLOT_REF = re.compile(r"^\?([A-Za-z0-9_]+)$")

# hestia/handler.py's _build_prompt() does template.format(retrieved_data=,
# source_map=, user_prompt=) -- .format() silently ignores an omitted named
# placeholder rather than raising, so a template missing {user_prompt}
# wouldn't crash, it would just silently drop the user's question from
# every RAG request. {retrieved_data}/{source_map} are just how this
# template happens to surface retrieved context/citations -- an admin is
# free to omit or restructure those -- so only {user_prompt} is enforced.
_REQUIRED_AUGMENT_PLACEHOLDERS = ("{user_prompt}",)


def _iter_ref_values(value: Any):
    """Yields every string leaf inside a possibly-nested inputs value (plain
    strings, or nested dicts/lists of them) -- an input isn't always a bare
    string, e.g. Retrieve's `options` is often a dict of literal values."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_ref_values(v)
    elif isinstance(value, list):
        for v in value:
            yield from _iter_ref_values(v)


def validate_workflow_graph(root: Dict[str, Any]) -> None:
    """Validates an admin-authored workflow YAML's parsed root dict before
    it's written to disk. Raises ValidationError (400) with a clear message
    on the first problem found -- not exhaustive, just enough to catch a
    broken graph before it fails on a live chat/generate request instead."""
    nodes_raw = root.get("nodes")
    if not nodes_raw:
        raise ValidationError("A workflow must have at least one node.")

    ids: List[str] = []
    produced_slots: set[str] = set()
    entries: List[Dict[str, Any]] = []

    for i, entry in enumerate(nodes_raw):
        if "use" in entry:
            frag = entry["use"]
            if frag not in FRAGMENT_TO_TYPE:
                raise ValidationError(
                    f"Node {i}: unknown fragment '{frag}' -- must be one of {sorted(FRAGMENT_TO_TYPE)}."
                )
            node_type = FRAGMENT_TO_TYPE[frag]
            with_block = entry.get("with", {}) or {}
            node_id = with_block.get("id")
            inputs = with_block.get("inputs", {}) or {}
            outputs = with_block.get("outputs", {}) or {}
        elif "type" in entry:
            node_type = entry["type"]
            if node_type not in NODE_TYPE_SPECS:
                raise ValidationError(
                    f"Node {i}: unknown type '{node_type}' -- must be one of {sorted(NODE_TYPE_SPECS)}."
                )
            node_id = entry.get("id")
            inputs = entry.get("inputs", {}) or {}
            outputs = entry.get("outputs", {}) or {}
        else:
            raise ValidationError(f"Node {i}: must have either 'use' (a base fragment) or 'type'.")

        if not node_id:
            raise ValidationError(f"Node {i}: missing 'id'.")
        if node_id in ids:
            raise ValidationError(f"Duplicate node id '{node_id}'.")
        ids.append(node_id)

        for raw_value in _iter_ref_values(inputs):
            ctx_match = _CTX_REF.match(raw_value)
            if ctx_match and ctx_match.group(1).split(".")[0] not in CONTEXT_FIELDS:
                raise ValidationError(
                    f"Node '{node_id}': '{raw_value}' references an unknown context field "
                    f"'{ctx_match.group(1)}' -- must be one of {sorted(CONTEXT_FIELDS)}."
                )
            slot_match = _SLOT_REF.match(raw_value)
            if slot_match and slot_match.group(1) not in produced_slots:
                raise ValidationError(
                    f"Node '{node_id}': '{raw_value}' references slot '{slot_match.group(1)}', "
                    "which no earlier node produces."
                )

        if node_type == "Augment" and isinstance(inputs.get("template"), str):
            template = inputs["template"]
            missing = [p for p in _REQUIRED_AUGMENT_PLACEHOLDERS if p not in template]
            if missing:
                raise ValidationError(
                    f"Node '{node_id}': template is missing required placeholder(s) {missing}."
                )
            try:
                # attached_documents is optional (Runner always passes it,
                # defaulting to "" -- see handler.py's _run_augment), so a
                # template using it must still validate even though it's
                # not in _REQUIRED_AUGMENT_PLACEHOLDERS.
                template.format(retrieved_data="x", source_map="x", user_prompt="x", attached_documents="x")
            except (KeyError, IndexError, ValueError) as e:
                raise ValidationError(f"Node '{node_id}': template has invalid formatting syntax -- {e}.")

        for out_value in outputs.values():
            if isinstance(out_value, str):
                produced_slots.add(out_value)

        entries.append({"id": node_id, "type": node_type})

    entrypoint = root.get("entrypoint")
    if entrypoint != ids[0]:
        raise ValidationError(f"entrypoint must be '{ids[0]}' (the first node) -- got '{entrypoint}'.")

    edges = root.get("edges")
    if edges:
        order = [ids[0]]
        cur = ids[0]
        while True:
            nxt = next((b for a, b in edges if a == cur), None)
            if nxt is None:
                break
            if nxt in order:
                raise ValidationError(f"Cycle detected in edges at node '{nxt}'.")
            order.append(nxt)
            cur = nxt
        if set(order) != set(ids):
            missing = set(ids) - set(order)
            raise ValidationError(
                f"edges must form a single chain through every node -- "
                f"{sorted(missing)} would never run (the execution engine has no branching support)."
            )
