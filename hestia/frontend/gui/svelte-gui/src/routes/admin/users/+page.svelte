<script lang="ts">

    import { onMount } from 'svelte';

    onMount(() => {
    refreshUsers();
    });

    let users: any = [];
    let error: string | null = null;

    let loading = false;

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
</script>

<div class="page-container">
  <div class="admin-content">
    <h1 class="title">User Management</h1>
    <p class="subtitle">View and manage registered users.</p>

    {#if error}
      <div class="error-box">{error}</div>
    {/if}

    <div class="actions">
      <button class="refresh-btn" disabled={loading} onclick={refreshUsers}>
        {loading ? "Refreshing…" : "Refresh"}
      </button>
    </div>

    <div class="table-container">
      <table class="user-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Username</th>
            <th>Role</th>
            <th>Created</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>

        <tbody>
          {#each users as u}
            <tr>
              <td>{u.id}</td>
              <td>{u.username}</td>
              <td>{u.roles}</td>
              <td>{new Date(u.created_at * 1000).toLocaleString()}</td>

              <td class="actions">
                <button class="small-btn">Edit</button>
                <button class="small-btn danger">Delete</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
        <div class="actions">
            <a href="/admin/users/create" class="create-user-btn">+ Create User</a>
        </div>
    </div>
  </div>
</div>

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
    margin-bottom: .25rem;
  }

  .subtitle {
    color: var(--color-neutral-600);
    margin-bottom: 1.5rem;
  }

  .actions {
    margin-bottom: 1rem;
  }

  .refresh-btn {
    background: var(--color-blue-600);
    color: white;
    padding: .5rem 1rem;
    border-radius: var(--radius-lg);
    cursor: pointer;
    font-weight: 600;
  }

  .refresh-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .table-container {
    background: white;
    padding: calc(var(--spacing) * 4);
    border-radius: var(--radius-2xl);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  }

  .user-table {
    width: 100%;
    border-collapse: collapse;
  }

  .user-table th,
  .user-table td {
    padding: .75rem 1rem;
    border-bottom: 1px solid var(--color-neutral-200);
  }

  .actions {
    display: flex;
    gap: .5rem;
  }

  .small-btn {
    background: var(--color-neutral-200);
    padding: .35rem .75rem;
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