<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import { addToast } from '$lib/stores/toast';
  import { invalidateAll } from '$app/navigation';
  import type { OrgBrief, JoinRequest, UserOrg, TenantSummary, Invitation } from '$lib/types';
  import SearchIcon from '$lib/components/icons/searchIcon.svelte';
  import InboxRequestRow from '$lib/components/InboxRequestRow.svelte';
  import CheckLgIcon from '$lib/components/icons/checkLgIcon.svelte';

  let {
    myOrgs,
    moderatedTenantIds,
    organizations,
    joinRequests,
    invitations,
  }: {
    myOrgs: UserOrg[];
    moderatedTenantIds: number[];
    organizations: OrgBrief[];
    joinRequests: JoinRequest[];
    invitations: Invitation[];
  } = $props();

  const myOrgIds = $derived(new Set(myOrgs.map((o) => o.id)));

  type TenantRow = { id: number; name: string; abbr: string; status: 'moderator' | 'member' | 'pending' };

  const tenantRows: TenantRow[] = $derived([
    ...myOrgs.map((o) => ({
      id: o.id,
      name: o.name,
      abbr: o.abbr,
      status: moderatedTenantIds.includes(o.id) ? ('moderator' as const) : ('member' as const),
    })),
    ...joinRequests
      .filter((r) => r.status === 'pending')
      .map((r) => ({ id: r.org_id, name: r.org_name ?? '', abbr: r.org_abbreviation ?? '', status: 'pending' as const })),
  ]);

  let search = $state('');
  const filteredOrgs = $derived(
    organizations
      .filter((o) => !myOrgIds.has(o.id))
      .filter(
        (o) => o.name.toLowerCase().includes(search.toLowerCase()) || o.abbreviation.toLowerCase().includes(search.toLowerCase())
      )
  );

  const requestedOrgIds = $derived(
    new Set(joinRequests.filter((r) => r.status === 'pending').map((r) => r.org_id))
  );

  const pendingInvitations = $derived(invitations.filter((i) => i.status === 'pending'));
  const invitedOrgIds = $derived(new Set(pendingInvitations.map((i) => i.org_id)));

  const CLASSIFICATION_LABELS = ['Public', 'Internal', 'Confidential', 'Restricted', 'Secret'];
  const classificationLabel = (level: number | null) =>
    level !== null && CLASSIFICATION_LABELS[level] ? CLASSIFICATION_LABELS[level] : 'Unknown';

  // ── Invitations ───────────────────────────────────────────────────────────
  let respondingInvite = $state<Record<string, boolean>>({});

  async function handleInvitationResponse(inv: Invitation, action: 'accept' | 'decline') {
    respondingInvite = { ...respondingInvite, [inv.id]: true };
    try {
      const res = await fetch(`/api/account/invitations/${inv.id}/${action}`, { method: 'POST' });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast(action === 'accept' ? 'Invitation accepted.' : 'Invitation declined.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to respond to invitation.', 'error');
    } finally {
      respondingInvite = { ...respondingInvite, [inv.id]: false };
    }
  }

  // ── Tenant summary (inline expand) ──────────────────────────────────────
  let expandedTenantId: number | null = $state(null);
  let tenantSummaries: Record<number, TenantSummary> = $state({});
  let summaryLoadingId: number | null = $state(null);

  async function toggleTenant(row: TenantRow) {
    if (row.status === 'pending') return;
    if (expandedTenantId === row.id) {
      expandedTenantId = null;
      return;
    }
    expandedTenantId = row.id;
    if (tenantSummaries[row.id]) return;
    summaryLoadingId = row.id;
    try {
      const res = await fetch(`/api/organizations/${row.id}/summary`);
      if (!res.ok) throw new Error(`${res.status}`);
      tenantSummaries = { ...tenantSummaries, [row.id]: await res.json() };
    } catch (e: any) {
      addToast('Failed to load tenant details.', 'error');
      expandedTenantId = null;
    } finally {
      summaryLoadingId = null;
    }
  }

  let requestOrg: OrgBrief | null = $state(null);
  let requestMessage = $state('');
  let requesting = $state(false);

  function openRequest(org: OrgBrief) {
    requestOrg = org;
    requestMessage = '';
  }

  async function handleRequest() {
    if (!requestOrg) return;
    requesting = true;
    try {
      const res = await fetch(`/api/organizations/${requestOrg.id}/join-requests`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: requestMessage.trim() || null }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Join request sent.', 'success');
      requestOrg = null;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to send join request.', 'error');
    } finally {
      requesting = false;
    }
  }
