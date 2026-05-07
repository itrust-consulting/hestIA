<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import CreateUserModal from '$lib/components/modals/CreateUserModal.svelte';

    import PlusCircleIcon from '$lib/components/icons/plusCircleIcon.svelte';
    
    onMount(() => {
      refreshUsers();
    });


    let users: any = [];
    let error: string | null = null;

    let loading = false;
    let openModal: null | "create_user" = null;

    const formatDate = (ts: number) => {
      if (!ts) return 'Never';
      return new Date(ts).toLocaleString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    };

    function open(modal: "create_user") {
        openModal = modal;
    }

    function close() {
        openModal = null;
    }

    async function refreshUsers() {
        loading = true;
        error = null;

        try {
            const res = await fetch('/api/admin/users');
            if (!res.ok) throw new Error('Failed to load users');

            users = await res.json();
        } catch (e) {
            error = 'Could not load users.';
        }

        loading = false;
    }


  function goToUser(userId: string | number) {
    goto(`/admin/users/user/${userId}`);
  }


</script>

<div class="page-container">
  <div class="admin-content">
    <h1 class="title">User Management</h1>
    <p class="subtitle">View and manage registered users.</p>

    {#if error}
      <div class="error-box">{error}</div>
    {/if}

    <div class="table-container">
      <table class="user-table">
        <thead>
          <tr>
            <th>No.</th>
            <th>Username</th>
            <th>Email</th>
            <th>Name</th>
            <th>Expires</th>
          </tr>
        </thead>

        <tbody>
          {#each users as u, i}
            <tr class="clickable-row" onclick={() => goToUser(u.id)}>
              <td>{i + 1}</td>
              <td>{u.username}</td>
              <td>{u.email}</td>
              <td>{u.first_name} {u.last_name}</td>
              <td>{formatDate(u.expires_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      <div class="actions">
        <button class="action-btn" onclick={() => open("create_user")}>
            <PlusCircleIcon/>Create User
        </button>
      </div>
    </div>
  </div>
</div>

<CreateUserModal open={openModal === "create_user"} onClose={close} isAdmin={true}/>

<style>
.page-container {
  display: flex;
  height: 100vh;
  background: var(--color-neutral-100);
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-6xl);
  margin-inline: auto;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.subtitle {
  color: var(--color-neutral-600);
  margin-bottom: 1.5rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.action-btn {
  background: var(--color-blue-600);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-weight: 600;
  display: flex;
  flex-direction: row;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.table-container {
  background: white;
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed; 
}

/* Shared cell rules */
.user-table th,
.user-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-neutral-200);
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}

.user-table thead th {
  position: sticky;
  top: 0;
  background: white;
  z-index: 2;
  font-weight: 600;
  box-shadow: 0 1px 0 var(--color-neutral-200);
}

.user-table th:nth-child(1),
.user-table td:nth-child(1) {
  width: 4rem;
  text-align: right;
}

.user-table th:nth-child(2),
.user-table td:nth-child(2) {
  width: 16%;
}

.user-table th:nth-child(3),
.user-table td:nth-child(3) {
  width: 26%;
}

.user-table th:nth-child(4),
.user-table td:nth-child(4) {
  width: 22%;
}

.user-table th:nth-child(5),
.user-table td:nth-child(5) {
  width: 14rem;
}

.user-table tbody tr:hover {
  background: var(--color-neutral-100);
}

.small-btn {
  background: var(--color-neutral-200);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
}

.small-btn:hover {
  background: var(--color-neutral-300);
}

.small-btn.danger {
  background: var(--color-red-500);
  color: white;
}

.small-btn.danger:hover {
  background: var(--color-red-600);
}

.error-box {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: var(--radius-xl);
}
</style>