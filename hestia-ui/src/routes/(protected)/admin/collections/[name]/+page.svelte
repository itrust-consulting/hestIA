<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import DocumentUploadModal from '$lib/components/modals/DocumentUploadModal.svelte';
  import SyncFolderModal from '$lib/components/modals/SyncFolderModal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import type { AccessGrant, Collection, CollectionDocument, Org } from '$lib/types';
  import { addToast } from '$lib/stores/toast';
  import { classificationLabel, CLASSIFICATION_OPTIONS, CLASSIFICATION_LABELS } from '$lib/classification';

  const { data }: { data: { collection: Collection; allOrganizations: Org[]; isAdmin: boolean; canManage: boolean } } = $props();
  const c = $derived(data.collection);

  const ownerTenant   = $derived<Org | null>(c.ownerTenant);
  const accessTenants = $derived<AccessGrant[]>(c.access);
  const allOrgs       = $derived<Org[]>(data.allOrganizations ?? []);

  const grantableOrgs = $derived(
    allOrgs.filter(o => {
      const isOwner   = ownerTenant && o.id === ownerTenant.id;
      const hasAccess = accessTenants.some(t => t.id === o.id);
      return !isOwner && !hasAccess;
    })
  );

  function statusClass(s: string) {
    if (s === 'green')  return 'badge-green';
    if (s === 'yellow') return 'badge-yellow';
    return 'badge-red';
  }

  // ── Manage access modal ───────────────────────────────────────────────
  let manageAccessOpen = $state(false);

  function openManageAccess() {
    selectedGrantOrg = null;
    manageAccessOpen = true;
  }

  // ── Grant access ──────────────────────────────────────────────────────
  let selectedGrantOrg = $state<number | null>(null);
  let grantMaxClass    = $state<number | null>(null);
  let granting = $state(false);

  async function grantAccess() {
    if (!selectedGrantOrg) return;
    granting = true;
    try {
      const res = await fetch(
        `/api/admin/tenants/${selectedGrantOrg}/collections/${encodeURIComponent(c.id)}`,
        {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ role: 'access', max_classification: grantMaxClass }),
        },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      selectedGrantOrg = null;
      grantMaxClass    = null;
      addToast('Access granted.', 'success');
      await invalidateAll();
    } catch {
      addToast('Failed to grant access.', 'error');
    } finally {
      granting = false;
    }
  }

  // ── Revoke access ─────────────────────────────────────────────────────
  let revokingId = $state<number | null>(null);

  async function revokeAccess(orgId: number) {
    revokingId = orgId;
    try {
      const res = await fetch(
        `/api/admin/tenants/${orgId}/collections/${encodeURIComponent(c.id)}`,
        { method: 'DELETE' },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      addToast('Access revoked.', 'success');
      await invalidateAll();
    } catch {
      addToast('Failed to revoke access.', 'error');
    } finally {
      revokingId = null;
    }
  }

  // ── Collection delete ──────────────────────────────────────────────────
  let confirmDelete = $state(false);

  async function handleDelete() {
    const res = await fetch(`/api/admin/collections/${encodeURIComponent(c.id)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete collection.');
    await goto('/admin/collections');
  }

  // ── Document delete ────────────────────────────────────────────────────
  let confirmDeleteDoc = $state<string | null>(null);

  async function handleDeleteDoc() {
    const res = await fetch(
      `/api/admin/collections/${encodeURIComponent(c.id)}/documents?source_uri=${encodeURIComponent(confirmDeleteDoc!)}`,
      { method: 'DELETE' },
    );
    if (!res.ok) throw new Error('Failed to delete document.');
    await invalidateAll();
  }

  // ── Upload / replace ───────────────────────────────────────────────────
  let uploadOpen = $state(false);
  let syncOpen = $state(false);
  let confirmingReplace = $state<CollectionDocument | null>(null);

  async function handleSyncSuccess() { await invalidateAll(); }

  async function handleUploadSuccess() { await invalidateAll(); }

  async function doReplace() {
    const res = await fetch(
      `/api/admin/collections/${encodeURIComponent(c.id)}/documents?source_uri=${encodeURIComponent(confirmingReplace!.source_uri)}`,
      { method: 'DELETE' },
    );
    if (!res.ok) throw new Error('Failed to delete document.');
    await invalidateAll();
    uploadOpen = true;
  }
</script>

<div class="admin-content">
  <!-- ── Page header ─────────────────────────────────────────────────── -->
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="title">{c.id}</h1>
      <span class="badge {statusClass(c.status)}">{c.status}</span>
    </div>
    <div class="page-header-right">
      <button class="add-btn" onclick={() => (uploadOpen = true)}>Add document</button>
      <button class="sync-btn" onclick={() => (syncOpen = true)}>Sync folder</button>
      {#if data.canManage}
        <button class="secondary-btn" onclick={openManageAccess}>Manage access</button>
        <button class="danger-btn" onclick={() => (confirmDelete = true)}>Delete collection</button>
      {/if}
    </div>
  </div>

  <!-- ── Stat cards ─────────────────────────────────────────────────── -->
  <div class="stats-row">
    <div class="stat-card">
      <span class="stat-label">Total chunks</span>
      <span class="stat-value">{c.points_count.toLocaleString()}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Documents</span>
      <span class="stat-value">{c.documents.length}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Owner</span>
      {#if ownerTenant}
        <div class="stat-value">{ownerTenant.abbreviation}</div>
      {:else}
        <span class="stat-value muted">—</span>
      {/if}
    </div>
    <div class="stat-card">
      <span class="stat-label">Access</span>
      {#if c.access.length}
        <div class="access-chips">
          {#each c.access as a}
            <span class="access-chip">{a.abbreviation}</span>
          {/each}
        </div>
      {:else}
        <span class="stat-value muted">—</span>
      {/if}
    </div>
  </div>


  <!-- ── Documents table ───────────────────────────────────────────────── -->
  <div class="table-container">
    <h2 class="section-title">Documents</h2>
    <table class="doc-table">
      <thead>
        <tr>
          <th>Document</th>
          <th>Uploaded by</th>
          <th>Uploaded at</th>
          <th class="right">Chunks</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {#if c.documents.length === 0}
          <tr><td colspan="5" class="empty-cell">No documents found.</td></tr>
        {:else}
          {#each c.documents as doc (doc.source_uri)}
            <tr>
              <td class="filename">{doc.source}</td>
              <td>{doc.uploaded_by || '—'}</td>
              <td class="timestamp">
                {#if doc.uploaded_at}
                  {new Date(doc.uploaded_at).toLocaleString()}
                {:else}
                  <span class="muted">—</span>
                {/if}
              </td>
              <td class="right">{doc.chunk_count}</td>
              <td class="actions-cell">
                <button class="replace-btn" onclick={() => (confirmingReplace = doc)}>Replace</button>
                <button class="del-btn" onclick={() => (confirmDeleteDoc = doc.source_uri)}>Delete</button>
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
</div>

<!-- ── Upload modal ──────────────────────────────────────────────────── -->
<DocumentUploadModal
  open={uploadOpen}
  onClose={() => (uploadOpen = false)}
  collectionName={c.id}
  defaultTenants={c.access.map(a => a.abbreviation)}
  onSuccess={handleUploadSuccess}
/>

<SyncFolderModal
  open={syncOpen}
  onClose={() => (syncOpen = false)}
  collectionName={c.id}
  defaultTenants={c.access.map(a => a.abbreviation)}
  onSuccess={handleSyncSuccess}
/>

<ConfirmDeleteModal
  open={confirmingReplace !== null}
  title="Replace document"
  onClose={() => (confirmingReplace = null)}
  onConfirm={doReplace}
  confirmLabel="Continue"
>
  <p>This will delete <strong>{confirmingReplace?.source}</strong> and open the upload dialog so you can add the replacement.</p>
</ConfirmDeleteModal>

<ConfirmDeleteModal
  open={confirmDeleteDoc !== null}
  title="Delete document"
  onClose={() => (confirmDeleteDoc = null)}
  onConfirm={handleDeleteDoc}
  successMessage="Document deleted."
>
  <p>Remove all chunks for <strong>{confirmDeleteDoc}</strong> from <strong>{c.id}</strong>?</p>
  <p>This cannot be undone.</p>
</ConfirmDeleteModal>

<ConfirmDeleteModal
  open={confirmDelete}
  title="Delete collection"
  onClose={() => (confirmDelete = false)}
  onConfirm={handleDelete}
  successMessage="Collection deleted."
>
  <p>Permanently delete <strong>{c.id}</strong> and all its documents?</p>
  <p>This cannot be undone.</p>
</ConfirmDeleteModal>

<!-- ── Manage access modal ────────────────────────────────────────────── -->
<Modal title="Manage Access" open={manageAccessOpen} onClose={() => (manageAccessOpen = false)}>
  <div class="access-modal-body">
    {#if accessTenants.length === 0}
      <p class="no-access">No tenants currently have access.</p>
    {:else}
      <div class="access-list">
        {#each accessTenants as org}
          <div class="access-row">
            <span class="abbr-chip">{org.abbreviation}</span>
            <span class="access-name">{org.name}</span>
            <span class="max-class-badge">
              {org.max_classification !== null ? `max: ${classificationLabel(org.max_classification)}` : 'no cap'}
            </span>
            <button
              class="revoke-btn"
              onclick={() => revokeAccess(org.id)}
              disabled={revokingId === org.id}
            >
              {revokingId === org.id ? 'Revoking…' : 'Revoke'}
            </button>
          </div>
        {/each}
      </div>
    {/if}

    {#if grantableOrgs.length > 0}
      <div class="grant-row">
        <select class="grant-select" bind:value={selectedGrantOrg}>
          <option value={null} disabled>Select tenant…</option>
          {#each grantableOrgs as org}
            <option value={org.id}>{org.name} ({org.abbreviation})</option>
          {/each}
        </select>
        <select class="grant-class-input" bind:value={grantMaxClass}>
          <option value={null}>No cap</option>
          {#each CLASSIFICATION_OPTIONS as lvl}
            <option value={lvl}>{CLASSIFICATION_LABELS[lvl]}</option>
          {/each}
        </select>
        <button class="grant-btn" onclick={grantAccess} disabled={granting || !selectedGrantOrg}>
          {granting ? 'Granting…' : 'Grant access'}
        </button>
      </div>
    {/if}
  </div>
</Modal>

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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  gap: 1rem;
}
.page-header-left { display: flex; align-items: center; gap: 0.75rem; }
.page-header-right { display: flex; align-items: center; gap: 0.5rem; }

.title { font-size: var(--text-3xl); font-weight: 700; margin: 0; }

.badge {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: capitalize;
  flex-shrink: 0;
}
.badge-green  { background: var(--color-green-100);  color: var(--color-green-700); }
.badge-yellow { background: var(--color-yellow-100); color: var(--color-yellow-700); }
.badge-red    { background: var(--color-red-100);    color: var(--color-red-700); }

/* ── Stat cards ──────────────────────────────────────────────────────── */
.stats-row { display: flex; gap: 1rem; margin-bottom: 1rem; }
.stat-card {
  display: flex; flex-direction: column; gap: 0.25rem;
  background: var(--color-neutral-50); padding: 1rem 1.5rem;
  border-radius: var(--radius-xl); box-shadow: 0 2px 8px rgba(0,0,0,0.05); min-width: 130px;
  max-width: 20rem;
}
.stat-value { font-size: var(--text-2xl); font-weight: 700; color: var(--color-neutral-900); }
.stat-label { font-size: var(--text-xs); color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: 0.05em; }
.muted { color: var(--color-neutral-400); }

.owner-row { display: flex; align-items: center; gap: 0.4rem; }
.owner-name { font-size: var(--text-sm); color: var(--color-neutral-700); }

/* ── Access section card ─────────────────────────────────────────────── */
.section-card {
  background: var(--color-neutral-50);
  border-radius: var(--radius-xl);
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  margin-bottom: 1rem;
}

.section-card-header {
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--color-neutral-100);
}

.section-title { font-size: var(--text-sm); font-weight: 600; margin: 0; color: var(--color-neutral-700); text-transform: uppercase; letter-spacing: 0.04em; }

.access-body {
  padding: 0.875rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

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
  gap: 0.35rem;
  margin-top: 0.1rem;
}

.access-chip {
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  border: 1px solid var(--color-blue-200);
  border-radius: 999px;
  padding: 0.1rem 0.55rem;
  font-size: var(--text-xs);
  font-weight: 500;
}

.chip-tenant-name {
  font-size: var(--text-xs);
  color: var(--color-neutral-600);
  padding-right: 0.2rem;
}

.chip-revoke {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 50%;
  border: none;
  background: var(--color-neutral-200);
  color: var(--color-neutral-500);
  font-size: 0.65rem;
  cursor: pointer;
  line-height: 1;
  flex-shrink: 0;
}
.chip-revoke:hover:not(:disabled) { background: var(--color-red-100); color: var(--color-red-600); }
.chip-revoke:disabled { opacity: 0.4; cursor: not-allowed; }

.no-access { font-size: var(--text-sm); color: var(--color-neutral-400); }

.grant-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  padding-top: 0.25rem;
  border-top: 1px solid var(--color-neutral-100);
}

.grant-select {
  flex: 1;
  max-width: 16rem;
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-neutral-50);
  color: var(--color-neutral-800);
}
.grant-select:focus { outline: none; border-color: var(--color-blue-400); }
.grant-class-input {
  width: 9rem;
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-neutral-50);
  color: var(--color-neutral-800);
}
.grant-class-input:focus { outline: none; border-color: var(--color-blue-400); }
.max-class-badge {
  font-size: var(--text-xs);
  color: var(--color-neutral-500);
  background: var(--color-neutral-100);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  padding: 0.1rem 0.45rem;
  white-space: nowrap;
}

.grant-btn {
  padding: 0.35rem 0.875rem;
  background: var(--color-blue-600);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.grant-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.grant-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Documents table ─────────────────────────────────────────────────── */
.table-container {
  background: var(--color-neutral-50); padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl); box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  max-height: calc(100vh - 22rem); overflow-y: auto;
}

.doc-table { width: 100%; border-collapse: collapse; }
.doc-table th, .doc-table td {
  padding: 0.65rem 0.875rem; border-bottom: 1px solid var(--color-neutral-200);
  text-align: left; vertical-align: middle; font-size: var(--text-sm);
}
.doc-table thead th {
  position: sticky; top: 0; background: var(--color-neutral-50); z-index: 2;
  font-weight: 600; color: var(--color-neutral-600);
  font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em;
  box-shadow: 0 1px 0 var(--color-neutral-200);
}
.doc-table tbody tr:hover { background: var(--color-neutral-50); }
.doc-table td.filename { font-weight: 500; word-break: break-all; }
.doc-table td.right, .doc-table th.right { text-align: right; }
.doc-table td.timestamp { color: var(--color-neutral-600); font-size: var(--text-xs); white-space: nowrap; }
.doc-table td.actions-cell { width: 9rem; text-align: right; display: flex; gap: 0.35rem; justify-content: flex-end; align-items: center; }
.empty-cell { text-align: center; padding: 2rem; color: var(--color-neutral-500); }

/* ── Access modal ────────────────────────────────────────────────────── */
.access-modal-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 22rem;
}

.access-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.access-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--color-neutral-100);
}
.access-row:last-child { border-bottom: none; }

.access-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-neutral-700);
}

.revoke-btn {
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-xs);
  white-space: nowrap;
}
.revoke-btn:hover:not(:disabled) { background: var(--color-red-50); }
.revoke-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Buttons ─────────────────────────────────────────────────────────── */
.add-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.add-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.add-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.sync-btn {
  background: var(--color-green-500); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.sync-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.sync-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.secondary-btn {
  background: var(--color-neutral-100); color: var(--color-neutral-800);
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  font-size: var(--text-sm); font-weight: 500; border: 1px solid var(--color-neutral-300); cursor: pointer;
}
.secondary-btn:hover { background: var(--color-neutral-200); }

.danger-btn {
  background: var(--color-red-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.danger-btn:hover:not(:disabled) { background: var(--color-red-700); }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.replace-btn {
  background: transparent; border: 1px solid var(--color-neutral-300); color: var(--color-neutral-600);
  padding: 0.2rem 0.55rem; border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-xs);
}
.replace-btn:hover { background: var(--color-neutral-100); }

.del-btn {
  background: transparent; border: 1px solid var(--color-red-300); color: var(--color-red-600);
  padding: 0.2rem 0.55rem; border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-xs);
}
.del-btn:hover { background: var(--color-red-50); }

</style>