</script>

<h1 class="section-title">Tenants</h1>

{#if pendingInvitations.length > 0}
  <div class="tenants-card">
    <h2 class="subsection-title">Invitations</h2>
    <div class="inbox-rows">
      {#each pendingInvitations as inv (inv.id)}
        <InboxRequestRow
          requestType="Invitation"
          typeVariant="join"
          issuer={`${inv.org_name} (${inv.org_abbreviation})`}
          date={inv.created_at}
          message={inv.message}
        >
          {#snippet actions()}
            <button
              class="icon-btn-sm approve"
              aria-label="Accept"
              onclick={() => handleInvitationResponse(inv, 'accept')}
              disabled={respondingInvite[inv.id]}
            ><CheckLgIcon /></button>
            <button
              class="icon-btn-sm reject"
              aria-label="Decline"
              onclick={() => handleInvitationResponse(inv, 'decline')}
              disabled={respondingInvite[inv.id]}
            >✕</button>
          {/snippet}
        </InboxRequestRow>
      {/each}
    </div>
  </div>
{/if}

<div class="tenants-card">
  <h2 class="subsection-title">Your Tenants</h2>
  {#if tenantRows.length === 0}
    <p class="empty-note">You're not a member of any tenant yet.</p>
  {:else}
    <ul class="org-list">
      {#each tenantRows as row (`${row.status}-${row.id}`)}
        <li class="org-item">
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="org-row" class:clickable={row.status !== 'pending'} onclick={() => toggleTenant(row)}>
            <div>
              <span class="org-name">{row.name}</span>
              <span class="abbr-chip-sm">{row.abbr}</span>
            </div>
            {#if row.status === 'moderator'}
              <span class="badge badge-blue">Moderator</span>
            {:else if row.status === 'pending'}
              <span class="badge badge-yellow">Pending</span>
            {:else}
              <span class="badge">Member</span>
            {/if}
          </div>

          {#if expandedTenantId === row.id}
            <div class="tenant-expand">
              {#if summaryLoadingId === row.id}
                <p class="tenant-line muted">Loading…</p>
              {:else if tenantSummaries[row.id]}
                <p class="tenant-line"><span class="tenant-line-label">Members:</span> {tenantSummaries[row.id].member_count}</p>
                <p class="tenant-line">
                  <span class="tenant-line-label">Collections:</span>
                  {tenantSummaries[row.id].owned_collections.length > 0 ? tenantSummaries[row.id].owned_collections.join(', ') : 'None'}
                </p>
                <p class="tenant-line">
                  <span class="tenant-line-label">Accessible Collections:</span>
                  {tenantSummaries[row.id].accessible_collections.length > 0 ? tenantSummaries[row.id].accessible_collections.join(', ') : 'None'}
                </p>
                <p class="tenant-line"><span class="tenant-line-label">Your permission level:</span> {classificationLabel(tenantSummaries[row.id].classification_level)}</p>
              {:else}
                <p class="tenant-line muted">Unable to load tenant details.</p>
              {/if}
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<div class="tenants-card">
  <h2 class="subsection-title">Request to join a tenant</h2>
  <div class="search-input-wrap">
    <span class="search-input-icon"><SearchIcon /></span>
    <input class="search-input" type="text" placeholder="Search tenants…" bind:value={search} />
  </div>

  {#if search.trim() === ''}
    <p class="empty-note"></p>
  {:else if filteredOrgs.length === 0}
    <p class="empty-note">No tenants found.</p>
  {:else}
    <ul class="org-list">
      {#each filteredOrgs as org}
        <li class="org-row">
          <div>
            <span class="org-name">{org.name}</span>
            <span class="abbr-chip-sm">{org.abbreviation}</span>
          </div>
          {#if invitedOrgIds.has(org.id)}
            <span class="badge badge-blue">Invited</span>
          {:else if requestedOrgIds.has(org.id)}
            <span class="badge badge-yellow">Request pending</span>
          {:else}
            <button class="btn-secondary btn-sm" onclick={() => openRequest(org)}>Request to Join</button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<Modal title="Request to Join" open={requestOrg !== null} onClose={() => (requestOrg = null)}>
  <div class="form-stack">
    <p>Request to join <strong>{requestOrg?.name}</strong>?</p>
    <label class="field">
      <span>Message (optional)</span>
      <textarea rows="3" bind:value={requestMessage} placeholder="Visible to the tenant's moderators"></textarea>
    </label>
  </div>
  <svelte:fragment slot="footer">
    <button class="btn-primary" onclick={handleRequest} disabled={requesting}>
      {requesting ? 'Sending…' : 'Send request'}
    </button>
  </svelte:fragment>
</Modal>

<style>
  .section-title {
    font-size: var(--text-xl);
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .tenants-card {
    background: var(--color-neutral-50);
    padding: 1.75rem;
    border-radius: var(--radius-2xl);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    margin-bottom: 1.5rem;
  }

  .subsection-title {
    font-size: var(--text-base);
    font-weight: 700;
    color: var(--color-neutral-800);
    margin-bottom: 1rem;
  }

  .search-input-wrap {
    position: relative;
    margin-bottom: 1rem;
  }

  .search-input-icon {
    position: absolute;
    top: 50%;
    left: 0.75rem;
    transform: translateY(-50%);
    display: inline-flex;
    color: var(--color-neutral-400);
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 0.75rem 0.5rem 2.15rem;
    border: 1px solid var(--color-neutral-300);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    background: var(--color-white);
  }
  .search-input:focus {
    outline: none;
    border-color: var(--color-blue-500);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
  }

  .org-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    list-style: none;
  }

  .org-item {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .org-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0.75rem;
    border-radius: var(--radius-lg);
    background: var(--color-white);
    border: 1px solid var(--color-neutral-200);
  }
  .org-row.clickable {
    cursor: pointer;
    transition: border-color 120ms ease, background-color 120ms ease;
  }
  .org-row.clickable:hover {
    border-color: var(--color-blue-200);
    background: var(--color-blue-50, #eff6ff);
  }

  .tenant-expand {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.1rem 0.9rem 0.4rem;
  }

  .tenant-line {
    font-size: var(--text-sm);
    color: var(--color-neutral-700);
  }
  .tenant-line.muted {
    color: var(--color-neutral-500);
  }

  .tenant-line-label {
    font-weight: 600;
    color: var(--color-neutral-600);
  }

  .org-name {
    font-weight: 500;
    margin-right: 0.5rem;
  }

  .abbr-chip-sm {
    display: inline-block;
    padding: 0.05rem 0.4rem;
    border-radius: 999px;
    background: var(--color-blue-50);
    color: var(--color-blue-700);
    font-size: var(--text-xs);
    font-weight: 600;
  }

  .empty-note {
    color: var(--color-neutral-500);
    font-size: var(--text-sm);
    padding: 0.5rem 0;
  }

  .badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: var(--text-xs);
    font-weight: 600;
    text-transform: capitalize;
    background: var(--color-neutral-100);
    color: var(--color-neutral-600);
  }
  .badge-yellow { background: var(--color-yellow-100, #fef3c7); color: var(--color-yellow-700, #b45309); }
  .badge-blue { background: var(--color-blue-50, #eff6ff); color: var(--color-blue-700, #1d4ed8); }

  .inbox-rows {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .icon-btn-sm {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-neutral-300);
    background: var(--color-white);
    cursor: pointer;
    font-size: var(--text-sm);
    line-height: 1;
  }
  .icon-btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
  .icon-btn-sm.approve {
    color: var(--color-green-600, #16a34a);
    border-color: var(--color-green-300, #86efac);
  }
  .icon-btn-sm.approve:hover:not(:disabled) {
    background: var(--color-green-50, #f0fdf4);
  }
  .icon-btn-sm.reject {
    color: var(--color-red-600, #dc2626);
    border-color: var(--color-red-300, #fca5a5);
  }
  .icon-btn-sm.reject:hover:not(:disabled) {
    background: var(--color-red-50, #fef2f2);
  }

  .btn-sm {
    padding: 0.35rem 0.75rem;
    font-size: var(--text-xs);
  }
  .btn-secondary {
    background: var(--color-neutral-100); color: var(--color-neutral-800);
    border-radius: var(--radius-lg);
    font-weight: 500; border: 1px solid var(--color-neutral-300); cursor: pointer;
  }
  .btn-secondary:hover:not(:disabled) { background: var(--color-neutral-200); }

  .btn-primary {
    background: var(--color-blue-600); color: white;
    padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
    font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
  }
  .btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .form-stack { display: flex; flex-direction: column; gap: 0.875rem; }
  .field { display: flex; flex-direction: column; gap: 0.3rem; font-size: var(--text-sm); font-weight: 500; color: var(--color-neutral-700); }
  .field textarea {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-neutral-300);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    background: var(--color-white);
    font-family: inherit;
    resize: vertical;
  }
</style>
