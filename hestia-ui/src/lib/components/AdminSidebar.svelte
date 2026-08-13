<script lang="ts">
  import { env } from '$env/dynamic/public';
  import { page } from '$app/stores';

  const currentVersion = env.PUBLIC_APP_VERSION;

  const adminNavGroups = [
    {
      label: 'Users & Authentication',
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
      label: 'System',
      items: [
        { label: 'Settings', href: '/admin/settings' },
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
}
</style>
