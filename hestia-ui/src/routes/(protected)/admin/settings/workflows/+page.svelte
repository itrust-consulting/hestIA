<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { addToast } from '$lib/stores/toast';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import EditIcon from '$lib/components/icons/editIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  const { data } = $props();

  const LABELS: Record<string, string> = {
    generate: 'Generate',
    rag_generate: 'RAG Generate',
    chat: 'Chat',
    rag_chat: 'RAG Chat',
  };

  // Duplicated (not shared -- no cross-language codegen here) from the
  // backend's _NAME_PATTERN in hestia/api/routers/workflow_settings.py.
  // Keep both in sync -- this copy only pre-empts a round-trip for a bad
  // name; the backend's is the actual enforcement.
  const NAME_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

  let resetting = $state<string | null>(null);
  let confirmDelete = $state<{ exec_type: string } | null>(null);

  async function resetWorkflow(execType: string) {
    resetting = execType;
    try {
      const res = await fetch(`/api/admin/workflows/${execType}`, { method: 'DELETE' });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Workflow reset to default.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to reset workflow.', 'error');
    } finally {
      resetting = null;
    }
  }

  async function deleteWorkflow() {
    const res = await fetch(`/api/admin/workflows/${confirmDelete!.exec_type}`, { method: 'DELETE' });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail ?? 'Failed to delete workflow.');
    }
    await invalidateAll();
  }

  // ── New workflow ─────────────────────────────────────────────────────────
  let createOpen = $state(false);
  let newName = $state('');
  let creating = $state(false);
  let createError = $state<string | null>(null);

  const newNameValid = $derived(NAME_PATTERN.test(newName));

  function openCreate() {
    newName = '';
    createError = null;
    createOpen = true;
  }

  async function handleCreate() {
    if (!newNameValid || creating) return;
    creating = true;
    createError = null;
    try {
      const res = await fetch('/api/admin/workflows', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: newName }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      createOpen = false;
      await goto(`/admin/settings/workflows/${newName}`);
    } catch (e: any) {
      createError = e.message ?? 'Failed to create workflow.';
    } finally {
      creating = false;
    }
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="title">Workflows</h1>
      <p class="subtitle">
        Each request type is executed as an ordered sequence of nodes (Encode, Retrieve, Augment, Generate, Chat).
        Edit the YAML below to change how a request type is handled.
      </p>
    </div>
  </div>

  <div class="section-header">
    <button class="icon-btn" aria-label="New workflow" use:tooltip={"New workflow"} onclick={openCreate}>
      <PlusLgIcon />
    </button>
  </div>

  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>Request type</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each data.workflows as w (w.exec_type)}
          <tr class="clickable-row" onclick={() => goto(`/admin/settings/workflows/${w.exec_type}`)}>
            <td class="label-cell">{LABELS[w.exec_type] ?? w.exec_type}</td>
            <td>
              {#if w.is_custom}
                <span class="custom-badge">Custom</span>
              {:else}
                <span class="muted">Default</span>
              {/if}
            </td>
            <td class="actions-cell">
              <button class="edit-btn" aria-label="Edit workflow" use:tooltip={"Edit"} onclick={(e) => { e.stopPropagation(); goto(`/admin/settings/workflows/${w.exec_type}`); }}>
                <EditIcon />
              </button>
              {#if w.is_builtin}
                {#if w.is_custom}
                  <button class="del-btn" disabled={resetting === w.exec_type} onclick={(e) => { e.stopPropagation(); resetWorkflow(w.exec_type); }}>
                    {resetting === w.exec_type ? 'Resetting…' : 'Reset to default'}
                  </button>
                {/if}
              {:else}
                <button class="del-btn" onclick={(e) => { e.stopPropagation(); confirmDelete = { exec_type: w.exec_type }; }}>
                  Delete
                </button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

<Modal title="New Workflow" open={createOpen} onClose={() => (createOpen = false)}>
  <label class="field">
    <span>Name <span class="hint">(letters, numbers, underscore, hyphen)</span></span>
    <input type="text" bind:value={newName} placeholder="my_custom_workflow" />
    {#if newName && !newNameValid}<div class="field-error">Invalid name.</div>{/if}
  </label>
  {#if createError}<div class="field-error">{createError}</div>{/if}
  <svelte:fragment slot="footer">
    <button class="action-btn" disabled={!newNameValid || creating} onclick={handleCreate}>
      {creating ? 'Creating…' : 'Create'}
    </button>
  </svelte:fragment>
</Modal>

<ConfirmDeleteModal
  open={confirmDelete !== null}
  title="Delete Workflow"
  onClose={() => (confirmDelete = null)}
  onConfirm={deleteWorkflow}
  successMessage="Workflow deleted."
>
  <p>Permanently delete <strong>{confirmDelete?.exec_type}</strong>? This workflow has no built-in default to fall back to.</p>
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

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.page-header-left { flex: 1; }

.section-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: 0.75rem;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.subtitle {
  color: var(--color-neutral-600);
  margin-bottom: 0;
}

.table-container {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-neutral-200);
  text-align: left;
  vertical-align: middle;
}
.data-table thead th {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-neutral-600);
}
.data-table tbody tr:last-child td { border-bottom: none; }

.clickable-row { cursor: pointer; transition: background 100ms ease; }
.clickable-row:hover { background: var(--color-neutral-100); }

.label-cell { font-weight: 500; }
.muted { color: var(--color-neutral-500); font-size: var(--text-sm); }

.custom-badge {
  display: inline-block;
  background: var(--color-blue-100);
  color: var(--color-blue-700);
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 600;
}

.actions-cell { display: flex; gap: 0.4rem; justify-content: flex-end; }

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.edit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-neutral-300);
  color: var(--color-neutral-700);
  padding: 0.35rem;
  border-radius: var(--radius-md);
  cursor: pointer;
}
.edit-btn:hover { background: var(--color-neutral-100); }

.del-btn {
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
}
.del-btn:hover:not(:disabled) { background: var(--color-red-50); }
.del-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input[type="text"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
  width: 100%;
}
.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); }

.field-error {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  margin-top: 0.5rem;
}
</style>
