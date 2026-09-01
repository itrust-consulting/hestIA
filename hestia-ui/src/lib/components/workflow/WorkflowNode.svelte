<script lang="ts">
  import { Handle, Position, type NodeProps } from '@xyflow/svelte';

  let { data, selected }: NodeProps = $props();

  const inputEntries = $derived(Object.entries(data.inputs ?? {}) as [string, unknown][]);

  function preview(value: unknown): string {
    if (typeof value !== 'string') return JSON.stringify(value);
    return value.length > 28 ? `${value.slice(0, 28)}…` : value;
  }
</script>

<Handle type="target" position={Position.Top} />
<div class="workflow-node" class:selected>
  <div class="node-type">{data.nodeType}</div>
  <div class="node-id">{data.label}</div>
  {#if inputEntries.length > 0}
    <div class="node-inputs">
      {#each inputEntries as [key, value] (key)}
        <div class="node-input-row"><span class="key">{key}:</span> {preview(value)}</div>
      {/each}
    </div>
  {:else}
    <div class="node-empty">no inputs set</div>
  {/if}
</div>
<Handle type="source" position={Position.Bottom} />

<style>
.workflow-node {
  min-width: 11rem;
  max-width: 15rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  padding: 0.5rem 0.7rem;
  font-size: var(--text-xs);
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.workflow-node.selected {
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.node-type {
  font-weight: 700;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-blue-700);
}
.node-id {
  font-weight: 600;
  font-size: var(--text-sm);
  margin-bottom: 0.3rem;
}
.node-inputs { display: flex; flex-direction: column; gap: 0.15rem; }
.node-input-row {
  color: var(--color-neutral-600);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-input-row .key { font-weight: 600; color: var(--color-neutral-500); }
.node-empty { color: var(--color-neutral-400); font-style: italic; }
</style>
