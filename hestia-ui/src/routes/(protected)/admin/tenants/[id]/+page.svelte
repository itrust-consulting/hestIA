<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { untrack } from 'svelte';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import CreateCollectionModal from '$lib/components/modals/CreateCollectionModal.svelte';
  import type { Collection } from '$lib/types';
  import type { PageData } from './$types';
  import { addToast } from '$lib/stores/toast';

  const { data }: { data: PageData } = $props();

  type Member = { id: string; username: string; email: string; first_name: string; last_name: string; classification_level: number; tenant_role: string | null };

  let tenant = $derived(data.tenant);
  let members: Member[] = $derived(data.members);
  let allUsers: any[] = $derived(data.allUsers);

  const memberIds = $derived(new Set(members.map((m) => m.id)));
  const availableUsers = $derived(allUsers.filter((u: any) => !memberIds.has(u.id)));

  const formatDate = (ts: number) =>
    ts ? new Date(ts).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

  // ── Details edit ─────────────────────────────────────────────────────────
  let editing = $state(untrack(() => data.editMode) ?? false);
  let editName = $state('');
  let editAbbr = $state('');
  let editSaving = $state(false);

  $effect(() => {
    editName = tenant.name;
    editAbbr = tenant.abbreviation;
  });

  function startEdit() {
    editName = tenant.name;
    editAbbr = tenant.abbreviation;
    editing = true;
  }

  function cancelEdit() {
    editing = false;
  }

  async function handleSave() {
    if (!editName.trim() || !editAbbr.trim()) return;
    editSaving = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: editName.trim(), abbreviation: editAbbr.trim() }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      editing = false;
      addToast('Tenant updated.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to update tenant.', 'error');
    } finally {
      editSaving = false;
    }
  }

  // ── Delete tenant ─────────────────────────────────────────────────────────
  let confirmDeleteOpen = $state(false);

  async function deleteTenant() {
    const res = await fetch(`/api/admin/tenants/${tenant.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete tenant.');
    goto('/admin/tenants');
  }

  // ── Remove member ─────────────────────────────────────────────────────────
  let confirmRemoveMember: Member | null = $state(null);

  async function handleRemoveMember() {
    const res = await fetch(`/api/admin/tenants/${tenant.id}/members/${confirmRemoveMember!.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to remove member.');
    await invalidateAll();
  }
  
  // ── Delete Collection ──────────────────────────────────────────────────────
  let confirmDeleteCol = $state<string | null>(null);

  async function handleDeleteCollection() {
    const [tenantRes, qdrantRes] = await Promise.all([
      fetch(`/api/admin/tenants/${tenant.id}/collections/${encodeURIComponent(confirmDeleteCol!)}`, { method: 'DELETE' }),
      fetch(`/api/admin/collections/${encodeURIComponent(confirmDeleteCol!)}`, { method: 'DELETE' }),
    ]);
    if (!tenantRes.ok || !qdrantRes.ok) throw new Error('Failed to delete collection.');
    await invalidateAll();
  }

  // ── Add member ────────────────────────────────────────────────────────────
  let addOpen = $state(false);
  let selectedUserId = $state('');
  let adding = $state(false);

  function openAdd() {
    selectedUserId = availableUsers[0]?.id ?? '';
    addOpen = true;
  }

  async function handleAdd() {
    if (!selectedUserId) return;
    adding = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/members`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ user_id: selectedUserId }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Member added.', 'success');
      addOpen = false;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to add member.', 'error');
    } finally {
      adding = false;
    }
  }

  // ── Member classification / role ──────────────────────────────────────────
  let savingMember = $state<Record<string, boolean>>({});

  async function setClassification(memberId: string, level: number) {
    savingMember = { ...savingMember, [memberId]: true };
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/members/${memberId}/classification`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ level }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to update classification.', 'error');
    } finally {
      savingMember = { ...savingMember, [memberId]: false };
    }
  }

  async function setTenantRole(memberId: string, role: string | null) {
    savingMember = { ...savingMember, [memberId]: true };
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/members/${memberId}/role`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to update role.', 'error');
    } finally {
      savingMember = { ...savingMember, [memberId]: false };
    }
  }

  // ── Collections ───────────────────────────────────────────────────────────
  let ownedCollections: Collection[] = $state(data.ownedCollections ?? []);
  let accessibleCollections: Collection[] = $state(data.accessibleCollections ?? []);
  $effect(() => { ownedCollections = data.ownedCollections ?? []; });
  $effect(() => { accessibleCollections = data.accessibleCollections ?? []; });

 

  let uploadOpen = $state(false);

  const uploadOrganizations = $derived(data.uploadOrganizations ?? []);

  function handleCreateSuccess(collectionName: string) {
    goto(`/admin/collections/${encodeURIComponent(collectionName)}`);
  }

</script>

<div class="admin-content">
  <!-- ── Header ─────────────────────────────────────────────────────────── -->
  <div class="page-header">
    <div class="page-header-left">
      <div class="avatar">{tenant.name?.charAt(0).toUpperCase()}</div>
      <div>
        <div class="title-row">
          <h1 class="title">{tenant.name}</h1>
          <span class="abbr-chip">{tenant.abbreviation}</span>
        </div>
        <span class="meta">Created {formatDate(tenant.created_at)}</span>
      </div>
    </div>
    {#if data.isAdmin}
      <div class="danger-zone">
        <button class="btn-danger" onclick={() => (confirmDeleteOpen = true)}>Delete Tenant</button>
      </div>
    {/if}
  </div>

  <!-- ── Details card ───────────────────────────────────────────────────── -->
  <section class="card">
    <h2 class="section-title">Details</h2>

    {#if editing}
      <div class="form-grid">
        <label class="field">
          <span>Name</span>
          <input type="text" bind:value={editName} />
        </label>
        <label class="field">
          <span>Abbreviation</span>
          <input type="text" bind:value={editAbbr} />
        </label>
      </div>
      <div class="card-footer">
        <button class="btn-secondary" onclick={cancelEdit} disabled={editSaving}>Cancel</button>
        <button class="btn-primary" onclick={handleSave}
          disabled={editSaving || !editName.trim() || !editAbbr.trim()}>
          {editSaving ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    {:else}
      <dl class="info-grid">
        <div class="info-row">
          <dt>Name</dt>
          <dd>{tenant.name}</dd>
        </div>
        <div class="info-row">
          <dt>Abbreviation</dt>
          <dd><span class="abbr-chip">{tenant.abbreviation}</span></dd>
        </div>
        <div class="info-row">
          <dt>Created</dt>
          <dd>{formatDate(tenant.created_at)}</dd>
        </div>
      </dl>
      {#if data.isAdmin}
        <div class="card-footer">
          <button class="btn-secondary" onclick={startEdit}>Edit</button>
        </div>
      {/if}
    {/if}
  </section>

  <!-- ── Members card ───────────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Members</h2>
      <button class="action-btn" onclick={openAdd} disabled={availableUsers.length === 0}>
        Add Member
      </button>
    </div>

    {#if members.length === 0}
      <p class="empty-note">No members yet.</p>
    {:else}
      <table class="data-table">
        <thead>
          <tr>
            <th>No.</th>
            <th>Username</th>
            <th>Name</th>
            <th>Email</th>
            <th>Classification</th>
            <th>Role</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each members as m, i}
            <tr onclick={() => goto(`/admin/users/user/${m.id}`)} class="clickable">
              <td class="num">{i + 1}</td>
              <td class="name">{m.username}</td>
              <td>{m.first_name} {m.last_name}</td>
              <td class="muted">{m.email}</td>
              <td onclick={(e) => e.stopPropagation()}>
                <select class="inline-select" value={m.classification_level}
                  onchange={(e) => setClassification(m.id, Number((e.currentTarget as HTMLSelectElement).value))}
                  disabled={savingMember[m.id]}>
                  <option value={0}>Public</option>
                  <option value={1}>Internal</option>
                  <option value={2}>Confidential</option>
                  <option value={3}>Restricted</option>
                  <option value={4}>Secret</option>
                </select>
              </td>
              <td onclick={(e) => e.stopPropagation()}>
                <select class="inline-select" value={m.tenant_role ?? ''}
                  onchange={(e) => setTenantRole(m.id, (e.currentTarget as HTMLSelectElement).value || null)}
                  disabled={savingMember[m.id]}>
                  <option value="">Member</option>
                  <option value="co-moderator">Co-moderator</option>
                  <option value="moderator">Moderator</option>
                </select>
              </td>
              <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
                <button class="edit-btn" onclick={() => goto(`/admin/users/user/${m.id}`)}>Edit</button>
                <button class="del-btn" onclick={() => (confirmRemoveMember = m)}>Remove</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <!-- ── Collections cards ──────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Collections</h2>
      <div class="col-header-actions">
        <button class="action-btn" onclick={() => (uploadOpen = true)}>Add collection</button>

      </div>
    </div>
    {#if ownedCollections.length === 0}
      <p class="empty-note">No collections created.</p>
    {:else}
      <table class="data-table col-table">
        <thead>
          <tr>
            <th>Collection</th>
            <th>Owner</th>
            <th>Docs</th>
            <th>Status</th>
            <th>Access Granted</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each ownedCollections as col}
            <tr class="clickable-row" onclick={() => goto(`/admin/collections/${encodeURIComponent(col.id)}`)}>
              <td class="name">{col.id}</td>
              <td class="muted">
                  <span class="abbr-chip-sm">{tenant.name}</span>
              </td>
              <td class="muted">{col.documentCount}</td>
              <td><span class="status-dot" class:green={col.status === 'green'}></span></td>
              <td class="muted">
                {#if col.access.length > 0}
                  {col.access.map(a => a.abbreviation).join(', ')}
                {:else}
                  <span class="no-access">No external access</span>
                {/if}
              </td>
              {#if data.isAdmin}
                <td class="actions-cell">
                  <button class="del-btn" onclick={(e) => { e.stopPropagation(); confirmDeleteCol = col.id; }}>Delete</button>
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Accessible Collections</h2>
    </div>

    {#if accessibleCollections.length === 0}
      <p class="empty-note">No collections assigned to this tenant.</p>
    {:else}
      <table class="data-table col-table">
        <thead>
          <tr>
            <th>Collection</th>
            <th>Owner</th>
            <th>Docs</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {#each accessibleCollections as col}
            <tr>
              <td class="name">{col.id}</td>
              <td class="muted">
                {#if col.ownerTenant}
                  <span class="abbr-chip-sm">{col.ownerTenant.name}</span>
                {:else}
                  <span class="no-access">No owner assigned</span>
                {/if}
              </td>
              <td class="muted">{col.documentCount}</td>
              <td><span class="status-dot" class:green={col.status === 'green'}></span></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
</div>

<!-- ── Add member modal ───────────────────────────────────────────────────── -->
<Modal title="Add Member" open={addOpen} onClose={() => (addOpen = false)}>
  <div class="form-stack">
    {#if availableUsers.length === 0}
      <p class="muted-note">All users are already members of this tenant.</p>
    {:else}
      <label class="field">
        <span>Select user</span>
        <select bind:value={selectedUserId}>
          {#each availableUsers as u}
            <option value={u.id}>{u.username} — {u.first_name} {u.last_name}</option>
          {/each}
        </select>
      </label>
    {/if}
  </div>
  <svelte:fragment slot="footer">
    <button class="btn-primary" onclick={handleAdd}
      disabled={adding || !selectedUserId || availableUsers.length === 0}>
      {adding ? 'Adding…' : 'Add'}
    </button>
  </svelte:fragment>
</Modal>

<!-- ── Create Collection modal ────────────────────────────────────────────── -->
<CreateCollectionModal
  open={uploadOpen}
  onClose={() => (uploadOpen = false)}
  ownerOrgs={uploadOrganizations}
  accessOrgs={uploadOrganizations}
  defaultOwner={tenant.abbreviation}
  onSuccess={handleCreateSuccess}
/>

<ConfirmDeleteModal
  open={confirmDeleteOpen}
  title="Delete Tenant"
  onClose={() => (confirmDeleteOpen = false)}
  onConfirm={deleteTenant}
  successMessage="Tenant deleted."
>
  <p>Permanently delete <strong>{tenant.name}</strong>?</p>
  <p> This cannot be undone.</p>
</ConfirmDeleteModal>

<ConfirmDeleteModal
  open={confirmRemoveMember !== null}
  title="Remove Member"
  onClose={() => (confirmRemoveMember = null)}
  onConfirm={handleRemoveMember}
  confirmLabel="Remove"
  successMessage="Member removed."
>
  <p>Remove <strong>{confirmRemoveMember?.username}</strong> from <strong>{tenant.name}</strong>?</p>
  <p>The user account will not be deleted.</p>
</ConfirmDeleteModal>

<ConfirmDeleteModal
  open={confirmDeleteCol !== null}
  title="Delete Collection"
  onClose={() => (confirmDeleteCol = null)}
  onConfirm={handleDeleteCollection}
  successMessage="Collection deleted."
>
  <p>Permanently delete <strong>{confirmDeleteCol}</strong> and all its documents?</p>
  <p>This cannot be undone.</p>
</ConfirmDeleteModal>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-4xl);
  margin-inline: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.avatar {
  width: 52px; height: 52px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-blue-600) 80%, transparent);
  color: white;
  font-size: var(--text-2xl);
  font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.title-row {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.title { font-size: var(--text-2xl); font-weight: 700; margin-bottom: 0.15rem; }
.meta { font-size: var(--text-sm); color: var(--color-neutral-500); }

.danger-zone { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }

.card {
  background: var(--color-neutral-50);
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.section-title {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-neutral-800);
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.section-header .section-title { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }

.card-footer {
  margin-top: 1.25rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.info-grid { display: flex; flex-direction: column; gap: 0; }
.info-row {
  display: grid;
  grid-template-columns: 10rem 1fr;
  align-items: baseline;
  gap: 1rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--color-neutral-100);
}
.info-row:last-child { border-bottom: none; }
.info-row dt { font-size: var(--text-sm); font-weight: 600; color: var(--color-neutral-500); }
.info-row dd { font-size: var(--text-sm); color: var(--color-neutral-800); }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.875rem 1.25rem;
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
.field select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
}
.field select:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
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
.data-table tbody tr.clickable { cursor: pointer; }

td.num { width: 3.5rem; text-align: right; color: var(--color-neutral-400); }
td.name { font-weight: 500; }
td.muted { color: var(--color-neutral-500); }
td.actions-cell { width: 9rem; text-align: right; display: flex; gap: 0.4rem; justify-content: flex-end; align-items: center; }
.clickable-row { cursor: pointer; }


.empty-note {
  color: var(--color-neutral-500);
  font-size: var(--text-sm);
  padding: 1rem 0;
}

.inline-select {
  padding: 0.2rem 0.4rem;
  font-size: var(--text-xs);
  border-radius: var(--radius-sm);
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

.col-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.add-col-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.col-table td { font-size: var(--text-sm); }
.col-table td.name { font-weight: 500; }
.no-access { color: var(--color-neutral-400); font-style: italic; font-size: var(--text-xs); }

.status-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--color-neutral-400);
}
.status-dot.green { background: var(--color-green-500); }

.abbr-chip-sm {
  display: inline-block;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
}


.btn-primary {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: var(--color-neutral-100); color: var(--color-neutral-800);
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-size: var(--text-sm); font-weight: 500; border: 1px solid var(--color-neutral-300); cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { background: var(--color-neutral-200); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-danger {
  background: var(--color-red-600); color: white;
  padding: 0.4rem 0.9rem; border-radius: var(--radius-md);
  font-size: var(--text-sm); font-weight: 500; border: none; cursor: pointer;
}
.btn-danger:hover:not(:disabled) { background: var(--color-red-700); }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.edit-btn {
  background: transparent;
  border: 1px solid var(--color-neutral-300);
  color: var(--color-neutral-700);
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-xs);
}
.edit-btn:hover { background: var(--color-neutral-100); }

.del-btn {
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-xs);
}
.del-btn:hover { background: var(--color-red-50); }

.form-stack { display: flex; flex-direction: column; gap: 0.875rem; }
.muted-note { color: var(--color-neutral-500); font-size: var(--text-sm); }
</style>
