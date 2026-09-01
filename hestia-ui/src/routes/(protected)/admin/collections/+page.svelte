<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import CreateCollectionModal from '$lib/components/modals/CreateCollectionModal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import type { Collection } from '$lib/types';
  import type { PageData } from './$types';

  const { data }: { data: PageData } = $props();

  const collections: Collection[] = $derived(data.collections ?? []);
  const ownerOrgs = $derived(data.ownerOrgs ?? []);
  const allOrganizations = $derived(data.allOrganizations ?? []);

  let uploadOpen = $state(false);
  let confirmDelete = $state<string | null>(null);

  function handleCreateSuccess(collectionName: string) {
    goto(`/admin/collections/${encodeURIComponent(collectionName)}`);
  }

  async function handleDelete() {
    const res = await fetch(`/api/admin/collections/${encodeURIComponent(confirmDelete!)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete collection.');
    await invalidateAll();
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="title">Knowledge Base</h1>
  </div>
  <div class="subtitle-row">
    <p class="subtitle">{data.isAdmin ? 'All collections across the system and their access configuration.' : 'Collections belonging to your moderated tenants.'}</p>
    <button class="icon-btn" title="Create collection" onclick={() => (uploadOpen = true)}>
      <PlusLgIcon />
    </button>
  </div>

  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>Collection</th>
          <th>Owner</th>
          <th>Documents</th>
          <th>Status</th>
          <th>Access granted to</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#if collections.length === 0}
          <tr><td colspan="6" class="empty-cell">No collections found.</td></tr>
        {:else}
          {#each collections as col}
            <tr class="clickable-row" onclick={() => goto(`/admin/collections/${encodeURIComponent(col.id)}`)}>
              <td class="col-name">{col.id}</td>
              <td>
                {#if col.ownerTenant}
                  <span class="abbr-chip" title={col.ownerTenant.name}>{col.ownerTenant.abbreviation}</span>
                {:else}
                  <span class="muted">—</span>
                {/if}
              </td>
              <td class="muted">{col.documentCount}</td>
              <td>
                <span class="status-badge" class:green={col.status === 'green'}>{col.status}</span>
              </td>
              <td>
                {#if col.access.length === 0}
                  <span class="muted">None</span>
                {:else}
                  <div class="access-chips">
                    {#each col.access as a}
                      <span class="abbr-chip" title={a.name}>{a.abbreviation}</span>
                    {/each}
                  </div>
                {/if}
              </td>
              {#if data.isAdmin}
                <td class="actions-cell">
                  <button class="del-btn" aria-label="Delete collection" title="Delete" onclick={(e) => { e.stopPropagation(); confirmDelete = col.id; }}>
                    <BinIcon />
                  </button>
                </td>
              {/if}
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
</div>

<ConfirmDeleteModal
  open={confirmDelete !== null}
  title="Delete collection"
  onClose={() => (confirmDelete = null)}
  onConfirm={handleDelete}
  successMessage="Collection deleted."
>
  <p>Permanently delete <strong>{confirmDelete}</strong> and all its vectors?</p>
  <p>This cannot be undone.</p>
</ConfirmDeleteModal>

<CreateCollectionModal
  open={uploadOpen}
  onClose={() => (uploadOpen = false)}
  ownerOrgs={ownerOrgs}
  accessOrgs={allOrganizations}
  onSuccess={handleCreateSuccess}
/>

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

td.col-name { font-weight: 500; color: var(--color-neutral-800); }
td.muted { color: var(--color-neutral-500); font-size: var(--text-sm); }
td.actions-cell { width: 5rem; text-align: right; }


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

.access-chips {
  display: flex;
  flex-wrap: wrap;
  max-width: 18rem;
  gap: 0.3rem;
}

.status-badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: var(--color-neutral-100);
  color: var(--color-neutral-600);
  font-size: var(--text-xs);
  font-weight: 500;
}

.status-badge.green {
  background: var(--color-green-50);
  color: var(--color-green-700);
}

.muted { color: var(--color-neutral-400); font-size: var(--text-sm); }

.empty-cell {
  text-align: center;
  padding: 2rem;
  color: var(--color-neutral-500);
}

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


</style>
