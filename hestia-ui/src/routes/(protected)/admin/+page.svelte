<script lang="ts">
  import { goto } from '$app/navigation';
  const { data } = $props();
</script>

<div class="admin-content">

  <div class="stats-row">
    {#if data.isAdmin}
      <button class="stat-card" onclick={() => goto('/admin/users')}>
        <span class="stat-label">Total users</span>
        <span class="stat-value">{data.userCount ?? '—'}</span>
      </button>
      <button class="stat-card" onclick={() => goto('/admin/tenants')}>
        <span class="stat-label">Tenants</span>
        <span class="stat-value">{data.tenantCount ?? '—'}</span>
      </button>
      <button class="stat-card" onclick={() => goto('/admin/collections')}>
        <span class="stat-label">Collections</span>
        <span class="stat-value">{data.collectionCount ?? '—'}</span>
      </button>
    {:else}
      <button class="stat-card" onclick={() => goto('/admin/tenants')}>
        <span class="stat-label">Members</span>
        <span class="stat-value">{data.totalMembers}</span>
      </button>
      <button class="stat-card" onclick={() => goto('/admin/collections')}>
        <span class="stat-label">Owned collections</span>
        <span class="stat-value">{data.totalOwned}</span>
      </button>
      <button class="stat-card" onclick={() => goto('/admin/collections')}>
        <span class="stat-label">Accessible collections</span>
        <span class="stat-value">{data.totalAccess}</span>
      </button>
    {/if}
  </div>

  <div class="admin-grid">
    {#if data.isAdmin}
      <div class="admin-card">
        <h2 class="admin-card-header">Users & Authentication</h2>
        <div class="admin-list">
          <div class="admin-item" onclick={() => goto('/admin/users')}>
            <span>User Management</span><span class="chevron">›</span>
          </div>
          <div class="admin-item" onclick={() => goto('/admin/roles')}>
            <span>Role Management</span><span class="chevron">›</span>
          </div>
          <div class="admin-item" onclick={() => goto('/admin/tenants')}>
            <span>Tenant Management</span><span class="chevron">›</span>
          </div>
        </div>
      </div>
      <div class="admin-card">
        <h2 class="admin-card-header">Knowledge Base</h2>
        <div class="admin-list">
          <div class="admin-item" onclick={() => goto('/admin/collections')}>
            <span>Collections</span><span class="chevron">›</span>
          </div>
        </div>
      </div>
      <div class="admin-card">
        <h2 class="admin-card-header">System</h2>
        <div class="admin-list">
          <div class="admin-item" onclick={() => goto('/admin/settings')}>
            <span>Settings</span><span class="chevron">›</span>
          </div>
        </div>
      </div>
    {:else}
      <div class="admin-card">
        <h2 class="admin-card-header">My Tenants</h2>
        <div class="admin-list">
          {#each data.myOrgs as org (org.id)}
            <div class="admin-item" onclick={() => goto(`/admin/tenants/${org.id}`)}>
              <div class="item-body">
                <span class="item-name">{org.name}</span>
                <span class="item-meta">
                  <span class="abbr-chip">{org.abbr}</span>
                  {org.memberCount} member{org.memberCount !== 1 ? 's' : ''}
                </span>
              </div>
              <span class="chevron">›</span>
            </div>
          {/each}
        </div>
      </div>
      <div class="admin-card">
        <h2 class="admin-card-header">Knowledge Base</h2>
        <div class="admin-list">
          <div class="admin-item" onclick={() => goto('/admin/collections')}>
            <span>Collections</span><span class="chevron">›</span>
          </div>
        </div>
      </div>
    {/if}
  </div>

</div>

<style>
.admin-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-6xl);
  margin-inline: auto;
}

/* ── Stat cards ──────────────────────────────────────────────────────── */
.stats-row {
  display: flex;
  gap: 1rem;
  margin-bottom: calc(var(--spacing) * 6);
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  background: var(--color-neutral-50);
  padding: 1.25rem 1.75rem;
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  min-width: 140px;
  border: 1px solid transparent;
  cursor: pointer;
  text-align: left;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}
.stat-card:hover {
  border-color: var(--color-blue-200);
  box-shadow: 0 4px 20px rgba(0,0,0,0.10);
}

.stat-label {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-neutral-500);
}
.stat-value {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--color-neutral-900);
  line-height: 1.1;
}

/* ── Nav cards ───────────────────────────────────────────────────────── */
.admin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  max-width: 720px;
  gap: calc(var(--spacing) * 4);
}

.admin-card {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.admin-card-header {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-neutral-500);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.admin-list {
  border-top: 1px solid var(--color-neutral-200);
}

.admin-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 0;
  font-size: var(--text-base);
  font-weight: 500;
  border-bottom: 1px solid var(--color-neutral-200);
  cursor: pointer;
  transition: padding-left 120ms ease;
}
.admin-item:last-child { border-bottom: none; }
.admin-item:hover { padding-left: 0.25rem; }
.admin-item:hover .chevron { opacity: 0.9; }

.chevron {
  font-size: var(--text-lg);
  opacity: 0.4;
  transition: opacity 150ms ease;
  flex-shrink: 0;
}

/* ── Moderator tenant item ───────────────────────────────────────────── */
.item-body {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.item-name { color: var(--color-neutral-800); }
.item-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--color-neutral-500);
}

.abbr-chip {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.03em;
}
</style>
