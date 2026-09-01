<script lang="ts">
  import { SvelteFlowProvider } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import WorkflowCanvasInner from './WorkflowCanvasInner.svelte';
  import type { WorkflowGraphState } from '$lib/workflowGraph';

  type Props = {
    initialGraph: WorkflowGraphState;
    onChange: (graph: WorkflowGraphState) => void;
  };
  const { initialGraph, onChange }: Props = $props();
</script>

<SvelteFlowProvider>
  <WorkflowCanvasInner {initialGraph} {onChange} />
</SvelteFlowProvider>
