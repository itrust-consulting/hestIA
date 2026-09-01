<script lang="ts">
  import './layout.css';
  import ToastContainer from '$lib/components/ToastContainer.svelte';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import AccountSetIcon from '$lib/components/icons/accountSetIcon.svelte';
  import AdminIcon from '$lib/components/icons/adminIcon.svelte';
  import UserIcon from '$lib/components/icons/userIcon.svelte';
  import LogoutIcon from '$lib/components/icons/logoutIcon.svelte';
  import HelpIcon from '$lib/components/icons/helpIcon.svelte';
  import MoonIcon from '$lib/components/icons/moonIcon.svelte';
  import SunIcon from '$lib/components/icons/sunIcon.svelte';
  import HestiaIcon from '$lib/components/icons/hestiaIcon.svelte';
  import { sending } from '$lib/chat/actions';
  import { tooltip } from '$lib/actions/tooltip';

  import { onMount } from 'svelte';
  import { version } from '$app/environment';
  import { startInactivityWatcher, scheduleTokenExpiration, startHeartbeat } from '$lib/auth/session';
  import { clearIsmsState } from '$lib/stores/isms';
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
      collections: "Knowledge Base",
      tenants: "Tenant Management",
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
      if (page.data.tokenExp) scheduleTokenExpiration(page.data.tokenExp);
      if (page.data.user) startHeartbeat();

      const saved = localStorage.getItem('theme');
      if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        isDark = true;
        document.documentElement.classList.add('dark');
      }
  });

  const { children } = $props();
  let isDropdownOpen = $state(false);
  let isDark = $state(false);

  function toggleDark() {
    isDark = !isDark;
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }

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
    clearIsmsState();
    window.location.href = '/api/logout';
  }

  function handleLogout() {
    closeDropdown();
    logout();
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="flex flex-col h-screen overflow-hidden bg-white text-neutral-900"
  onclick={handleOutsideClick}
>
  <header class="app-header">
    <div class="app-header-left">
      <a class="app-brand" href="/chat"><HestiaIcon thinking={$sending} /><h1>hestIA</h1>
        <span class="app-version">{version}</span></a>
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
      <button class="icon-btn" onclick={toggleDark} aria-label="Toggle dark mode" use:tooltip={isDark ? 'Switch to light mode' : 'Switch to dark mode'}>
        {#if isDark}
          <SunIcon />
        {:else}
          <MoonIcon />
        {/if}
      </button>

      <div class="relative">
        <button
          class="icon-btn"
          onclick={toggleDropdown}
          aria-label="Account menu"
          use:tooltip={"Account menu"}
        >
          <UserIcon />
        </button>
        {#if isDropdownOpen}
          <div class="user-dropdown">
            <a class="dropdown-btn" href="/account/overview" onclick={closeDropdown}>
              <AccountSetIcon /> Account
            </a>
            {#if user?.permissions?.is_admin || (user?.permissions?.moderated_tenants?.length ?? 0) > 0}
              <a class="dropdown-btn" href="/admin" onclick={closeDropdown}>
                <AdminIcon /> Admin Panel
              </a>
            {/if}
            <a class="dropdown-btn" href="/help" onclick={closeDropdown}>
              <HelpIcon /> Help
            </a>
            <button class="dropdown-btn" onclick={handleLogout}>
              <LogoutIcon /> Logout
            </button>
          </div>
        {/if}
      </div>
    </div>
    {/if}
  </header>
  {@render children()}
  <ToastContainer />
</div>