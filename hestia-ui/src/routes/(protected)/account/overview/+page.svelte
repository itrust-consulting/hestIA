<script lang="ts">
  import AccountSidebar from '$lib/components/AccountSidebar.svelte';
  import ProfileCard from '$lib/components/account/ProfileCard.svelte';
  import SecurityCard from '$lib/components/account/SecurityCard.svelte';
  import TenantsCard from '$lib/components/account/TenantsCard.svelte';

  let { data } = $props();
</script>

<div class="layout">
  <AccountSidebar currentSection={data.section} />

  <main class="page-content">
    {#if !data.user}
      <p>Unable to load account details.</p>

    {:else if data.section === 'profile'}
      <ProfileCard user={data.user} />

    {:else if data.section === 'security'}
      <SecurityCard mustChangePw={data.user.must_change_pw} />

    {:else if data.section === 'tenants'}
      <TenantsCard
        myOrgs={data.user.orgs ?? []}
        moderatedTenantIds={data.user.permissions?.moderated_tenants ?? []}
        organizations={data.organizations ?? []}
        joinRequests={data.joinRequests ?? []}
        invitations={data.invitations ?? []}
      />

    {:else if data.section === 'support'}
      <h1>Support Center</h1>
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
