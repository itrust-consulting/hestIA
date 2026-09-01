<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { addToast } from '$lib/stores/toast';
  import { NODE_TYPES, CONTEXT_FIELDS } from '$lib/workflowNodeSpecs';
  import { parseWorkflowYaml, serializeWorkflowGraph, type WorkflowGraphState } from '$lib/workflowGraph';
  import WorkflowCanvas from '$lib/components/workflow/WorkflowCanvas.svelte';
  import NodePalette from '$lib/components/workflow/NodePalette.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';

  const { data } = $props();

  const LABELS: Record<string, string> = {
    generate: 'Generate',
    rag_generate: 'RAG Generate',
    chat: 'Chat',
    rag_chat: 'RAG Chat',
  };

  let activeTab = $state<'visual' | 'yaml'>('visual');
  let graph = $state<WorkflowGraphState>(parseGraphOrEmpty(data.workflow.yaml_text));
  let canvasKey = $state(0);
  let yamlDraft = $state(data.workflow.yaml_text);
  let yamlParseError = $state<string | null>(null);
  let savePhase = $state<'saving' | 'resetting' | null>(null);
  let saveError = $state<string | null>(null);

  function parseGraphOrEmpty(yamlText: string): WorkflowGraphState {
    try {
      return parseWorkflowYaml(yamlText);
    } catch {
      return { nodes: [], edges: [] };
    }
  }

  function switchToYaml() {
    try {
      yamlDraft = serializeWorkflowGraph(graph);
      saveError = null;
      activeTab = 'yaml';
    } catch (e: any) {
      saveError = e.message ?? 'Fix the graph before viewing it as YAML.';
    }
  }

  function switchToVisual() {
    try {
      graph = parseWorkflowYaml(yamlDraft);
      yamlParseError = null;
      saveError = null;
      canvasKey++;
      activeTab = 'visual';
    } catch (e: any) {
      yamlParseError = e.message ?? 'Invalid YAML';
    }
  }

  function validateYamlDraft() {
    try {
      parseWorkflowYaml(yamlDraft);
      yamlParseError = null;
    } catch (e: any) {
      yamlParseError = e.message ?? 'Invalid YAML';
    }
  }

  async function handleSave() {
    saveError = null;
    let text: string;
    if (activeTab === 'yaml') {
      try {
        parseWorkflowYaml(yamlDraft); // re-validate before saving
      } catch (e: any) {
        saveError = e.message ?? 'Fix the YAML syntax error above before saving.';
        return;
      }
      text = yamlDraft;
    } else {
      try {
        text = serializeWorkflowGraph(graph);
      } catch (e: any) {
        saveError = e.message ?? 'Fix the graph before saving.';
        return;
      }
    }

    savePhase = 'saving';
    try {
      const res = await fetch(`/api/admin/workflows/${data.workflow.exec_type}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ yaml_text: text }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Workflow saved.', 'success');
      await invalidateAll();
    } catch (e: any) {
      saveError = e.message ?? 'Failed to save.';
    } finally {
      savePhase = null;
    }
  }

  async function handleReset() {
    savePhase = 'resetting';
    saveError = null;
    try {
      const res = await fetch(`/api/admin/workflows/${data.workflow.exec_type}`, { method: 'DELETE' });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Workflow reset to default.', 'success');
      await goto(`/admin/settings/workflows/${data.workflow.exec_type}`, { invalidateAll: true });
    } catch (e: any) {
      saveError = e.message ?? 'Failed to reset.';
    } finally {
      savePhase = null;
    }
  }

  let confirmDeleteOpen = $state(false);

  async function handleDelete() {
    const res = await fetch(`/api/admin/workflows/${data.workflow.exec_type}`, { method: 'DELETE' });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail ?? 'Failed to delete workflow.');
    }
    await goto('/admin/settings/workflows');
  }
</script>

<div class="admin-content">
  <a class="back-link" href="/admin/settings/workflows">&larr; Workflows</a>
  <h1 class="title">{LABELS[data.workflow.exec_type] ?? data.workflow.exec_type}</h1>
  <p class="subtitle">
    An ordered sequence of nodes, executed top to bottom. Each node's <code>inputs</code> can reference
    <code>${'{'}field{'}'}</code> (a value from the incoming request) or <code>?slot</code> (an output from an earlier node).
  </p>

  <div class="tab-row">
    <button class="tab-btn" class:active={activeTab === 'visual'} onclick={switchToVisual}>Visual</button>
    <button class="tab-btn" class:active={activeTab === 'yaml'} onclick={switchToYaml}>YAML</button>
  </div>

  {#if activeTab === 'visual'}
    <div class="visual-layout">
      <div class="canvas-wrap">
        {#key canvasKey}
          <WorkflowCanvas initialGraph={graph} onChange={(g) => (graph = g)} />
        {/key}
      </div>
      <div class="panel palette-panel">
        <NodePalette />
      </div>
    </div>
  {:else}
    <div class="editor-layout">
      <div class="panel editor-panel">
        <textarea
          class="yaml-editor"
          spellcheck="false"
          bind:value={yamlDraft}
          onblur={validateYamlDraft}
        ></textarea>
        {#if yamlParseError}<div class="field-error">{yamlParseError}</div>{/if}
      </div>

      <div class="panel reference-panel">
        <h3 class="section-title">Node types</h3>
        {#each NODE_TYPES as nt (nt.type)}
          <div class="node-type-card">
            <div class="node-type-name">{nt.type}</div>
            <div class="node-type-row"><span class="static-label">inputs</span> {nt.inputs.join(', ')}</div>
            <div class="node-type-row"><span class="static-label">outputs</span> {nt.outputs.join(', ')}</div>
            <div class="node-type-row"><span class="static-label">fragment</span> {nt.fragment}</div>
          </div>
        {/each}

        <h3 class="section-title" style="margin-top:1.25rem">Context fields</h3>
        <p class="hint">Available as <code>${'{'}field{'}'}</code> in any node's inputs.</p>
        <div class="context-fields">
          {#each CONTEXT_FIELDS as f}
            <span class="context-field-chip">{f}</span>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  {#if saveError}<div class="field-error save-error">{saveError}</div>{/if}
  <div class="editor-actions">
    {#if data.workflow.is_builtin}
      <button class="del-btn" disabled={savePhase !== null} onclick={handleReset}>
        {savePhase === 'resetting' ? 'Resetting…' : 'Reset to default'}
      </button>
    {:else}
      <button class="del-btn" disabled={savePhase !== null} onclick={() => (confirmDeleteOpen = true)}>
        Delete workflow
      </button>
    {/if}
    <button class="action-btn" disabled={savePhase !== null} onclick={handleSave}>
      {savePhase === 'saving' ? 'Saving…' : 'Save'}
    </button>
  </div>
</div>

<ConfirmDeleteModal
  open={confirmDeleteOpen}
  title="Delete Workflow"
  onClose={() => (confirmDeleteOpen = false)}
  onConfirm={handleDelete}
>
  <p>Permanently delete <strong>{data.workflow.exec_type}</strong>? This workflow has no built-in default to fall back to.</p>
  <p>This cannot be undone.</p>
</ConfirmDeleteModal>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-6xl);
  margin-inline: auto;
}

.back-link {
  display: inline-block;
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
  text-decoration: none;
  margin-bottom: 0.5rem;
}
.back-link:hover { color: var(--color-neutral-800); }

.title { font-size: var(--text-3xl); font-weight: 700; margin-bottom: 0.25rem; }
.subtitle { color: var(--color-neutral-600); margin-bottom: 1rem; font-size: var(--text-sm); }
.subtitle code { background: var(--color-neutral-100); padding: 0.05rem 0.3rem; border-radius: var(--radius-md); }

.tab-row { display: flex; gap: 0.25rem; margin-bottom: 1rem; }
.tab-btn {
  background: transparent;
  border: 1px solid var(--color-neutral-300);
  color: var(--color-neutral-600);
  padding: 0.4rem 1rem;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: 600;
}
.tab-btn:hover { background: var(--color-neutral-100); }
.tab-btn.active { background: var(--color-blue-600); border-color: var(--color-blue-600); color: white; }

.visual-layout {
  display: grid;
  grid-template-columns: 1fr 14rem;
  gap: 1.5rem;
  align-items: start;
}
.canvas-wrap { min-width: 0; }
.palette-panel { padding: 1rem; }

.editor-layout {
  display: grid;
  grid-template-columns: 1fr 20rem;
  gap: 1.5rem;
  align-items: start;
}

.panel {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.yaml-editor {
  width: 100%;
  min-height: 32rem;
  padding: 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--color-white);
  resize: vertical;
  tab-size: 2;
}
.yaml-editor:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.field-error {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  margin-top: 0.5rem;
}
.save-error { margin-top: 1rem; }

.editor-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.del-btn {
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: var(--text-sm);
}
.del-btn:hover:not(:disabled) { background: var(--color-red-50); }
.del-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.section-title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--color-neutral-800);
  margin-bottom: 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--color-neutral-200);
}

.node-type-card {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-neutral-200);
  font-size: var(--text-xs);
}
.node-type-card:last-of-type { border-bottom: none; }
.node-type-name { font-weight: 600; font-size: var(--text-sm); margin-bottom: 0.2rem; }
.node-type-row { color: var(--color-neutral-600); }
.static-label { font-weight: 600; color: var(--color-neutral-500); margin-right: 0.3rem; }

.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); margin-bottom: 0.5rem; }
.hint code { background: var(--color-neutral-100); padding: 0.05rem 0.3rem; border-radius: var(--radius-md); }

.context-fields { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.context-field-chip {
  display: inline-block;
  background: var(--color-neutral-100);
  color: var(--color-neutral-700);
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
