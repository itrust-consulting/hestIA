<script lang="ts">

  let error: string | null = null;

</script>

<div class="page-container">
  <div class="admin-content">

    {#if error}
      <div class="error-box">{error}</div>
    {/if}

    <!-- Admin Sections -->
    <div class="admin-grid">

      <!-- Users & Authentication -->
        <div class="admin-card">
            <h2 class="admin-card-header">Users & Authentication</h2>

            <div class="admin-list">
                <div class="admin-item" on:click={() => open('/admin/users')}>
                <span>User Management</span>
                <span class="chevron">›</span>
                </div>

                <div class="admin-item" on:click={() => open('/admin/roles')}>
                <span>Role Management</span>
                <span class="chevron">›</span>
                </div>

                <div class="admin-item" on:click={() => open('/admin/passwords')}>
                <span>Password Management</span>
                <span class="chevron">›</span>
                </div>
            </div>
        </div>
        <div class="admin-card">
            <div class="admin-card-header">Knowledge Base</div>
            <div class="admin-list">
                <div class="admin-item">
                    <span>Document Management</span>
                    <span class="chevron">›</span>
                </div>
            </div>
        </div>
        <div class="admin-card">
            <div class="admin-card-header">Agent Settings</div>
            <div class="admin-list">
                <div class="admin-item">
                    <span>ISMS</span>
                    <span class="chevron">›</span>
                </div>
                <div class="admin-item">
                    <span>Audit Assistant</span>
                    <span class="chevron">›</span>
                </div>
                <div class="admin-item">
                    <span>Asset Manager</span>
                    <span class="chevron">›</span>
                </div>
            </div>
        </div>
      <!-- System -->
      <div class="admin-card">
        <h2 class="admin-card-header">System</h2>

        <div class="admin-list">
            <div class="admin-item" on:click={() => open('/admin/system')}>
            <span>System Settings</span>
            <span class="chevron">›</span>
            </div>

            <div class="admin-item" on:click={() => open('/admin/database')}>
            <span>Database Management</span>
            <span class="chevron">›</span>
            </div>

            <div class="admin-item" on:click={() => open('/admin/llm')}>
            <span>LLM Configuration</span>
            <span class="chevron">›</span>
            </div>
        </div>
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
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  margin-inline: auto;
}

.admin-card-header {
  font-size: 1.25rem; /* 36px */
  font-weight: 700;
  color: var(--color-neutral-900);
  margin-bottom: 0.75rem;
}

/* ---------------------------
   SECTION CARDS
---------------------------- */
.admin-grid {
  display: grid;

  /* ✅ Never more than 3 columns */
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  grid-auto-flow: row;
  max-width: 100%;
  
  /* ✅ NEW: Limit to exactly 3 columns max */
  grid-template-columns: repeat(3, minmax(0, 1fr));

  /* spacing */
  gap: calc(var(--spacing) * 4);
  margin-bottom: calc(var(--spacing) * 6);
}
/* Card still provides section grouping */
.admin-card {
  background: white;
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  position: relative;
}


/* Items list container */
.admin-list {
  margin-top: calc(var(--spacing) * 2);
  border-top: 1px solid var(--color-neutral-200);
  border-bottom: 1px solid var(--color-neutral-200);
}

/* Each row, no background, only borders */
.admin-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  padding: .85rem 0;
  font-size: var(--text-base);
  font-weight: 500;

  border-bottom: 1px solid var(--color-neutral-200);
  cursor: pointer;

  transition: background 120ms ease, padding-left 120ms ease;
}

/* Remove last border */
.admin-item:last-child {
  border-bottom: none;
}

/* Hover effect: slight highlight + slide */
.admin-item:hover {
  background: var(--color-neutral-100);
  padding-left: .25rem;
}

.chevron {
  font-size: var(--text-lg);
  opacity: 0.5;
  transition: opacity 150ms ease;
}

.admin-item:hover .chevron {
  opacity: 0.9;
}
/* ---------------------------
   ERROR BOX
---------------------------- */
.error-box {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: var(--radius-xl);
  text-align: center;
}
</style>