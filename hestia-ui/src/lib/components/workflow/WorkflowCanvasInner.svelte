<script lang="ts">
  import { SvelteFlow, Background, Controls, useSvelteFlow, type Node as FlowNode, type Edge as FlowEdge, type Connection } from '@xyflow/svelte';
  import WorkflowNode from './WorkflowNode.svelte';
  import NodeInspector from './NodeInspector.svelte';
  import { createNode, type WorkflowGraphState, type WorkflowNode as GraphNode } from '$lib/workflowGraph';
  import { addToast } from '$lib/stores/toast';

  // Rendered as a child of <SvelteFlowProvider> (see WorkflowCanvas.svelte) --
  // useSvelteFlow() below only resolves its context from an ancestor
  // provider, which a component instantiating <SvelteFlow> itself can't be
  // (context propagates to descendants, not siblings), hence the split.
  type Props = {
    initialGraph: WorkflowGraphState;
    onChange: (graph: WorkflowGraphState) => void;
  };
  const { initialGraph, onChange }: Props = $props();

  const nodeTypes = { workflowNode: WorkflowNode };

  function toFlowNode(n: GraphNode): FlowNode {
    return {
      id: n.id,
      type: 'workflowNode',
      position: n.position,
      data: { nodeType: n.type, label: n.id, inputs: n.inputs, outputs: n.outputs },
    };
  }

  function toFlowEdge([source, target]: [string, string]): FlowEdge {
    return { id: `${source}->${target}`, source, target };
  }

  let flowNodes = $state.raw<FlowNode[]>(initialGraph.nodes.map(toFlowNode));
  let flowEdges = $state.raw<FlowEdge[]>(initialGraph.edges.map(toFlowEdge));
  let selectedNodeId = $state<string | null>(null);

  const selectedNode = $derived.by(() => {
    const flow = flowNodes.find((n) => n.id === selectedNodeId);
    if (!flow) return null;
    return graphNodeFromFlow(flow);
  });

  // Output slot names produced by every node that precedes `nodeId` in the
  // current chain (only nodes reachable by walking edges backward from it) --
  // fed to NodeInspector's "Earlier node's output" picker.
  const availableSlots = $derived.by(() => {
    if (!selectedNodeId) return [];
    const incoming = new Map(flowEdges.map((e) => [e.target, e.source]));
    const slots: string[] = [];
    let cur: string | undefined = incoming.get(selectedNodeId);
    const seen = new Set<string>();
    while (cur && !seen.has(cur)) {
      seen.add(cur);
      const node = flowNodes.find((n) => n.id === cur);
      if (node) slots.push(...(Object.values(node.data.outputs ?? {}) as string[]));
      cur = incoming.get(cur);
    }
    return slots;
  });

  function graphNodeFromFlow(n: FlowNode): GraphNode {
    return {
      id: n.id,
      type: n.data.nodeType as string,
      inputs: (n.data.inputs as Record<string, unknown>) ?? {},
      outputs: (n.data.outputs as Record<string, unknown>) ?? {},
      position: n.position,
    };
  }

  function emitChange() {
    onChange({
      nodes: flowNodes.map(graphNodeFromFlow),
      edges: flowEdges.map((e) => [e.source, e.target] as [string, string]),
    });
  }

  function hasOutgoing(nodeId: string): boolean {
    return flowEdges.some((e) => e.source === nodeId);
  }

  function isValidConnection(candidate: Connection | FlowEdge): boolean {
    const source = 'source' in candidate ? candidate.source : undefined;
    if (!source) return false;
    if (hasOutgoing(source)) {
      addToast('This node already has an outgoing connection -- workflows run as a single linear chain.', 'error');
      return false;
    }
    return true;
  }

  function handleConnect(connection: Connection) {
    flowEdges = [...flowEdges, { id: `${connection.source}->${connection.target}`, source: connection.source, target: connection.target }];
    emitChange();
  }

  function handleNodeClick({ node }: { node: FlowNode }) {
    selectedNodeId = node.id;
  }

  function handlePaneClick() {
    selectedNodeId = null;
  }

  function handleNodeDragStop() {
    emitChange();
  }

  function handleInspectorChange(updated: GraphNode, previousId: string) {
    flowNodes = flowNodes.map((n) => (n.id === previousId ? toFlowNode(updated) : n));
    if (updated.id !== previousId) {
      flowEdges = flowEdges.map((e) => ({
        ...e,
        id: e.id.replace(previousId, updated.id),
        source: e.source === previousId ? updated.id : e.source,
        target: e.target === previousId ? updated.id : e.target,
      }));
      selectedNodeId = updated.id;
    }
    emitChange();
  }

  function handleDeleteNode(nodeId: string) {
    flowNodes = flowNodes.filter((n) => n.id !== nodeId);
    flowEdges = flowEdges.filter((e) => e.source !== nodeId && e.target !== nodeId);
    if (selectedNodeId === nodeId) selectedNodeId = null;
    emitChange();
  }

  const { screenToFlowPosition } = useSvelteFlow();

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    const type = event.dataTransfer?.getData('application/workflow-node-type');
    if (!type) return;
    const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const newNode = createNode(type, position, flowNodes.map((n) => n.id));
    flowNodes = [...flowNodes, toFlowNode(newNode)];
    emitChange();
  }
</script>

<div class="canvas-layout">
  <div class="canvas-area" ondragover={handleDragOver} ondrop={handleDrop} role="application">
    <SvelteFlow
      bind:nodes={flowNodes}
      bind:edges={flowEdges}
      {nodeTypes}
      {isValidConnection}
      onconnect={handleConnect}
      onnodeclick={handleNodeClick}
      onnodedragstop={handleNodeDragStop}
      onpaneclick={handlePaneClick}
      fitView
      minZoom={0.3}
    >
      <Background />
      <Controls />
    </SvelteFlow>
  </div>

  {#if selectedNode}
    <div class="inspector-panel">
      <NodeInspector
        node={selectedNode}
        {availableSlots}
        onChange={handleInspectorChange}
        onDelete={handleDeleteNode}
        onClose={() => (selectedNodeId = null)}
      />
    </div>
  {/if}
</div>

<style>
.canvas-layout {
  display: grid;
  grid-template-columns: 1fr 18rem;
  gap: 1rem;
  height: 34rem;
}
.canvas-area {
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-neutral-50);
}
.inspector-panel {
  background: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg);
  padding: 0.75rem;
  overflow-y: auto;
}
</style>
