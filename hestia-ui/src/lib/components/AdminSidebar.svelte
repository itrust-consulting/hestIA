<script lang="ts">
  import { env } from '$env/dynamic/public';
  import { page } from '$app/stores';
  import ItrustIcon from './icons/itrustIcon.svelte';

  const currentVersion = env.PUBLIC_APP_VERSION;

  const adminNavGroups = [
    {
      label: 'Identity & Access',
      items: [
        { label: 'Users',    href: '/admin/users'   },
        { label: 'Roles',    href: '/admin/roles'   },
        { label: 'Tenants',  href: '/admin/tenants' },
      ]
    },
    {
      label: 'Knowledge Base',
      items: [
        { label: 'Collections', href: '/admin/collections' },
      ]
    },
    {
      label: 'Settings',
      items: [
        { label: 'Connections', href: '/admin/settings/connections' },
        { label: 'Workflows', href: '/admin/settings/workflows' },
        { label: 'Authentication', href: '/admin/settings/authentication' },
        { label: 'Logging', href: '/admin/settings/logging' },
        { label: 'Notifications', href: '/admin/settings/notifications' },
      ]
    },
  ];

  const moderatorNavGroups = [
    {
      label: 'Dashboard',
      items: [
        { label: 'Tenants', href: '/admin/tenants' },
        { label: 'Collections', href: '/admin/collections' },
      ]
    },
  ];

  $: navGroups = $page.data.isAdmin ? adminNavGroups : moderatorNavGroups;

  function isActive(href: string): boolean {
    return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
  }
</script>

<aside class="sidebar">
  <div class="sidebar-list">
    {#each navGroups as group}
      <h2>{group.label}</h2>
      {#each group.items as item}
        <a
          href={item.href}
          class="sidebar-item"
          class:active={isActive(item.href)}
        >
          {item.label}
        </a>
      {/each}
    {/each}
  </div>

  <div class="sidebar-footer">
    <span class="powered-by">Powered by</span>
    <div class="logo-wrapper">
      <ItrustIcon />
    </div>
    <span class="version">{currentVersion}</span>
  </div>
</aside>

<style>
.sidebar {
  position: sticky;
  top: var(--header-height);
  height: calc(100vh - var(--header-height));
  width: var(--sidebar-width);
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid var(--color-neutral-200);
  background: var(--color-neutral-200);
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.sidebar h2 {
  font-size: var(--text-md);
  font-weight: 600;
  padding-bottom: 0.25rem;
  margin-top: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-400);
}

.sidebar-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: 2.25rem;
  padding: 0 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
  text-decoration: none;
  transition: background-color 120ms ease, color 120ms ease;
}

.sidebar-item:hover {
  background: var(--color-white);
  color: var(--color-neutral-900);
}

.sidebar-item.active {
  background: var(--color-white);
  color: var(--color-neutral-900);
  box-shadow: inset 3px 0 0 var(--color-blue-600);
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 1rem;
  padding-bottom: 0.5rem;
  text-align: center;
  color: var(--color-neutral-500);
  font-size: var(--text-xs);
  user-select: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.powered-by {
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-neutral-400);
}

.logo-wrapper :global(svg) {
  width: 5em;
  filter: grayscale(1);
  opacity: 0.55;
  transition: opacity 150ms ease;
}

:global(.dark) .logo-wrapper :global(svg) {
  filter: grayscale(1) invert(1);
}

.logo-wrapper:hover :global(svg) {
  opacity: 0.85;
}
</style>
