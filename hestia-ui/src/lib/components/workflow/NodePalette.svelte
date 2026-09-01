<script lang="ts">
  import { NODE_TYPES } from '$lib/workflowNodeSpecs';

  // Native HTML5 drag-and-drop, matching Svelte Flow's own documented
  // drag-and-drop-from-sidebar pattern -- WorkflowCanvas reads this data
  // type on drop to know which node type to instantiate.
  function handleDragStart(event: DragEvent, type: string) {
    if (!event.dataTransfer) return;
    event.dataTransfer.setData('application/workflow-node-type', type);
    event.dataTransfer.effectAllowed = 'move';
  }
</script>

<div class="palette">
  <h3 class="section-title">Node types</h3>
  <p class="hint">Drag a node onto the canvas.</p>
  {#each NODE_TYPES as nt (nt.type)}
    <div
      class="palette-item"
      draggable="true"
      ondragstart={(e) => handleDragStart(e, nt.type)}
      role="listitem"
    >
      <div class="palette-item-label">{nt.label}</div>
      <div class="palette-item-type">{nt.type}</div>
    </div>
  {/each}
</div>

<style>
.palette {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.section-title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--color-neutral-800);
  margin-bottom: 0.25rem;
}
.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); margin-bottom: 0.5rem; }

.palette-item {
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  padding: 0.5rem 0.7rem;
  cursor: grab;
  user-select: none;
}
.palette-item:hover { background: var(--color-neutral-50); border-color: var(--color-blue-400); }
.palette-item:active { cursor: grabbing; }
.palette-item-label { font-weight: 600; font-size: var(--text-sm); }
.palette-item-type {
  font-size: var(--text-xs);
  color: var(--color-neutral-500);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
