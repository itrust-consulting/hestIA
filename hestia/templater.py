import os
import re
import yaml
from typing import Any, Dict

from hestia.schemas.api import ExecutionGraph, Node


TEMPLATE_DIR = "hestia/templates"

# ${var} interpolation (context namespace)
CTX_PATTERN = re.compile(r"\$\{([A-Za-z0-9_.]+)\}")

# Exact match for raw injection
CTX_EXACT_PATTERN = re.compile(r"^\$\{([A-Za-z0-9_.]+)\}$")

# @slotvar references (runtime slot variables)
SLOT_PATTERN = re.compile(r"^\?([A-Za-z0-9_]+)$")


class TemplateRepository:
    def __init__(self, templates_dir: str = TEMPLATE_DIR):
        if not os.path.isdir(templates_dir):
            raise ValueError(f"Templates directory not found: {templates_dir}")
        self.templates_dir = templates_dir

    def load_yaml(self, rel_path: str) -> Dict[str, Any]:
        path = os.path.join(self.templates_dir, rel_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Template not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


class TemplatePlanBuilder:
    """
    Builds an ExecutionGraph from YAML workflow templates.
    Supports:
      - ${var}       → context variables (from ExecutionRequest)
      - ?var         → slot variables (runtime outputs from previous nodes)
      - include:     → fragment templates
      - use: / with: → fragment-based node construction

    Applies a safe two-phase interpolation strategy:
      1. Interpolate strings containing ${...}
      2. Replace whole-field ${var} with raw Python values
      3. Preserve ?var for runtime slot reference (no stringification)
    """

    def __init__(self, repo):
        self.repo = repo

    def build(self, request, template_rel_path: str):
        root = self.repo.load_yaml(template_rel_path)

        fragments = self._load_fragments(root, template_rel_path)

        ctx = self._build_ctx(request)

        hydrated_nodes = []
        for entry in root.get("nodes", []):
            node = self._hydrate_node(entry, fragments, ctx)
            hydrated_nodes.append(node)

        return self._to_graph({
            "entrypoint": root.get("entrypoint"),
            "exitpoints": root.get("exitpoints", []),
            "nodes": hydrated_nodes,
            "edges": root.get("edges", []),
            "context_refs": root.get("context_refs", {}),
        })

    def _load_fragments(self, root, template_rel_path):
        fragments = {}
        for inc in (root.get("include") or []):
            abs_path = self._resolve_rel(template_rel_path, inc)
            fragments[os.path.basename(inc)] = self.repo.load_yaml(abs_path)
        return fragments

    def _hydrate_node(self, entry, fragments, ctx):
        if "use" in entry:
            frag_name = entry["use"]
            if frag_name not in fragments:
                raise ValueError(f"Fragment '{frag_name}' not included.")

            base = fragments[frag_name]
            overrides = entry.get("with", {})

            overrides = self._interpolate_strings(overrides, ctx)
            merged = self._merge_fragment(base, overrides)
            merged = self._inject_raw_ctx(merged, ctx)
            merged = self._interpolate_strings(merged, ctx)

            # slot refs (`?var`) remain unchanged
            return merged

        # direct node
        node = self._interpolate_strings(entry, ctx)
        node = self._inject_raw_ctx(node, ctx)
        return node

    def _interpolate_strings(self, data, ctx):
        if isinstance(data, str):
            # leave ?var untouched
            if SLOT_PATTERN.match(data):
                return data
            return self._interpolate_str(data, ctx)
        return data

    def _interpolate_str(self, s: str, ctx):
        def repl(m):
            key = m.group(1)
            val = self._resolve_key(ctx, key)
            return "" if val is None else str(val)
        return CTX_PATTERN.sub(repl, s)

    def _inject_raw_ctx(self, data, ctx):
        if isinstance(data, dict):
            return {k: self._inject_raw_ctx(v, ctx) for k, v in data.items()}
        if isinstance(data, list):
            return [self._inject_raw_ctx(v, ctx) for v in data]

        if isinstance(data, str):
            # Keep ?slot vars untouched here
            if SLOT_PATTERN.match(data):
                return data

            m = CTX_EXACT_PATTERN.match(data)
            if m:
                key = m.group(1)
                return self._resolve_key(ctx, key)

        return data

    def _resolve_key(self, ctx: Dict[str, Any], dotted: str):
        cur = ctx
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    def _resolve_rel(self, base_rel, inc_rel):
        return os.path.normpath(os.path.join(os.path.dirname(base_rel), inc_rel))

    def _build_ctx(self, req):
        return {
            "prompt": req.prompt,
            "history": req.history,
            "last_user_message": req.last_user_message,
            "model": req.model,
            "model_kwargs": req.model_kwargs,
            "collection": req.collection,
            "query_kwargs": req.query_kwargs,
        }

    def _merge_fragment(self, frag, overrides):
        out = dict(frag)
        for k, v in overrides.items():
            if k in ("inputs", "outputs") and isinstance(v, dict):
                base = dict(out.get(k, {}))
                base.update(v)
                out[k] = base
            else:
                out[k] = v
        return out

    def _to_graph(self, hydrated):
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
        if not edges and nodes:
            for i in range(len(nodes) - 1):
                edges.append((nodes[i].id, nodes[i+1].id))

        entrypoint = hydrated.get("entrypoint") or (nodes[0].id if nodes else None)
        exitpoints = hydrated.get("exitpoints") or ([nodes[-1].id] if nodes else [])

        return ExecutionGraph(
            nodes=nodes,
            edges=edges,
            entrypoint=entrypoint,
            exitpoints=exitpoints,
            context_refs=hydrated.get("context_refs", {}),
        )

def chain(p1: ExecutionGraph, p2: ExecutionGraph) -> ExecutionGraph:
    """Linear chain: p1 → p2 (connect p1.exit -> p2.entry)."""
    nodes = p1.nodes + p2.nodes
    edges = p1.edges + [(p1.exitpoints[0], p2.entrypoint)] + p2.edges
    return ExecutionGraph(
        nodes=nodes,
        edges=edges,
        entrypoint=p1.entrypoint,
        exitpoints=p2.exitpoints,
        context_refs={**p1.context_refs, **p2.context_refs},
    )