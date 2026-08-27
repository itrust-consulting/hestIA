<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import { addToast } from '$lib/stores/toast';

  const { data } = $props();

  type Tenant = { id: number; name: string; abbreviation: string; created_at: number; member_count?: number };

  const formatDate = (ts: number) =>
    ts ? new Date(ts).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

  // ── Create ──────────────────────────────────────────────────────────────
  let createOpen = $state(false);
  let createName = $state('');
  let createAbbr = $state('');
  let createSaving = $state(false);

  function openCreate() {
    createName = '';
    createAbbr = '';
    createOpen = true;
  }

  async function handleCreate() {
    if (!createName.trim() || !createAbbr.trim()) return;
    createSaving = true;
    try {
      const res = await fetch('/api/admin/tenants', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: createName.trim(), abbreviation: createAbbr.trim() }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Tenant created.', 'success');
      createOpen = false;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to create tenant.', 'error');
    } finally {
      createSaving = false;
    }
  }

  // ── Delete ──────────────────────────────────────────────────────────────
  let confirmDelete = $state<Tenant | null>(null);

  async function handleDelete() {
    const res = await fetch(`/api/admin/tenants/${confirmDelete!.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete tenant.');
    await invalidateAll();
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="title">{data.isAdmin ? 'Tenant Management' : 'My Tenants'}</h1>
  </div>
  <div class="subtitle-row">
    <p class="subtitle">{data.isAdmin ? 'Manage organisations and their document access.' : 'Organisations you moderate.'}</p>
    {#if data.isAdmin}
      <button class="icon-btn" title="Add tenant" onclick={openCreate}>
        <PlusLgIcon />
      </button>
    {/if}
  </div>

  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>No.</th>
          <th>Name</th>
          <th>Abbreviation</th>
          <th>Members</th>
          <th>Created</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#if data.tenants.length === 0}
          <tr><td colspan="6" class="loading-cell">No tenants found.</td></tr>
        {:else}
          {#each data.tenants as t, i}
            <tr class="clickable-row" onclick={() => goto(`/admin/tenants/${t.id}`)}>
              <td class="num">{i + 1}</td>
              <td class="name">{t.name}</td>
              <td class="abbr"><span class="abbr-chip">{t.abbreviation}</span></td>
              <td class="members-cell">
                {#if t.member_count}
                  {t.member_count}
                {:else}
                  <span class="no-members">—</span>
                {/if}
              </td>
              <td class="muted">{formatDate(t.created_at)}</td>
              <td class="actions-cell">
                {#if data.isAdmin}
                  <button class="del-btn" aria-label="Delete tenant" title="Delete" onclick={(e) => { e.stopPropagation(); confirmDelete = t; }}><BinIcon /></button>
                {/if}
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
</div>

<!-- ── Create modal ──────────────────────────────────────────────────────── -->
<Modal title="Create Tenant" open={createOpen} onClose={() => (createOpen = false)}>
  <div class="form-stack">
    <label class="field">
      <span>Name <span class="req">*</span></span>
      <input type="text" bind:value={createName} placeholder="e.g. Acme Corp" />
    </label>
    <label class="field">
      <span>Abbreviation <span class="req">*</span></span>
      <input type="text" bind:value={createAbbr} placeholder="e.g. ACME" />
    </label>
  </div>
  <svelte:fragment slot="footer">
    <button class="action-btn" onclick={handleCreate}
      disabled={createSaving || !createName.trim() || !createAbbr.trim()}>
      {createSaving ? 'Saving…' : 'Create'}
    </button>
  </svelte:fragment>
</Modal>

<ConfirmDeleteModal
  open={confirmDelete !== null}
  title="Delete Tenant"
  onClose={() => (confirmDelete = null)}
  onConfirm={handleDelete}
  successMessage="Tenant deleted."
>
  <p>Permanently delete <strong>{confirmDelete?.name}</strong>?</p>
  <p>This will remove the tenant from all users but will not affect documents in the knowledge base.</p>
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
  margin-bottom: 0.25rem;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 0;
}

.subtitle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.subtitle {
  color: var(--color-neutral-600);
}

.table-container {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-neutral-200);
  text-align: left;
  vertical-align: middle;
}
.data-table thead th {
  position: sticky;
  top: 0;
  background: var(--color-neutral-50);
  z-index: 2;
  font-weight: 600;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-600);
  box-shadow: 0 1px 0 var(--color-neutral-200);
}
.clickable-row { cursor: pointer; transition: background 100ms ease; }
.clickable-row:hover { background: var(--color-neutral-100); }

td.num { width: 4rem; text-align: right; color: var(--color-neutral-400); }
td.name { font-weight: 500; }
td.muted { color: var(--color-neutr-500); font-size: var(--text-sm); }
td.actions-cell { width: 5rem; text-align: right; }

td.members-cell { width: 6rem; }
.no-members { color: var(--color-neutral-400); }

.abbr-chip {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.03em;
}

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }


.del-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.35rem;
  border-radius: var(--radius-md);
  cursor: pointer;
}
.del-btn:hover { background: var(--color-red-50); }


.loading-cell {
  text-align: center;
  padding: 2rem;
  color: var(--color-neutral-500);
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

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
}
.field input[type="text"]:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.req { color: var(--color-red-500); }
</style>
