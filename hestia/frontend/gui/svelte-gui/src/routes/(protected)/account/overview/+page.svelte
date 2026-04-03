<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import AccountSidebar from '$lib/components/AccountSidebar.svelte';
  import ProfileCard from '$lib/components/account/ProfileCard.svelte';
  import SecurityCard from '$lib/components/account/SecurityCard.svelte';
  import { getAccountDetails } from '$lib/account/actions';

  let section = $state('profile');
  let user: any = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  const querySection = $derived(page.url.searchParams.get('section'));

  $effect(() => {
    if (querySection) section = querySection;
  });

  function select(newSection: string) {
    section = newSection;

    const params = new URLSearchParams(page.url.searchParams);
    params.set('section', newSection);

    goto(`/account/overview?${params}`);
  }

  onMount(async () => {
    try {
      user = await getAccountDetails();
    } catch (err: any) {
      error = err.message ?? 'Unable to load account details.';
    } finally {
      loading = false;
    }
  });
</script>

<div class="layout">
  <AccountSidebar bind:currentSection={section} onSelect={select} />

  <main class="page-content">
    {#if loading}
      <p>Loading account details…</p>

    {:else if error}
      <p style="color: red">{error}</p>

    {:else}
      {#if section === 'profile'}
        <ProfileCard {user}></ProfileCard>

      {:else if section === 'security'}
        <SecurityCard mustChangePw={user.must_change_pw} />

      {:else if section === 'settings'}
        <h1>Preferences</h1>

      {:else if section === 'billing'}
        <h1>Billing & Invoices</h1>

      {:else if section === 'sessions'}
        <h1>Active Sessions</h1>

      {:else if section === 'support'}
        <h1>Support Center</h1>

      {:else if section === 'logout'}
        <h1>You are being logged out…</h1>
      {/if}
    {/if}
  </main>
</div>

<style>
  .layout {
    display: flex;
    height: 100%;
    overflow: hidden;
  }
  .page-content {
    flex: 1;
    padding: 2rem;
    overflow-y: auto;
  }
</style>