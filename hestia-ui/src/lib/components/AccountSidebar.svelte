<script lang="ts">
  import UserIcon from '$lib/components/icons/userIcon.svelte';
  import LockIcon from './icons/lockIcon.svelte';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import HelpIcon from '$lib/components/icons/helpIcon.svelte';
  import LogoutIcon from '$lib/components/icons/logoutIcon.svelte';
  import OrgIcon from '$lib/components/icons/orgIcon.svelte';

  import { version as currentVersion } from '$app/environment';

  export let currentSection: string = "profile";

  const sections = [
    { id: "profile",   label: "Profile",   icon: UserIcon,   href: "/account/overview?section=profile" },
    { id: "security",  label: "Security",  icon: LockIcon,   href: "/account/overview?section=security" },
    { id: "tenants",   label: "Tenants",   icon: OrgIcon,    href: "/account/overview?section=tenants" },
    { id: "support",   label: "Support",   icon: HelpIcon,   href: "/account/overview?section=support" },
    { id: "logout",    label: "Logout",    icon: LogoutIcon, href: "/api/logout", danger: true, noPreload: true },
  ];
</script>

<aside class="sidebar">

  <!-- Navigation -->
  <div class="sidebar-list">

    {#each sections as s}
      <a
        href={s.href}
        class="sidebar-item"
        class:active={currentSection === s.id}
        class:danger={s.danger}
        data-sveltekit-preload-data={s.noPreload ? 'off' : 'hover'}
      >
        <div class="icon-wrapper">
          <s.icon />
        </div>
        <span class="sidebar-label">{s.label}</span>
      </a>
    {/each}
  </div>

  <!-- Footer -->
  <div class="sidebar-footer">
    <span class="version">{currentVersion}</span>
  </div>

</aside>

<style>

    .sidebar {
        position: sticky;
        top: var(--header-height);
        height: calc(100vh - var(--header-height));
        width: var(--sidebar-width);         /* your expanded width */
        flex-shrink: 0;
        overflow-y: auto;
        border-right: 1px solid var(--color-neutral-200);
        background: var(--color-neutral-200);
        padding: 1rem;
        display: flex;
        flex-direction: column;
        transition: width 200ms ease, transform 200ms ease, opacity 150ms ease, padding 200ms ease;
    }


    .sidebar-toggle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: var(--radius-lg);
        color: var(--color-neutral-700);
        border: none;
        cursor: pointer;
        transition: background-color 150ms ease;
    }
    .sidebar-toggle:hover {
        transform: scale(1.4);
    }

    .sidebar-closed {
        width: 56px;                 
        padding: 0.75rem;            
        transform: translateX(0);    
        opacity: 1;                 
        /* IMPORTANT: allow clicks so the toggle works */
        pointer-events: auto;
    }

    .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .sidebar-list {
        display: flex;
        flex-direction: column;
        gap: .5rem;
    }

    .sidebar-item {
        display: flex;
        align-items: center;
        gap: .75rem;
        line-height: 1.5rem;
        height: 1.75rem;
        padding: 0 .75rem;
        border-radius: var(--radius-md);
        transition: background-color 120ms ease, color 120ms ease;
        cursor: pointer;
        text-decoration: none;
        color: inherit;
    }

    .sidebar-item:hover {
        border-radius: var(--radius-md);
        background: var(--color-white);
    }


    /* left accent bar */
    .sidebar-item.active::before {
        content: "";
        position: absolute;
        left: 0.25rem;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 70%;
        border-radius: 999px;
    }

    .sidebar-footer {
        margin-top: auto;                 
        padding-top: 1rem;
        padding-bottom: .5rem;
        text-align: center;
        color: var(--color-neutral-500);
        font-size: var(--text-xs);
        user-select: none;
    }
</style>