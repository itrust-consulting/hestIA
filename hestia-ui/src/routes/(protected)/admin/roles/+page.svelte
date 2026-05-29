<script lang="ts">
  const { data } = $props();
  type Role = { id: number; name: string; description?: string };
  const roles: Role[] = $derived(data.roles ?? []);
</script>

<div class="admin-content">
  <h1 class="title">Role Management</h1>
  <p class="subtitle">View the roles defined in the system.</p>

  <div class="table-container">
    {#if roles.length === 0}
      <div class="empty-state">No roles found.</div>
    {:else}
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            {#if roles.some(r => r.description)}
              <th>Description</th>
            {/if}
          </tr>
        </thead>
        <tbody>
          {#each roles as role}
            <tr>
              <td>{role.id}</td>
              <td>{role.name}</td>
              {#if roles.some(r => r.description)}
                <td>{role.description ?? '—'}</td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

<style>
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
  margin-bottom: 0;
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
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-600);
  box-shadow: 0 1px 0 var(--color-neutral-200);
}

.data-table tbody tr:hover { background: var(--color-neutral-50); }

.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--color-neutral-500);
}


</style>
