<script lang="ts">
  import './layout.css';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import AccountSetIcon from '$lib/components/icons/accountSetIcon.svelte';
  import AdminIcon from '$lib/components/icons/adminIcon.svelte';
  import UserIcon from '$lib/components/icons/userIcon.svelte';
  import LogoutIcon from '$lib/components/icons/logoutIcon.svelte';
  import HelpIcon from '$lib/components/icons/helpIcon.svelte';

  import { onMount } from 'svelte';
  import { startInactivityWatcher } from '$lib/auth/session';
  import { page } from '$app/state';

  const user = $derived(page.data.user)

  const path = $derived(page.url.pathname);
  const hideBreadcumbs = $derived(
        path === "/login" || path.startsWith("/chat")
      );

  const hideHeaderButtons = $derived(
    path === "/login"
  );
  
  type Breadcrumb = {
    label: string;
    href: string;
  };

  const breadcrumbs = $derived.by<Breadcrumb[]>(() => {
    if (hideBreadcumbs) return [];

    const parts = path.split('/').filter(Boolean);

    const labelMap: Record<string, string> = {
      admin: "Admin Dashboard",
      users: "User Management",
      account: "Account",
      overview: "Overview",
      security: "Security",
      settings: "Settings"
    };

    let currentPath = "";

    return parts.map((part) => {
      currentPath += `/${part}`;

      return {
        label: labelMap[part] ?? part.charAt(0).toUpperCase() + part.slice(1),
        href: currentPath
      };
    });
  });

  onMount(() => {
      startInactivityWatcher();
  });

  const { children } = $props();
  let isDropdownOpen = $state(false);

  // Toggle dropdown visibility
  function toggleDropdown() {
    isDropdownOpen = !isDropdownOpen;
  }

  // Close dropdown when clicking outside
  function handleOutsideClick(event: MouseEvent) {
    const dropdown = document.querySelector('.user-dropdown');
    if (dropdown && !dropdown.contains(event.target as Node)) {
      isDropdownOpen = false;
    }
  }

  // Close dropdown when clicking a menu item
  function closeDropdown() {
    isDropdownOpen = false;
  }

  function logout() {
    fetch('/api/logout', { method: 'POST' }).
    then(() => window.location.href = '/login');
  }

  function handleLogout() {
    closeDropdown();
    logout();
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="flex flex-col h-screen overflow-hidden"
  onclick={handleOutsideClick}
>
  <header class="app-header">
    <div class="app-header-left">
      <h1><a href="/chat">hestIA</a></h1>
      {#if breadcrumbs.length > 0}
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          {#each breadcrumbs as crumb, i}
            {#if i < breadcrumbs.length - 1}
              <a href={crumb.href} class="breadcrumb-link">
                {crumb.label}
              </a>
              <span class="crumb-sep">»</span>
            {:else}
              <span class="breadcrumb-current">
                {crumb.label}
              </span>
            {/if}
          {/each}
        </nav>
      {/if}
    </div>
    {#if !hideHeaderButtons}
    <div class="app-header-buttons">
      <button class="icon-btn">
        <SettingsIcon />
      </button>
      <div class="relative">
        <button
          class="icon-btn"
          onclick={toggleDropdown}
        >
          <UserIcon />
        </button>
        {#if isDropdownOpen}
          <div class="user-dropdown ">
            <button
              class="dropdown-btn"
              onclick={closeDropdown}
            >
              <AccountSetIcon /> <a href="/account/overview">Account</a>
            </button>
            {#if user?.permissions?.system_management}
              <button
                class="dropdown-btn"
                onclick={closeDropdown}
              >
                <AdminIcon />
                <a href="/admin">Admin Panel</a>
              </button>
            {/if}
            <button
              class="dropdown-btn"
              onclick={closeDropdown}
            >
              <HelpIcon /><a href=".">Help</a>
            </button>
            <button
              class="dropdown-btn"
              onclick={handleLogout}
            >
              <LogoutIcon />Logout
            </button>
          </div>
        {/if}
      </div>
    </div>
    {/if}
  </header>
  {@render children()}
</div>