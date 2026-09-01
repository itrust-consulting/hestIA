// Parses/serializes the same workflow YAML shape hestia/domain/rag/graph.py's
// validate_workflow_graph() and hestia/domain/rag/templater.py's
// TemplatePlanBuilder work with, into a flat, canvas-friendly form (one
// in-memory model shared by the visual editor and the YAML tab). Both
// use:/with: fragment-shorthand nodes and direct inline {id, type, inputs,
// outputs} nodes are accepted on parse (most shipped defaults still use the
// shorthand for non-Augment nodes); serialization always emits inline nodes,
// matching the "admin-authored nodes are self-contained" convention.

import { parse as parseYamlText, stringify as stringifyYaml } from 'yaml';
import { NODE_TYPES } from './workflowNodeSpecs';

const FRAGMENT_TO_TYPE: Record<string, string> = Object.fromEntries(
  NODE_TYPES.map((nt) => [nt.fragment, nt.type])
);

export type WorkflowNode = {
  id: string;
  type: string;
  // Real inputs/outputs values are almost always strings (${ctx}, ?slot, or
  // literal text) -- the one exception is a hand-authored nested dict/list
  // value (e.g. a literal Retrieve.options object), which round-trips
  // unchanged since the inspector only edits string-valued fields.
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  position: { x: number; y: number };
};

export type WorkflowGraphState = {
  nodes: WorkflowNode[];
  edges: [string, string][];
};

type FlatNode = {
  id: string;
  type: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  position?: { x: number; y: number };
};

function flattenEntry(entry: any, index: number): FlatNode {
  if (entry.use) {
    const type = FRAGMENT_TO_TYPE[entry.use];
    if (!type) throw new Error(`Node ${index}: unknown fragment '${entry.use}'.`);
    const withBlock = entry.with ?? {};
    if (!withBlock.id) throw new Error(`Node ${index}: missing 'id'.`);
    return {
      id: withBlock.id as string,
      type,
      inputs: withBlock.inputs ?? {},
      outputs: withBlock.outputs ?? {},
      position: withBlock.position as { x: number; y: number } | undefined,
    };
  }
  if (entry.type) {
    if (!entry.id) throw new Error(`Node ${index}: missing 'id'.`);
    return {
      id: entry.id as string,
      type: entry.type as string,
      inputs: entry.inputs ?? {},
      outputs: entry.outputs ?? {},
      position: entry.position as { x: number; y: number } | undefined,
    };
  }
  throw new Error(`Node ${index}: must have either 'use' (a base fragment) or 'type'.`);
}

/** Follows an explicit `edges` list (same shape Runner._linear_order reads)
 * from the first node; falls back to declaration order when absent, exactly
 * like the backend does. */
function declaredOrder(ids: string[], edges: unknown): string[] {
  if (!Array.isArray(edges) || edges.length === 0) return ids;
  const next = new Map<string, string>();
  for (const e of edges) {
    const [a, b] = Array.isArray(e) ? e : [e[0], e[1]];
    next.set(a, b);
  }
  const order = [ids[0]];
  const seen = new Set(order);
  let cur = ids[0];
  while (next.has(cur)) {
    const nxt = next.get(cur)!;
    if (seen.has(nxt)) break; // cycle -- stop rather than loop forever, leave the rest in declaration order
    order.push(nxt);
    seen.add(nxt);
    cur = nxt;
  }
  for (const id of ids) if (!seen.has(id)) order.push(id);
  return order;
}

export function parseWorkflowYaml(yamlText: string): WorkflowGraphState {
  const root = parseYamlText(yamlText);
  if (!root || !Array.isArray(root.nodes) || root.nodes.length === 0) {
    throw new Error('Workflow YAML must have a non-empty "nodes" list.');
  }

  const flat: FlatNode[] = root.nodes.map((entry: any, i: number) => flattenEntry(entry, i));
  const ids: string[] = flat.map((n) => n.id);
  const order = declaredOrder(ids, root.edges);

  const edges: [string, string][] = [];
  for (let i = 0; i < order.length - 1; i++) edges.push([order[i], order[i + 1]]);

  const byId = new Map<string, FlatNode>(flat.map((n) => [n.id, n]));
  const nodes: WorkflowNode[] = order.map((id, i) => {
    const n = byId.get(id)!;
    return {
      id: n.id,
      type: n.type,
      inputs: n.inputs,
      outputs: n.outputs,
      position: n.position ?? { x: 80, y: 60 + i * 150 },
    };
  });

  return { nodes, edges };
}

/** True if `nodeId` already has an outgoing connection -- the one topology
 * rule the canvas enforces interactively (Runner has no branching support),
 * mirroring the check serializeWorkflowGraph()/resolveOrder() do at save time. */
export function hasOutgoingEdge(edges: [string, string][], nodeId: string): boolean {
  return edges.some(([from]) => from === nodeId);
}

/** Walks edges into the single linear chain the engine will actually
 * execute. Throws with a message meant to be shown directly to the admin
 * if the graph isn't a single connected chain through every node. */
export function resolveOrder(state: WorkflowGraphState): string[] {
  const ids = state.nodes.map((n) => n.id);
  if (ids.length === 0) throw new Error('A workflow must have at least one node.');
  if (ids.length === 1) return ids;

  const outgoing = new Map<string, string>();
  const hasIncoming = new Set<string>();
  for (const [a, b] of state.edges) {
    if (outgoing.has(a)) throw new Error(`Node '${a}' has more than one outgoing connection.`);
    outgoing.set(a, b);
    hasIncoming.add(b);
  }
  const starts = ids.filter((id) => !hasIncoming.has(id));
  if (starts.length !== 1) {
    throw new Error('The workflow must be a single connected chain -- connect every node in sequence.');
  }

  const order = [starts[0]];
  const seen = new Set(order);
  let cur = starts[0];
  while (outgoing.has(cur)) {
    const next = outgoing.get(cur)!;
    if (seen.has(next)) throw new Error(`Cycle detected at node '${next}'.`);
    order.push(next);
    seen.add(next);
    cur = next;
  }
  if (order.length !== ids.length) {
    const missing = ids.filter((id) => !seen.has(id));
    throw new Error(`Every node must be connected in sequence -- not connected: ${missing.join(', ')}.`);
  }
  return order;
}

export function serializeWorkflowGraph(state: WorkflowGraphState): string {
  const order = resolveOrder(state);
  const byId = new Map(state.nodes.map((n) => [n.id, n]));
  const orderedNodes = order.map((id) => byId.get(id)!);

  const root = {
    entrypoint: order[0],
    exitpoints: [order[order.length - 1]],
    nodes: orderedNodes.map((n) => ({
      id: n.id,
      type: n.type,
      inputs: n.inputs,
      outputs: n.outputs,
      position: n.position,
    })),
    edges: state.edges,
  };
  return stringifyYaml(root);
}

export function createNode(type: string, position: { x: number; y: number }, existingIds: string[]): WorkflowNode {
  const spec = NODE_TYPES.find((nt) => nt.type === type);
  if (!spec) throw new Error(`Unknown node type '${type}'.`);
  let n = 1;
  while (existingIds.includes(`${type}${n}`)) n++;
  const outputs: Record<string, string> = Object.fromEntries(spec.outputs.map((k) => [k, k]));
  return { id: `${type}${n}`, type, inputs: {}, outputs, position };
}
