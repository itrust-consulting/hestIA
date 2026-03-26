<script lang="ts">
  import './layout.css';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import AccountSetIcon from '$lib/components/icons/accountSetIcon.svelte';
  import UserIcon from '$lib/components/icons/userIcon.svelte';
  import LogoutIcon from '$lib/components/icons/logoutIcon.svelte';
  import HelpIcon from '$lib/components/icons/helpIcon.svelte';


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
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="flex flex-col h-screen overflow-hidden"
  onclick={handleOutsideClick}
>
  <header class="app-header">
    <div>
      <h1>hestIA</h1>
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
              <AccountSetIcon /> <a href=".">Account</a>
            </button>
            <button
              class="dropdown-btn"
              onclick={closeDropdown}
            >
              <HelpIcon /><a href=".">Help</a>
            </button>
            <button
              class="dropdown-btn"
              onclick={closeDropdown}
            >
              <LogoutIcon /><a href="../login">Logout</a>
            </button>
          </div>
        {/if}
      </div>
    </div>
  </header>
  {@render children()}
</div>