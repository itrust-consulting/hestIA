<script lang="ts">
  import { NODE_TYPES, CONTEXT_FIELDS, type NodeTypeSpec } from '$lib/workflowNodeSpecs';
  import type { WorkflowNode } from '$lib/workflowGraph';

  type Props = {
    node: WorkflowNode;
    availableSlots: string[];
    onChange: (updated: WorkflowNode, previousId: string) => void;
    onDelete: (nodeId: string) => void;
    onClose: () => void;
  };
  const { node, availableSlots, onChange, onDelete, onClose }: Props = $props();

  const spec = $derived(NODE_TYPES.find((nt) => nt.type === node.type) as NodeTypeSpec | undefined);

  type Mode = 'context' | 'slot' | 'literal';

  function modeOf(value: unknown): Mode {
    if (typeof value !== 'string') return 'literal';
    if (/^\$\{[A-Za-z0-9_.]+\}$/.test(value)) return 'context';
    if (/^\?[A-Za-z0-9_]+$/.test(value)) return 'slot';
    return 'literal';
  }

  function bareValue(value: unknown, mode: Mode): string {
    if (typeof value !== 'string') return '';
    if (mode === 'context') return value.slice(2, -1);
    if (mode === 'slot') return value.slice(1);
    return value;
  }

  function updateInput(key: string, mode: Mode, bare: string) {
    let value: string;
    if (mode === 'context') value = `\${${bare}}`;
    else if (mode === 'slot') value = `?${bare}`;
    else value = bare;
    onChange({ ...node, inputs: { ...node.inputs, [key]: value } }, node.id);
  }

  function setMode(key: string, mode: Mode) {
    // Prefer an explicit per-node-type default (see NodeTypeSpec.contextDefaults
    // -- needed whenever an input's correct context field isn't the same name,
    // e.g. EncodeDense's "model" input must default to ${embedding_model}, not
    // ${model}). Otherwise, when the input's own name is itself a valid context
    // field (e.g. Chat's "model" input), default straight to that. Both avoid a
    // silent mismatch that would otherwise require a second, non-obvious pick.
    const contextFallback =
      spec?.contextDefaults?.[key] ??
      ((CONTEXT_FIELDS as readonly string[]).includes(key) ? key : (CONTEXT_FIELDS[0] ?? ''));
    const fallback = mode === 'context' ? contextFallback : mode === 'slot' ? (availableSlots[0] ?? '') : '';
    updateInput(key, mode, fallback);
  }

  function updateId(newId: string) {
    if (!newId.trim()) return;
    onChange({ ...node, id: newId.trim() }, node.id);
  }

  function updateOutput(key: string, value: string) {
    onChange({ ...node, outputs: { ...node.outputs, [key]: value } }, node.id);
  }
</script>

<div class="inspector">
  <div class="inspector-header">
    <h3 class="section-title">{node.type}</h3>
    <button class="close-btn" onclick={onClose} title="Close">×</button>
  </div>

  <label class="field">
    <span>Node id</span>
    <input type="text" value={node.id} onblur={(e) => updateId(e.currentTarget.value)} />
  </label>

  {#if spec}
    {#each spec.inputs as key (key)}
      {@const value = node.inputs[key]}
      {@const mode = modeOf(value)}
      {@const bare = bareValue(value, mode)}
      <div class="field">
        <span>{key}</span>
        <div class="mode-row">
          <select value={mode} onchange={(e) => setMode(key, e.currentTarget.value as Mode)}>
            <option value="context">Context field</option>
            <option value="slot">Earlier node's output</option>
            <option value="literal">Literal value</option>
          </select>
        </div>
        {#if mode === 'context'}
          <select value={bare} onchange={(e) => updateInput(key, mode, e.currentTarget.value)}>
            {#each CONTEXT_FIELDS as f (f)}
              <option value={f}>${'{'}{f}{'}'}</option>
            {/each}
          </select>
        {:else if mode === 'slot'}
          {#if availableSlots.length === 0}
            <span class="hint">No earlier node produces an output yet.</span>
          {:else}
            <select value={bare} onchange={(e) => updateInput(key, mode, e.currentTarget.value)}>
              {#each availableSlots as slot (slot)}
                <option value={slot}>?{slot}</option>
              {/each}
            </select>
          {/if}
        {:else if key === 'template'}
          <textarea class="template-editor" value={bare} onblur={(e) => updateInput(key, mode, e.currentTarget.value)}></textarea>
        {:else}
          <input type="text" value={bare} onblur={(e) => updateInput(key, mode, e.currentTarget.value)} />
        {/if}
      </div>
    {/each}

    <h3 class="section-title" style="margin-top:1rem">Outputs</h3>
    {#each spec.outputs as key (key)}
      <label class="field">
        <span>{key} &rarr; slot name</span>
        <input type="text" value={String(node.outputs[key] ?? '')} onblur={(e) => updateOutput(key, e.currentTarget.value)} />
      </label>
    {/each}
  {/if}

  <div class="inspector-footer">
    <button class="del-btn" onclick={() => onDelete(node.id)}>Delete node</button>
  </div>
</div>

<style>
.inspector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.inspector-header { display: flex; justify-content: space-between; align-items: center; }
.section-title { font-size: var(--text-sm); font-weight: 700; color: var(--color-neutral-800); }
.close-btn { background: none; border: none; font-size: 1.2rem; line-height: 1; cursor: pointer; color: var(--color-neutral-500); }
.close-btn:hover { color: var(--color-neutral-800); }

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input[type="text"], .field select {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
  width: 100%;
}
.mode-row select { font-size: var(--text-xs); }
.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); }

.template-editor {
  width: 100%;
  min-height: 12rem;
  padding: 0.5rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  resize: vertical;
}

.inspector-footer { margin-top: 0.5rem; }
.del-btn {
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  width: 100%;
}
.del-btn:hover { background: var(--color-red-50); }
</style>
