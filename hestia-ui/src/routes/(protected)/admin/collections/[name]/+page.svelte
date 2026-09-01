<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import DocumentUploadModal from '$lib/components/modals/DocumentUploadModal.svelte';
  import SyncFolderModal from '$lib/components/modals/SyncFolderModal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import type { AccessGrant, Collection, CollectionDocument, Org } from '$lib/types';
  import { addToast } from '$lib/stores/toast';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import UploadIcon from '$lib/components/icons/uploadIcon.svelte';
  import RetryIcon from '$lib/components/icons/retry.svelte';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';
  import { CLASSIFICATION_OPTIONS, CLASSIFICATION_LABELS } from '$lib/classification';

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

  const reassignableOrgs = $derived(
    allOrgs.filter(o => !ownerTenant || o.id !== ownerTenant.id)
  );

  function statusClass(s: string) {
    if (s === 'green')  return 'badge-green';
    if (s === 'yellow') return 'badge-yellow';
    return 'badge-red';
  }

  // ── Manage access modal ───────────────────────────────────────────────
  let manageAccessOpen = $state(false);

  function openManageAccess() {
    selectedOwnerOrg = null;
    closeOrgSearch();
    manageAccessOpen = true;
  }

  // ── Reassign owner (admin only) ────────────────────────────────────────
  let selectedOwnerOrg = $state<number | null>(null);
  let reassigningOwner = $state(false);

  async function reassignOwner() {
    if (!selectedOwnerOrg) return;
    reassigningOwner = true;
    try {
      const res = await fetch(
        `/api/admin/tenants/${selectedOwnerOrg}/collections/${encodeURIComponent(c.id)}`,
        {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ role: 'owner' }),
        },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      selectedOwnerOrg = null;
      addToast('Owner reassigned.', 'success');
      await invalidateAll();
    } catch {
      addToast('Failed to reassign owner.', 'error');
    } finally {
      reassigningOwner = false;
    }
  }

  // ── Grant access (org search popover) ───────────────────────────────────
  let orgSearchOpen      = $state(false);
  let orgSearchQuery     = $state('');
  let addingOrgId        = $state<number | null>(null);
  let orgSearchWrapperEl = $state<HTMLDivElement | null>(null);

  const filteredGrantableOrgs = $derived(
    (() => {
      const q = orgSearchQuery.trim().toLowerCase();
      if (!q) return grantableOrgs;
      return grantableOrgs.filter(o =>
        o.name.toLowerCase().includes(q) || o.abbreviation.toLowerCase().includes(q)
      );
    })()
  );

  function toggleOrgSearch() {
    if (orgSearchOpen) {
      closeOrgSearch();
    } else {
      orgSearchQuery = '';
      orgSearchOpen  = true;
    }
  }

  function closeOrgSearch() {
    orgSearchOpen = false;
  }

  function handleWindowClick(e: MouseEvent) {
    if (orgSearchOpen && orgSearchWrapperEl && !orgSearchWrapperEl.contains(e.target as Node)) {
      closeOrgSearch();
    }
  }

  async function selectOrgForAccess(org: Org) {
    addingOrgId = org.id;
    try {
      const res = await fetch(
        `/api/admin/tenants/${org.id}/collections/${encodeURIComponent(c.id)}`,
        {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ role: 'access', max_classification: 0 }),
        },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      closeOrgSearch();
      addToast('Access granted.', 'success');
      await invalidateAll();
    } catch {
      addToast('Failed to grant access.', 'error');
    } finally {
      addingOrgId = null;
    }
  }

  // ── Update max permission for an access grant ───────────────────────────
  let updatingMaxClass = $state<Record<number, boolean>>({});

  async function updateMaxClassification(orgId: number, level: number) {
    updatingMaxClass = { ...updatingMaxClass, [orgId]: true };
    try {
      const res = await fetch(
        `/api/admin/tenants/${orgId}/collections/${encodeURIComponent(c.id)}`,
        {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ role: 'access', max_classification: level }),
        },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      await invalidateAll();
    } catch {
      addToast('Failed to update permission.', 'error');
    } finally {
      updatingMaxClass = { ...updatingMaxClass, [orgId]: false };
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
  <div class="section-header">
    <h2 class="section-title">Documents</h2>
    <div class="section-header-actions">
      <button class="icon-btn" aria-label="Add document" use:tooltip={"Add document"} onclick={() => (uploadOpen = true)}>
        <UploadIcon />
      </button>
      <button class="icon-btn" aria-label="Sync folder" use:tooltip={"Sync folder"} onclick={() => (syncOpen = true)}>
        <RetryIcon />
      </button>
      {#if data.canManage}
        <button class="icon-btn" aria-label="Manage access" use:tooltip={"Manage access"} onclick={openManageAccess}>
          <SettingsIcon />
        </button>
      {/if}
    </div>
  </div>
  <div class="table-container">
    <table class="doc-table">
      <thead>
        <tr>
          <th>Document</th>
          <th>Uploaded by</th>
          <th>Uploaded at</th>
          <th class="right">Chunks</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#if c.documents.length === 0}
          <tr><td colspan="5" class="empty-cell">No documents found.</td></tr>
        {:else}
          {#each c.documents as doc (doc.source_uri)}
            <tr class="clickable-row" onclick={() => goto(`/admin/collections/${encodeURIComponent(c.id)}/documents/${encodeURIComponent(doc.source_uri)}`)}>
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
                <button class="replace-btn-icon" aria-label="Replace document" use:tooltip={"Replace"} onclick={(e) => { e.stopPropagation(); confirmingReplace = doc; }}><UploadIcon /></button>
                <button class="del-btn" aria-label="Delete document" use:tooltip={"Delete"} onclick={(e) => { e.stopPropagation(); confirmDeleteDoc = doc.source_uri; }}><BinIcon /></button>
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>

  <!-- ── Danger zone ────────────────────────────────────────────────────── -->
  {#if data.canManage}
    <div class="table-container danger-card">
      <div class="danger-row">
        <div>
          <p class="danger-title">Delete this collection</p>
          <p class="danger-desc">
            Permanently delete <strong>{c.id}</strong> and all its documents.
          </p>
        </div>
        <button class="danger-btn" onclick={() => (confirmDelete = true)}>Delete collection</button>
      </div>
    </div>
  {/if}
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
    <div class="owner-section">
      <span class="owner-section-label">Owner</span>
      <div class="owner-current">
        {#if ownerTenant}
          <span class="abbr-chip owner-chip">{ownerTenant.abbreviation}</span>
          <span class="access-name">{ownerTenant.name}</span>
        {:else}
          <span class="no-access">No owner set.</span>
        {/if}
      </div>
      {#if data.isAdmin}
        <div class="grant-row">
          <select class="grant-select" bind:value={selectedOwnerOrg}>
            <option value={null} disabled>Select new owner…</option>
            {#each reassignableOrgs as org}
              <option value={org.id}>{org.name} ({org.abbreviation})</option>
            {/each}
          </select>
          <button class="grant-btn" onclick={reassignOwner} disabled={reassigningOwner || !selectedOwnerOrg}>
            {reassigningOwner ? 'Reassigning…' : 'Reassign owner'}
          </button>
        </div>
      {/if}
    </div>

    <div class="access-section">
      <div class="access-section-header">
        <span class="owner-section-label">Access</span>
        {#if grantableOrgs.length > 0}
          <div class="org-search-wrapper" bind:this={orgSearchWrapperEl}>
            {#if orgSearchOpen}
              <div class="org-search-popover">
                <input
                  class="org-search-input"
                  type="text"
                  placeholder="Search organizations…"
                  bind:value={orgSearchQuery}
                />
                <div class="org-search-list">
                  {#if filteredGrantableOrgs.length === 0}
                    <p class="org-search-empty">No matching organizations.</p>
                  {:else}
                    {#each filteredGrantableOrgs as org (org.id)}
                      <button
                        class="org-search-item"
                        onclick={() => selectOrgForAccess(org)}
                        disabled={addingOrgId === org.id}
                      >
                        <span class="abbr-chip">{org.abbreviation}</span>
                        <span class="org-search-item-name">{org.name}</span>
                        {#if addingOrgId === org.id}<span class="org-search-item-status">Adding…</span>{/if}
                      </button>
                    {/each}
                  {/if}
                </div>
              </div>
            {/if}
            <button class="icon-btn" aria-label="Add access" use:tooltip={"Add access"} onclick={toggleOrgSearch}>
              <PlusLgIcon />
            </button>
          </div>
        {/if}
      </div>

      {#if accessTenants.length === 0}
        <p class="no-access">No tenants currently have access.</p>
      {:else}
        <table class="data-table">
          <thead>
            <tr>
              <th>Acronym</th>
              <th>Name</th>
              <th>Max. Permission</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each accessTenants as org}
              <tr>
                <td><span class="abbr-chip">{org.abbreviation}</span></td>
                <td class="name">{org.name}</td>
                <td>
                  <select
                    class="inline-select"
                    onchange={(e) => {
                      const raw = (e.currentTarget as HTMLSelectElement).value;
                      updateMaxClassification(org.id, Number(raw));
                    }}
                    disabled={updatingMaxClass[org.id]}
                  >
                    {#each CLASSIFICATION_OPTIONS as lvl}
                      <option value={lvl} selected={org.max_classification === lvl}>{CLASSIFICATION_LABELS[lvl]}</option>
                    {/each}
                  </select>
                </td>
                <td class="actions-cell">
                  <button
                    class="del-btn"
                    aria-label="Revoke access"
                    use:tooltip={"Revoke"}
                    onclick={() => revokeAccess(org.id)}
                    disabled={revokingId === org.id}
                  >
                    <BinIcon />
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
</Modal>

<svelte:window onclick={handleWindowClick} />

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

.title { font-size: var(--text-3xl); font-weight: 700; margin: 0; }

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  gap: 1rem;
}
.section-header-actions { display: flex; align-items: center; gap: 0.25rem; }

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
  padding: 0.75rem 1rem; border-bottom: 1px solid var(--color-neutral-200);
  text-align: left; vertical-align: middle;
}
.doc-table thead th {
  position: sticky; top: 0; background: var(--color-neutral-50); z-index: 2;
  font-weight: 600; color: var(--color-neutral-600);
  font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em;
  box-shadow: 0 1px 0 var(--color-neutral-200);
}
.doc-table tbody tr.clickable-row { cursor: pointer; transition: background 100ms ease; }
.doc-table tbody tr.clickable-row:hover { background: var(--color-neutral-100); }
.doc-table td.filename { font-weight: 500; word-break: break-all; }
.doc-table td.right, .doc-table th.right { text-align: right; }
.doc-table td.timestamp { color: var(--color-neutral-600); font-size: var(--text-xs); white-space: nowrap; }
.doc-table td.actions-cell { width: 5rem; text-align: right; display: flex; gap: 0.35rem; justify-content: flex-end; align-items: center; }
.empty-cell { text-align: center; padding: 2rem; color: var(--color-neutral-500); }

/* ── Access modal ────────────────────────────────────────────────────── */
.access-modal-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 22rem;
}

.owner-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.owner-section-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-neutral-500);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.owner-current { display: flex; align-items: center; gap: 0.5rem; }
.owner-chip { background: var(--color-blue-100); }

.access-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.access-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.org-search-wrapper {
  position: relative;
  display: inline-flex;
}

.org-search-popover {
  position: absolute;
  top: 50%;
  right: calc(100% + 0.5rem);
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  width: 16rem;
  padding: 0.6rem;
  background: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 20px rgba(0,0,0,0.12);
  z-index: 10;
}

.org-search-input {
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-neutral-50);
  color: var(--color-neutral-800);
}
.org-search-input:focus { outline: none; border-color: var(--color-blue-400); }

.org-search-list {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  max-height: 12rem;
  overflow-y: auto;
}

.org-search-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.4rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  text-align: left;
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-neutral-800);
}
.org-search-item:hover:not(:disabled) { background: var(--color-neutral-100); }
.org-search-item:disabled { opacity: 0.5; cursor: not-allowed; }

.org-search-item-name { flex: 1; }
.org-search-item-status { font-size: var(--text-xs); color: var(--color-neutral-400); }

.org-search-empty {
  font-size: var(--text-sm);
  color: var(--color-neutral-400);
  padding: 0.35rem 0.4rem;
  margin: 0;
}

.inline-select {
  box-sizing: border-box;
  width: 30%;
  max-width: 50%;
  padding: 0.25rem 0.5rem;
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-neutral-300);
  background: var(--color-white);
  color: var(--color-neutral-800);
  cursor: pointer;
}
.inline-select:focus { outline: none; border-color: var(--color-blue-500); }
.inline-select:disabled {
  background: var(--color-neutral-100);
  color: var(--color-neutral-400);
  cursor: not-allowed;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-100);
  text-align: left;
  vertical-align: middle;
  font-size: var(--text-sm);
}
.data-table thead th {
  font-weight: 600;
  color: var(--color-neutral-600);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: var(--color-neutral-50); }
.data-table td.name { font-weight: 500; }
.data-table td.actions-cell { width: 5rem; text-align: right; }

.access-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-neutral-700);
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
.danger-btn {
  background: var(--color-red-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.danger-btn:hover:not(:disabled) { background: var(--color-red-700); }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.danger-card {
  margin-top: 1rem;
  border: 1px solid var(--color-red-200);
}
.danger-card .section-title { margin-bottom: 0.75rem; }
.danger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.danger-title {
  font-weight: 600;
  color: var(--color-neutral-800);
  margin-bottom: 0.2rem;
}
.danger-desc {
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
  max-width: 40rem;
}

.replace-btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent; border: 1px solid var(--color-neutral-300); color: var(--color-neutral-600);
  padding: 0.35rem; border-radius: var(--radius-md); cursor: pointer;
}
.replace-btn-icon:hover { background: var(--color-neutral-100); }

.del-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent; border: 1px solid var(--color-red-300); color: var(--color-red-600);
  padding: 0.35rem; border-radius: var(--radius-md); cursor: pointer;
}
.del-btn:hover:not(:disabled) { background: var(--color-red-50); }
.del-btn:disabled { opacity: 0.5; cursor: not-allowed; }

</style>
