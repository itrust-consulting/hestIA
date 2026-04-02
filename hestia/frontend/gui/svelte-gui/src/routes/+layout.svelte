<script lang="ts">
  import './layout.css';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import AccountSetIcon from '$lib/components/icons/accountSetIcon.svelte';
  import UserIcon from '$lib/components/icons/userIcon.svelte';
  import LogoutIcon from '$lib/components/icons/logoutIcon.svelte';
  import HelpIcon from '$lib/components/icons/helpIcon.svelte';

  import { onMount } from 'svelte';
  import { startInactivityWatcher } from '$lib/auth/session';
  import { page } from '$app/state';

  const path = $derived(page.url.pathname);

  // derive breadcrumb segments
  const segments = $derived(
    (() => {
      const parts = path.split('/').filter(Boolean);

      // hide breadcrumbs on home/chat
      if (parts.length === 0 || parts[0] === 'chat') return [];

      // optional: a nicer label map
      const labelMap: Record<string, string> = {
        admin: "Admin Dashboard",
        users: "User Management",
        account: "Account",
        overview: "Overview",
        security: "Security",
        settings: "Settings"
      };

      const cap = (s: string) =>
        labelMap[s] ?? s.charAt(0).toUpperCase() + s.slice(1);

      return parts.map(cap);
    })()
  );


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
      {#if segments.length > 0}
        <div class="breadcrumbs">
          {#each segments as seg, i}
            {seg}{#if i < segments.length - 1} <span class="crumb-sep">»</span> {/if}
          {/each}
        </div>
      {/if}
    </div>

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
  </header>
  {@render children()}
</div>