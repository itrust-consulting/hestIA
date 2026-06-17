from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict

import yaml

from hestia.domain.exceptions import ConfigurationError
from hestia.domain.rag.graph import ExecutionGraph, ExecutionRequest, Node


_log = logging.getLogger("hestia.system")

TEMPLATE_DIR = "hestia/templates"

CTX_PATTERN = re.compile(r"\$\{([A-Za-z0-9_.]+)\}")
CTX_EXACT_PATTERN = re.compile(r"^\$\{([A-Za-z0-9_.]+)\}$")
SLOT_PATTERN = re.compile(r"^\?([A-Za-z0-9_]+)$")


class TemplateRepository:

    def __init__(self, templates_dir: str = TEMPLATE_DIR):
        if not os.path.isdir(templates_dir):
            raise ConfigurationError(f"Templates directory not found: {templates_dir}")
        self.templates_dir = templates_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_yaml(self, rel_path: str) -> Dict[str, Any]:
        path = os.path.join(self.templates_dir, rel_path)
        if path in self._cache:
            return self._cache[path]
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Template not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self._cache[path] = data
        return data


# @MRS-035
class TemplatePlanBuilder:

    def __init__(self, repo: TemplateRepository):
        self.repo = repo

    def preload(self, template_rel_paths: list) -> None:
        for rel_path in template_rel_paths:
            root = self.repo.load_yaml(rel_path)
            self._load_fragments(root, rel_path)
            _log.debug("template_preloaded", extra={"template": rel_path})

    def build(self, request: ExecutionRequest, template_rel_path: str) -> ExecutionGraph:
        _log.debug("template_build", extra={
            "template": template_rel_path,
            "exec_type": request.exec_type,
            "ctx_keys": [k for k, v in self._build_ctx(request).items() if v is not None],
        })
        root = self.repo.load_yaml(template_rel_path)
        fragments = self._load_fragments(root, template_rel_path)
        ctx = self._build_ctx(request)

        hydrated_nodes = [self._hydrate_node(entry, fragments, ctx) for entry in root.get("nodes", [])]

        graph = self._to_graph({
            "entrypoint": root.get("entrypoint"),
            "exitpoints": root.get("exitpoints", []),
            "nodes": hydrated_nodes,
            "edges": root.get("edges", []),
            "context_refs": root.get("context_refs", {}),
        })
        _log.debug("template_build_done", extra={
            "template": template_rel_path,
            "n_nodes": len(graph.nodes),
            "entrypoint": graph.entrypoint,
        })
        return graph

    def _load_fragments(self, root: dict, template_rel_path: str) -> dict:
        fragments = {}
        for inc in (root.get("include") or []):
            abs_path = self._resolve_rel(template_rel_path, inc)
            fragments[os.path.basename(inc)] = self.repo.load_yaml(abs_path)
        return fragments

    def _hydrate_node(self, entry: dict, fragments: dict, ctx: dict) -> dict:
        if "use" in entry:
            frag_name = entry["use"]
            if frag_name not in fragments:
                raise ConfigurationError(f"Fragment '{frag_name}' not found — check template includes.")
            base = fragments[frag_name]
            overrides = self._interpolate_strings(entry.get("with", {}), ctx)
            merged = self._merge_fragment(base, overrides)
            merged = self._inject_raw_ctx(merged, ctx)
            return self._interpolate_strings(merged, ctx)
        node = self._interpolate_strings(entry, ctx)
        return self._inject_raw_ctx(node, ctx)

    def _interpolate_strings(self, data, ctx: dict):
        if isinstance(data, str):
            if SLOT_PATTERN.match(data):
                return data
            m = CTX_EXACT_PATTERN.match(data)
            if m:
                val = self._resolve_key(ctx, m.group(1))
                if val is not None and not isinstance(val, str):
                    return val  # preserve list/dict/numeric types
            return self._interpolate_str(data, ctx)
        if isinstance(data, dict):
            return {k: self._interpolate_strings(v, ctx) for k, v in data.items()}
        if isinstance(data, list):
            return [self._interpolate_strings(v, ctx) for v in data]
        return data

    def _interpolate_str(self, s: str, ctx: dict) -> str:
        def repl(m):
            val = self._resolve_key(ctx, m.group(1))
            return "" if val is None else str(val)
        return CTX_PATTERN.sub(repl, s)

    def _inject_raw_ctx(self, data, ctx: dict):
        if isinstance(data, dict):
            return {k: self._inject_raw_ctx(v, ctx) for k, v in data.items()}
        if isinstance(data, list):
            return [self._inject_raw_ctx(v, ctx) for v in data]
        if isinstance(data, str):
            if SLOT_PATTERN.match(data):
                return data
            m = CTX_EXACT_PATTERN.match(data)
            if m:
                return self._resolve_key(ctx, m.group(1))
        return data

    def _resolve_key(self, ctx: Dict[str, Any], dotted: str):
        cur = ctx
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    def _resolve_rel(self, base_rel: str, inc_rel: str) -> str:
        return os.path.normpath(os.path.join(os.path.dirname(base_rel), inc_rel))

    def _build_ctx(self, req: ExecutionRequest) -> dict:
        return {
            "prompt": req.prompt,
            "history": req.history,
            "last_user_message": req.last_user_message,
            "model": req.model,
            "model_kwargs": req.model_kwargs,
            "collection": req.collection,
            "query_kwargs": req.query_kwargs,
        }

    def _merge_fragment(self, frag: dict, overrides: dict) -> dict:
        out = dict(frag)
        for k, v in overrides.items():
            if k in ("inputs", "outputs") and isinstance(v, dict):
                out[k] = {**out.get(k, {}), **v}
            else:
                out[k] = v
        return out

    def _to_graph(self, hydrated: dict) -> ExecutionGraph:
        nodes_raw = hydrated.get("nodes", [])
        nodes = [
            Node(
                id=n["id"],
                type=n["type"],
                inputs=n.get("inputs", {}),
                outputs=n.get("outputs", {}),
                model=n.get("model"),
            )
            for n in nodes_raw
        ]

        edges = hydrated.get("edges", [])
        if not edges and len(nodes) > 1:
            edges = [(nodes[i].id, nodes[i + 1].id) for i in range(len(nodes) - 1)]

        entrypoint = hydrated.get("entrypoint") or (nodes[0].id if nodes else "")
        exitpoints = hydrated.get("exitpoints") or ([nodes[-1].id] if nodes else [])

        return ExecutionGraph(
            nodes=nodes,
            edges=edges,
            entrypoint=entrypoint,
            exitpoints=exitpoints,
            context_refs=hydrated.get("context_refs", {}),
        )


def chain(p1: ExecutionGraph, p2: ExecutionGraph) -> ExecutionGraph:
    nodes = p1.nodes + p2.nodes
    edges = p1.edges + [(p1.exitpoints[0], p2.entrypoint)] + p2.edges
    return ExecutionGraph(
        nodes=nodes,
        edges=edges,
        entrypoint=p1.entrypoint,
        exitpoints=p2.exitpoints,
        context_refs={**p1.context_refs, **p2.context_refs},
    )
