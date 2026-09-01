<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import CreateUserModal from '$lib/components/modals/CreateUserModal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';

  const { data } = $props();

  let openModal = $state<null | 'create_user'>(null);

  const formatDate = (ts: number) => {
    if (!ts) return 'Never';
    return new Date(ts).toLocaleString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric'
    });
  };

  function open(modal: 'create_user') { openModal = modal; }
  function close() { openModal = null; }

  function goToUser(userId: string | number) {
    goto(`/admin/users/${userId}`);
  }

  let confirmDelete = $state<{ id: string; username: string } | null>(null);

  async function deleteUser() {
    const res = await fetch(`/api/admin/users/user/${confirmDelete!.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete user.');
    await invalidateAll();
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="title">User Management</h1>
  </div>
  <div class="subtitle-row">
    <p class="subtitle">View and manage registered users.</p>
    <button class="icon-btn" title="Add user" onclick={() => open('create_user')}>
      <PlusLgIcon />
    </button>
  </div>

  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>No.</th>
          <th>Username</th>
          <th>Email</th>
          <th>Name</th>
          <th>Status</th>
          <th>Expires</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#if data.users.length === 0}
          <tr><td colspan="6" class="loading-cell">No users found.</td></tr>
        {:else}
          {#each data.users as u, i}
            <tr class="clickable-row" onclick={() => goToUser(u.id)}>
              <td>{i + 1}</td>
              <td>{u.username}</td>
              <td>{u.email}</td>
              <td>{u.first_name} {u.last_name}</td>
              <td>
                <span class="status-dot" class:status-dot--online={u.is_online}></span>
                {#if u.is_online}
                  Online
                {:else}
                  <span class="muted">Last active: {formatDate(u.last_seen_at)}</span>
                {/if}
              </td>
              <td>{formatDate(u.expires_at)}</td>
              <td class="actions-cell">
                <button class="del-btn" aria-label="Delete user" title="Delete" onclick={(e) => { e.stopPropagation();
                  confirmDelete = u; }}><BinIcon /></button>
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
</div>

<CreateUserModal
  open={openModal === 'create_user'}
  onClose={close}
  onSuccess={() => invalidateAll()}
  isAdmin={true}
/>

<ConfirmDeleteModal
  open={confirmDelete !== null}
  title="Delete User"
  onClose={() => (confirmDelete = null)}
  onConfirm={deleteUser}
  successMessage="User deleted."
>
  <p>Permanently delete <strong>{confirmDelete?.username}</strong>?</p>
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
  margin-bottom: 0.25rem;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 0.25rem;
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

.muted { color: var(--color-gray-700); font-size: var(--text-sm); }
td.actions-cell { width: 5rem; text-align: right; }

.status-dot {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--color-neutral-300);
  margin-right: 0.4rem;
}
.status-dot--online { background: var(--color-green-600); }

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
</style>
