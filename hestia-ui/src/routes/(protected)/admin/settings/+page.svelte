<script lang="ts">
  import { goto } from '$app/navigation';

  const sections = [
    {
      label: 'Connections',
      description: 'Manage Ollama, OpenAI, and Qdrant backends for generation, embedding, reranking, and vector storage.',
      href: '/admin/settings/connections',
    },
    {
      label: 'Workflows',
      description: 'Configure the node sequence used to handle each request type — Encode, Retrieve, Augment, Generate, Chat.',
      href: '/admin/settings/workflows',
    },
    {
      label: 'Authentication',
      description: 'Set the password policy and configure OIDC and LDAP sign-in.',
      href: '/admin/settings/authentication',
    },
    {
      label: 'Logging',
      description: 'Configure log retention and export, and inspect application logs.',
      href: '/admin/settings/logging',
    },
  ];
</script>

<div class="admin-content">
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="title">Settings</h1>
      <p class="subtitle">Configure how Hestia connects, processes requests, authenticates users, and logs activity.</p>
    </div>
  </div>

  <div class="settings-grid">
    {#each sections as s (s.href)}
      <button class="settings-card" onclick={() => goto(s.href)}>
        <div class="settings-card-body">
          <span class="settings-card-title">{s.label}</span>
          <span class="settings-card-desc">{s.description}</span>
        </div>
        <span class="chevron">›</span>
      </button>
    {/each}
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

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.page-header-left { flex: 1; }

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.subtitle {
  color: var(--color-neutral-600);
  margin-bottom: 0;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: calc(var(--spacing) * 4);
}

.settings-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  border: 1px solid transparent;
  cursor: pointer;
  text-align: left;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}
.settings-card:hover {
  border-color: var(--color-blue-200);
  box-shadow: 0 4px 20px rgba(0,0,0,0.10);
}
.settings-card:hover .chevron { opacity: 0.9; }

.settings-card-body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.settings-card-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-neutral-900);
}

.settings-card-desc {
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
}

.chevron {
  font-size: var(--text-lg);
  opacity: 0.4;
  transition: opacity 150ms ease;
  flex-shrink: 0;
}
</style>
