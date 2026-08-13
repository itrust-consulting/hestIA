<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import CreateUserModal from '$lib/components/modals/CreateUserModal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';

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
    goto(`/admin/users/user/${userId}`);
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
    <div class="page-header-left">
      <h1 class="title">User Management</h1>
    </div>
    <div class="page-header-right">
      <button class="action-btn" onclick={() => open('create_user')}>
        Add User
      </button>
    </div>
  </div>
  <p class="subtitle">View and manage registered users.</p>

  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>No.</th>
          <th>Username</th>
          <th>Email</th>
          <th>Name</th>
          <th>Expires</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#if data.users.length === 0}
          <tr><td colspan="5" class="loading-cell">No users found.</td></tr>
        {:else}
          {#each data.users as u, i}
            <tr class="clickable-row" onclick={() => goToUser(u.id)}>
              <td>{i + 1}</td>
              <td>{u.username}</td>
              <td>{u.email}</td>
              <td>{u.first_name} {u.last_name}</td>
              <td>{formatDate(u.expires_at)}</td>
              <td>
                <button class="edit-btn" onclick={(e) => { e.stopPropagation();
                  goto(`/admin/users/user/${u.id}`); }}>Edit</button>
                <button class="del-btn" onclick={(e) => { e.stopPropagation();
                  confirmDelete = u; }}>Delete</button>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
  gap: 1rem;
}
.page-header-left { flex: 1; }
.page-header-right { display: flex; gap: 0.5rem; align-items: center; }


.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.subtitle {
  color: var(--color-neutral-600);
  margin-bottom: 1.5rem;
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
  box-shadow: 0 1px 0 var(--color-neutral-200);
}
.clickable-row { cursor: pointer; transition: background 100ms ease; }
.clickable-row:hover { background: var(--color-gray-700); }

td.num { width: 4rem; text-align: right; color: var(--color-neutral-400); }
td.name { font-weight: 500; }
td.muted { color: var(--color-neutral-500); font-size: var(--text-sm); }
td.actions-cell { width: 10rem; text-align: right; display: flex; gap: 0.4rem; justify-content: flex-end; align-items: center; }

td.members-cell { width: 6rem; }
.no-members { color: var(--color-neutral-400); }


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
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
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
.del-btn:hover { background: var(--color-red-50); }

.loading-cell {
  text-align: center;
  padding: 2rem;
  color: var(--color-neutral-500);
}
</style>
