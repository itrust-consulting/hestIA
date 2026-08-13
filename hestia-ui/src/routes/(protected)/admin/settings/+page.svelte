<div class="admin-content">
  <h1 class="title">Settings</h1>
  <p class="subtitle">System-wide configuration.</p>

  <div class="table-container">
    <div class="empty-state">No settings configured yet.</div>
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
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--color-neutral-500);
}
</style>
