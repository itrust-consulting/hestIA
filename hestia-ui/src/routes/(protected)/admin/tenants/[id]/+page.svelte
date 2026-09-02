<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { untrack } from 'svelte';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import CreateCollectionModal from '$lib/components/modals/CreateCollectionModal.svelte';
  import type { Collection, JoinRequest, ShareRequest, OrgBrief, Invitation } from '$lib/types';
  import type { PageData } from './$types';
  import { addToast } from '$lib/stores/toast';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import EditIcon from '$lib/components/icons/editIcon.svelte';
  import CheckLgIcon from '$lib/components/icons/checkLgIcon.svelte';
  import InboxIcon from '$lib/components/icons/inboxIcon.svelte';
  import SendIcon from '$lib/components/icons/sendIcon.svelte';
  import InboxRequestRow from '$lib/components/InboxRequestRow.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  const { data }: { data: PageData } = $props();

  type Member = { id: string; username: string; email: string; first_name: string; last_name: string; classification_level: number; tenant_role: string | null };

  let tenant = $derived(data.tenant);
  let members: Member[] = $derived(data.members);
  let allUsers: any[] = $derived(data.allUsers);

  const memberIds = $derived(new Set(members.map((m) => m.id)));
  const availableUsers = $derived(allUsers.filter((u: any) => !memberIds.has(u.id)));

  const formatDate = (ts: number) =>
    ts ? new Date(ts).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

  // ── Details edit ─────────────────────────────────────────────────────────
  let editing = $state(untrack(() => data.editMode) ?? false);
  let editName = $state('');
  let editAbbr = $state('');
  let editSaving = $state(false);

  $effect(() => {
    editName = tenant.name;
    editAbbr = tenant.abbreviation;
  });

  function startEdit() {
    editName = tenant.name;
    editAbbr = tenant.abbreviation;
    editing = true;
  }

  function cancelEdit() {
    editing = false;
  }

  async function handleSave() {
    if (!editName.trim() || !editAbbr.trim()) return;
    editSaving = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: editName.trim(), abbreviation: editAbbr.trim() }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      editing = false;
      addToast('Tenant updated.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to update tenant.', 'error');
    } finally {
      editSaving = false;
    }
  }

  // ── Delete tenant ─────────────────────────────────────────────────────────
  let confirmDeleteOpen = $state(false);

  async function deleteTenant() {
    const res = await fetch(`/api/admin/tenants/${tenant.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete tenant.');
    goto('/admin/tenants');
  }

  // ── Remove member ─────────────────────────────────────────────────────────
  let confirmRemoveMember: Member | null = $state(null);

  async function handleRemoveMember() {
    const res = await fetch(`/api/admin/tenants/${tenant.id}/members/${confirmRemoveMember!.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to remove member.');
    await invalidateAll();
  }
  
  // ── Delete Collection ──────────────────────────────────────────────────────
  let confirmDeleteCol = $state<string | null>(null);

  async function handleDeleteCollection() {
    const [tenantRes, qdrantRes] = await Promise.all([
      fetch(`/api/admin/tenants/${tenant.id}/collections/${encodeURIComponent(confirmDeleteCol!)}`, { method: 'DELETE' }),
      fetch(`/api/admin/collections/${encodeURIComponent(confirmDeleteCol!)}`, { method: 'DELETE' }),
    ]);
    if (!tenantRes.ok || !qdrantRes.ok) throw new Error('Failed to delete collection.');
    await invalidateAll();
  }

  // ── Add member / invite user ────────────────────────────────────────────────
  // Admins pick from a dropdown of existing users (immediate add). Moderators
  // don't get a browsable user list, so they send an invite by username/email
  // instead -- same button, different flow depending on data.isAdmin.
  const invitations: Invitation[] = $derived(data.invitations ?? []);

  let addOpen = $state(false);
  let memberSearchText = $state('');
  let adding = $state(false);
  let inviteIdentifier = $state('');
  let inviteMessage = $state('');
  let inviting = $state(false);

  const selectedUser = $derived(
    availableUsers.find((u: any) => u.username === memberSearchText)
  );
  const selectedUserId = $derived(selectedUser?.id ?? '');

  function openAdd() {
    memberSearchText = '';
    inviteIdentifier = '';
    inviteMessage = '';
    addOpen = true;
  }

  async function handleAdd() {
    if (!selectedUserId) return;
    adding = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/members`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ user_id: selectedUserId }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Member added.', 'success');
      addOpen = false;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to add member.', 'error');
    } finally {
      adding = false;
    }
  }

  async function handleInvite() {
    if (!inviteIdentifier.trim()) return;
    inviting = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/invitations`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ identifier: inviteIdentifier.trim(), message: inviteMessage.trim() || null }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Invitation sent.', 'success');
      addOpen = false;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to send invitation.', 'error');
    } finally {
      inviting = false;
    }
  }

  let cancellingInvite = $state<Record<string, boolean>>({});

  async function cancelInvitation(inv: Invitation) {
    cancellingInvite = { ...cancellingInvite, [inv.id]: true };
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/invitations/${inv.id}/cancel`, { method: 'POST' });
      if (!res.ok) throw new Error(`${res.status}`);
      addToast('Invitation cancelled.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to cancel invitation.', 'error');
    } finally {
      cancellingInvite = { ...cancellingInvite, [inv.id]: false };
    }
  }

  // ── Member classification / role ──────────────────────────────────────────
  let savingMember = $state<Record<string, boolean>>({});

  async function setClassification(memberId: string, level: number) {
    savingMember = { ...savingMember, [memberId]: true };
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/members/${memberId}/classification`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ level }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to update classification.', 'error');
    } finally {
      savingMember = { ...savingMember, [memberId]: false };
    }
  }

  async function setTenantRole(memberId: string, role: string | null) {
    savingMember = { ...savingMember, [memberId]: true };
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/members/${memberId}/role`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to update role.', 'error');
    } finally {
      savingMember = { ...savingMember, [memberId]: false };
    }
  }

  // ── Collections ───────────────────────────────────────────────────────────
  let ownedCollections: Collection[] = $state(data.ownedCollections ?? []);
  let accessibleCollections: Collection[] = $state(data.accessibleCollections ?? []);
  $effect(() => { ownedCollections = data.ownedCollections ?? []; });
  $effect(() => { accessibleCollections = data.accessibleCollections ?? []; });

 

  let uploadOpen = $state(false);

  const uploadOrganizations = $derived(data.uploadOrganizations ?? []);

  function handleCreateSuccess(collectionName: string) {
    goto(`/admin/collections/${encodeURIComponent(collectionName)}`);
  }

  // ── Join requests ─────────────────────────────────────────────────────────
  // Server-side loader already filters to status=pending.
  const pendingJoinRequests: JoinRequest[] = $derived(data.joinRequests ?? []);

  let approveJoinReq: JoinRequest | null = $state(null);
  let approveTenantRole = $state('');
  let approveClassification = $state(0);
  let approvingJoin = $state(false);

  function openApproveJoin(req: JoinRequest) {
    approveJoinReq = req;
    approveTenantRole = '';
    approveClassification = 0;
  }

  async function handleApproveJoin() {
    if (!approveJoinReq) return;
    approvingJoin = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/join-requests/${approveJoinReq.id}/approve`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ tenant_role: approveTenantRole || null, classification_level: approveClassification }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Join request accepted.', 'success');
      approveJoinReq = null;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to accept request.', 'error');
    } finally {
      approvingJoin = false;
    }
  }

  let rejectJoinReq: JoinRequest | null = $state(null);
  let rejectJoinReason = $state('');
  let rejectingJoin = $state(false);

  function openRejectJoin(req: JoinRequest) {
    rejectJoinReq = req;
    rejectJoinReason = '';
  }

  async function handleRejectJoin() {
    if (!rejectJoinReq) return;
    rejectingJoin = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/join-requests/${rejectJoinReq.id}/reject`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ reason: rejectJoinReason.trim() || null }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Join request rejected.', 'success');
      rejectJoinReq = null;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to reject request.', 'error');
    } finally {
      rejectingJoin = false;
    }
  }

  // ── Sharing requests ──────────────────────────────────────────────────────
  // Server-side loader already filters incoming to status=pending.
  const pendingIncomingShare: ShareRequest[] = $derived(data.incomingShareRequests ?? []);
  // Server-side loader already filters outgoing to status=pending.
  const pendingOutgoingShare: ShareRequest[] = $derived(data.outgoingShareRequests ?? []);
  const allTenants: OrgBrief[] = $derived(data.allTenants ?? []);

  // ── Inbox (merged join + incoming share requests) ──────────────────────────
  type InboxItem =
    | { kind: 'join'; id: string; created_at: number; join: JoinRequest }
    | { kind: 'share'; id: string; created_at: number; share: ShareRequest };

  const INBOX_PAGE_SIZE = 4;
  let inboxExpanded = $state(false);

  const inboxItems: InboxItem[] = $derived(
    [
      ...pendingJoinRequests.map((r) => ({ kind: 'join' as const, id: `join-${r.id}`, created_at: r.created_at, join: r })),
      ...pendingIncomingShare.map((r) => ({ kind: 'share' as const, id: `share-${r.id}`, created_at: r.created_at, share: r })),
    ].sort((a, b) => b.created_at - a.created_at)
  );
  const visibleInboxItems = $derived(inboxExpanded ? inboxItems : inboxItems.slice(0, INBOX_PAGE_SIZE));
  const otherTenants = $derived(allTenants.filter((t) => t.id !== tenant.id));

  let fileShareOpen = $state(false);
  let fileShareTargetId = $state('');
  let fileShareMessage = $state('');
  let filingShare = $state(false);

  function openFileShare() {
    fileShareTargetId = otherTenants[0]?.id != null ? String(otherTenants[0].id) : '';
    fileShareMessage = '';
    fileShareOpen = true;
  }

  async function handleFileShare() {
    if (!fileShareTargetId) return;
    filingShare = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/share-requests`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ target_org_id: Number(fileShareTargetId), message: fileShareMessage.trim() || null }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Sharing request sent.', 'success');
      fileShareOpen = false;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to send sharing request.', 'error');
    } finally {
      filingShare = false;
    }
  }

  let approveShareReq: ShareRequest | null = $state(null);
  let shareSelections: Record<string, { checked: boolean; max_classification: number }> = $state({});
  let approvingShare = $state(false);

  function openApproveShare(req: ShareRequest) {
    approveShareReq = req;
    shareSelections = Object.fromEntries(
      ownedCollections.map((c) => [c.id, { checked: false, max_classification: 0 }])
    );
  }

  async function handleApproveShare() {
    if (!approveShareReq) return;
    const collections = Object.entries(shareSelections)
      .filter(([, v]) => v.checked)
      .map(([collection_id, v]) => ({ collection_id, max_classification: v.max_classification }));
    if (collections.length === 0) {
      addToast('Select at least one knowledge base to share.', 'error');
      return;
    }
    approvingShare = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/share-requests/${approveShareReq.id}/approve`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ collections }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Sharing request accepted.', 'success');
      approveShareReq = null;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to accept sharing request.', 'error');
    } finally {
      approvingShare = false;
    }
  }

  let rejectShareReq: ShareRequest | null = $state(null);
  let rejectShareReason = $state('');
  let rejectingShare = $state(false);

  function openRejectShare(req: ShareRequest) {
    rejectShareReq = req;
    rejectShareReason = '';
  }

  async function handleRejectShare() {
    if (!rejectShareReq) return;
    rejectingShare = true;
    try {
      const res = await fetch(`/api/admin/tenants/${tenant.id}/share-requests/${rejectShareReq.id}/reject`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ reason: rejectShareReason.trim() || null }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Sharing request rejected.', 'success');
      rejectShareReq = null;
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to reject sharing request.', 'error');
    } finally {
      rejectingShare = false;
    }
  }

</script>

<div class="admin-content">
  <!-- ── Header ─────────────────────────────────────────────────────────── -->
  <div class="page-header">
    <div class="page-header-left">
      <div class="avatar">{tenant.name?.charAt(0).toUpperCase()}</div>
      <div>
        <div class="title-row">
          <h1 class="title">{tenant.name}</h1>
          <span class="abbr-chip">{tenant.abbreviation}</span>
        </div>
        <span class="meta">Created {formatDate(tenant.created_at)}</span>
      </div>
    </div>
  </div>

  <!-- ── Details card ───────────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Details</h2>
      {#if data.isAdmin && !editing}
        <button class="icon-btn" aria-label="Edit" use:tooltip={"Edit"} onclick={startEdit}>
          <EditIcon />
        </button>
      {/if}
    </div>

    {#if editing}
      <div class="form-grid">
        <label class="field">
          <span>Name</span>
          <input type="text" bind:value={editName} />
        </label>
        <label class="field">
          <span>Abbreviation</span>
          <input type="text" bind:value={editAbbr} />
        </label>
      </div>
      <div class="card-footer">
        <button class="btn-secondary" onclick={cancelEdit} disabled={editSaving}>Cancel</button>
        <button class="btn-primary" onclick={handleSave}
          disabled={editSaving || !editName.trim() || !editAbbr.trim()}>
          {editSaving ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    {:else}
      <dl class="info-grid">
        <div class="info-row">
          <dt>Name</dt>
          <dd>{tenant.name}</dd>
        </div>
        <div class="info-row">
          <dt>Abbreviation</dt>
          <dd><span class="abbr-chip">{tenant.abbreviation}</span></dd>
        </div>
        <div class="info-row">
          <dt>Created</dt>
          <dd>{formatDate(tenant.created_at)}</dd>
        </div>
      </dl>
    {/if}
  </section>

  <!-- ── Inbox card ─────────────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Inbox</h2>
      <div class="inbox-header-icon">
        <InboxIcon />
        {#if inboxItems.length > 0}
          <span class="inbox-count-badge">{inboxItems.length > 99 ? '99+' : inboxItems.length}</span>
        {/if}
      </div>
    </div>

    {#if inboxItems.length === 0}
      <p class="empty-note">No pending requests.</p>
    {:else}
      <div class="inbox-rows">
        {#each visibleInboxItems as item (item.id)}
          {#if item.kind === 'join'}
            <InboxRequestRow
              requestType="Join Request"
              typeVariant="join"
              issuer={`${item.join.first_name} ${item.join.last_name} (${item.join.username})`}
              date={item.join.created_at}
              message={item.join.message}
            >
              {#snippet actions()}
                <button class="icon-btn-sm approve" aria-label="Accept" use:tooltip={"Accept"} onclick={() => openApproveJoin(item.join)}><CheckLgIcon /></button>
                <button class="icon-btn-sm reject" aria-label="Reject" use:tooltip={"Reject"} onclick={() => openRejectJoin(item.join)}>✕</button>
              {/snippet}
            </InboxRequestRow>
          {:else}
            <InboxRequestRow
              requestType="Sharing Request"
              typeVariant="share"
              issuer={`${item.share.other_org_name} (${item.share.other_org_abbreviation})`}
              date={item.share.created_at}
              message={item.share.message}
            >
              {#snippet actions()}
                <button class="icon-btn-sm approve" aria-label="Accept" use:tooltip={"Accept"} onclick={() => openApproveShare(item.share)}><CheckLgIcon /></button>
                <button class="icon-btn-sm reject" aria-label="Reject" use:tooltip={"Reject"} onclick={() => openRejectShare(item.share)}>✕</button>
              {/snippet}
            </InboxRequestRow>
          {/if}
        {/each}
      </div>
      {#if inboxItems.length > visibleInboxItems.length}
        <button class="show-more-btn" onclick={() => (inboxExpanded = true)}>
          Show more ({inboxItems.length - visibleInboxItems.length})
        </button>
      {/if}
    {/if}
  </section>

  <!-- ── Members card ───────────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Members</h2>
      <button
        class="icon-btn"
        aria-label={data.isAdmin ? 'Add member' : 'Invite user'}
        use:tooltip={data.isAdmin ? 'Add member' : 'Invite user'}
        onclick={openAdd}
        disabled={data.isAdmin && availableUsers.length === 0}
      >
        <PlusLgIcon />
      </button>
    </div>

    {#if invitations.length > 0}
      <div class="inbox-rows">
        {#each invitations as inv (inv.id)}
          <InboxRequestRow
            requestType="Invitation Sent"
            typeVariant="outgoing"
            issuer={inv.username ? `${inv.first_name} ${inv.last_name} (${inv.username})` : inv.email ?? ''}
            date={inv.created_at}
            message={inv.message}
          >
            {#snippet actions()}
              <button class="btn-secondary btn-sm" onclick={() => cancelInvitation(inv)} disabled={cancellingInvite[inv.id]}>
                {cancellingInvite[inv.id] ? 'Cancelling…' : 'Cancel'}
              </button>
            {/snippet}
          </InboxRequestRow>
        {/each}
      </div>
    {/if}

    {#if members.length === 0}
      <p class="empty-note">No members yet.</p>
    {:else}
      <table class="data-table">
        <thead>
          <tr>
            <th>No.</th>
            <th>Username</th>
            <th>Name</th>
            <th>Email</th>
            <th>Classification</th>
            <th>Role</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each members as m, i}
            <tr onclick={() => goto(`/admin/users/${m.id}`)} class="clickable">
              <td class="num">{i + 1}</td>
              <td class="name">{m.username}</td>
              <td>{m.first_name} {m.last_name}</td>
              <td class="muted">{m.email}</td>
              <td onclick={(e) => e.stopPropagation()}>
                <select class="inline-select" value={m.classification_level}
                  onchange={(e) => setClassification(m.id, Number((e.currentTarget as HTMLSelectElement).value))}
                  disabled={savingMember[m.id]}>
                  <option value={0}>Public</option>
                  <option value={1}>Internal</option>
                  <option value={2}>Confidential</option>
                  <option value={3}>Restricted</option>
                  <option value={4}>Secret</option>
                </select>
              </td>
              <td onclick={(e) => e.stopPropagation()}>
                <select class="inline-select" value={m.tenant_role ?? ''}
                  onchange={(e) => setTenantRole(m.id, (e.currentTarget as HTMLSelectElement).value || null)}
                  disabled={savingMember[m.id]}>
                  <option value="">Member</option>
                  <option value="co-moderator">Co-moderator</option>
                  <option value="moderator">Moderator</option>
                </select>
              </td>
              <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
                <button class="del-btn-icon" aria-label="Remove member" use:tooltip={"Delete"} onclick={() => (confirmRemoveMember = m)}><BinIcon /></button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <!-- ── Collections cards ──────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Collections</h2>
      <div class="col-header-actions">
        <button class="icon-btn" aria-label="Add collection" use:tooltip={"Add collection"} onclick={() => (uploadOpen = true)}>
          <PlusLgIcon />
        </button>
      </div>
    </div>
    {#if ownedCollections.length === 0}
      <p class="empty-note">No collections created.</p>
    {:else}
      <table class="data-table col-table">
        <thead>
          <tr>
            <th>Collection</th>
            <th>Owner</th>
            <th>Docs</th>
            <th>Status</th>
            <th>Access Granted</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each ownedCollections as col}
            <tr class="clickable-row" onclick={() => goto(`/admin/collections/${encodeURIComponent(col.id)}`)}>
              <td class="name">{col.id}</td>
              <td class="muted">
                  <span class="abbr-chip-sm">{tenant.name}</span>
              </td>
              <td class="muted">{col.documentCount}</td>
              <td><span class="status-dot" class:green={col.status === 'green'}></span></td>
              <td class="muted">
                {#if col.access.length > 0}
                  {col.access.map(a => a.abbreviation).join(', ')}
                {:else}
                  <span class="no-access">No external access</span>
                {/if}
              </td>
              {#if data.isAdmin}
                <td class="actions-cell">
                  <button class="del-btn-icon" aria-label="Delete collection" use:tooltip={"Delete"} onclick={(e) => { e.stopPropagation(); confirmDeleteCol = col.id; }}><BinIcon /></button>
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Accessible Collections</h2>
      <button class="icon-btn send-btn" aria-label="Send access request" use:tooltip={"Send access request"} onclick={openFileShare} disabled={otherTenants.length === 0}>
        <SendIcon />
      </button>
    </div>

    {#if pendingOutgoingShare.length > 0}
      <div class="inbox-rows">
        {#each pendingOutgoingShare as r (r.id)}
          <InboxRequestRow
            requestType="Request Sent"
            typeVariant="outgoing"
            issuer={`To ${r.other_org_name} (${r.other_org_abbreviation})`}
            date={r.created_at}
            message={r.message}
          >
            {#snippet actions()}
              <span class="pending-tag">Pending</span>
            {/snippet}
          </InboxRequestRow>
        {/each}
      </div>
    {/if}

    {#if accessibleCollections.length === 0}
      <p class="empty-note">No collections assigned to this tenant.</p>
    {:else}
      <table class="data-table col-table">
        <thead>
          <tr>
            <th>Collection</th>
            <th>Owner</th>
            <th>Docs</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {#each accessibleCollections as col}
            <tr>
              <td class="name">{col.id}</td>
              <td class="muted">
                {#if col.ownerTenant}
                  <span class="abbr-chip-sm">{col.ownerTenant.name}</span>
                {:else}
                  <span class="no-access">No owner assigned</span>
                {/if}
              </td>
              <td class="muted">{col.documentCount}</td>
              <td><span class="status-dot" class:green={col.status === 'green'}></span></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <!-- ── Danger zone ────────────────────────────────────────────────────── -->
  {#if data.isAdmin}
    <section class="card danger-card">
      <div class="danger-row">
        <div>
          <p class="danger-title">Delete this tenant</p>
          <p class="danger-desc">
            Permanently delete <strong>{tenant.name}</strong> and remove it from all users.
          </p>
          <p class="danger-desc">This will not affect documents in the knowledge base.</p>
        </div>
        <button class="danger-btn" onclick={() => (confirmDeleteOpen = true)}>Delete tenant</button>
      </div>
    </section>
  {/if}
</div>

<!-- ── Add member / invite user modal ─────────────────────────────────────── -->
<Modal title={data.isAdmin ? 'Add Member' : 'Invite User'} open={addOpen} onClose={() => (addOpen = false)}>
  {#if data.isAdmin}
    <div class="form-stack">
      {#if availableUsers.length === 0}
        <p class="muted-note">All users are already members of this tenant.</p>
      {:else}
        <label class="field">
          <span>Search user</span>
          <input type="text" list="available-users-list" bind:value={memberSearchText} placeholder="Search by username or name…" />
          <datalist id="available-users-list">
            {#each availableUsers as u}
              <option value={u.username}>{u.first_name} {u.last_name} — {u.email}</option>
            {/each}
          </datalist>
        </label>
      {/if}
    </div>
  {:else}
    <div class="form-stack">
      <label class="field">
        <span>Username or email</span>
        <input type="text" bind:value={inviteIdentifier} placeholder="jdoe or jdoe@example.com" />
      </label>
      <label class="field">
        <span>Message (optional)</span>
        <textarea rows="3" bind:value={inviteMessage} placeholder="Visible to the invited user"></textarea>
      </label>
    </div>
  {/if}
  <svelte:fragment slot="footer">
    {#if data.isAdmin}
      <button class="btn-primary" onclick={handleAdd}
        disabled={adding || !selectedUserId || availableUsers.length === 0}>
        {adding ? 'Adding…' : 'Add'}
      </button>
    {:else}
      <button class="btn-primary" onclick={handleInvite} disabled={inviting || !inviteIdentifier.trim()}>
        {inviting ? 'Sending…' : 'Send invitation'}
      </button>
    {/if}
  </svelte:fragment>
</Modal>

<!-- ── Create Collection modal ────────────────────────────────────────────── -->
<CreateCollectionModal
  open={uploadOpen}
  onClose={() => (uploadOpen = false)}
  ownerOrgs={uploadOrganizations}
  accessOrgs={uploadOrganizations}
  defaultOwner={tenant.abbreviation}
  onSuccess={handleCreateSuccess}
/>

<ConfirmDeleteModal
  open={confirmDeleteOpen}
  title="Delete Tenant"
  onClose={() => (confirmDeleteOpen = false)}
  onConfirm={deleteTenant}
  successMessage="Tenant deleted."
>
  <p>Permanently delete <strong>{tenant.name}</strong>?</p>
  <p> This cannot be undone.</p>
</ConfirmDeleteModal>

<ConfirmDeleteModal
  open={confirmRemoveMember !== null}
  title="Remove Member"
  onClose={() => (confirmRemoveMember = null)}
  onConfirm={handleRemoveMember}
  confirmLabel="Remove"
  successMessage="Member removed."
>
  <p>Remove <strong>{confirmRemoveMember?.username}</strong> from <strong>{tenant.name}</strong>?</p>
  <p>The user account will not be deleted.</p>
</ConfirmDeleteModal>

<!-- ── Accept join request modal ──────────────────────────────────────────── -->
<Modal title="Accept Join Request" open={approveJoinReq !== null} onClose={() => (approveJoinReq = null)}>
  <div class="form-stack">
    <p>Add <strong>{approveJoinReq?.first_name} {approveJoinReq?.last_name}</strong> to <strong>{tenant.name}</strong> as:</p>
    <label class="field">
      <span>Classification level</span>
      <select bind:value={approveClassification}>
        <option value={0}>Public</option>
        <option value={1}>Internal</option>
        <option value={2}>Confidential</option>
        <option value={3}>Restricted</option>
        <option value={4}>Secret</option>
      </select>
    </label>
    <label class="field">
      <span>Tenant role</span>
      <select bind:value={approveTenantRole}>
        <option value="">Member</option>
        <option value="co-moderator">Co-moderator</option>
        <option value="moderator">Moderator</option>
      </select>
    </label>
  </div>
  <svelte:fragment slot="footer">
    <button class="btn-primary" onclick={handleApproveJoin} disabled={approvingJoin}>
      {approvingJoin ? 'Accepting…' : 'Accept'}
    </button>
  </svelte:fragment>
</Modal>

<!-- ── Reject join request modal ──────────────────────────────────────────── -->
<Modal title="Reject Join Request" open={rejectJoinReq !== null} onClose={() => (rejectJoinReq = null)}>
  <div class="form-stack">
    <p>Reject <strong>{rejectJoinReq?.first_name} {rejectJoinReq?.last_name}</strong>'s request to join <strong>{tenant.name}</strong>?</p>
    <label class="field">
      <span>Reason (optional)</span>
      <textarea rows="3" bind:value={rejectJoinReason} placeholder="Visible to the requester"></textarea>
    </label>
  </div>
  <svelte:fragment slot="footer">
    <button class="danger-btn" onclick={handleRejectJoin} disabled={rejectingJoin}>
      {rejectingJoin ? 'Rejecting…' : 'Reject'}
    </button>
  </svelte:fragment>
</Modal>

<!-- ── File sharing request modal ─────────────────────────────────────────── -->
<Modal title="Send access request" open={fileShareOpen} onClose={() => (fileShareOpen = false)}>
  <div class="form-stack">
    {#if otherTenants.length === 0}
      <p class="muted-note">No other tenants exist yet.</p>
    {:else}
      <label class="field">
        <span>Target tenant</span>
        <select bind:value={fileShareTargetId}>
          {#each otherTenants as t}
            <option value={String(t.id)}>{t.name} ({t.abbreviation})</option>
          {/each}
        </select>
      </label>
      <label class="field">
        <span>Message (optional)</span>
        <textarea rows="3" bind:value={fileShareMessage} placeholder="Explain what access you're looking for"></textarea>
      </label>
    {/if}
  </div>
  <svelte:fragment slot="footer">
    <button class="btn-primary" onclick={handleFileShare} disabled={filingShare || !fileShareTargetId}>
      {filingShare ? 'Sending…' : 'Send request'}
    </button>
  </svelte:fragment>
</Modal>

<!-- ── Accept sharing request modal ───────────────────────────────────────── -->
<Modal title="Accept Sharing Request" open={approveShareReq !== null} onClose={() => (approveShareReq = null)} wide>
  <div class="form-stack">
    <p>Select which of <strong>{tenant.name}</strong>'s knowledge bases to share with <strong>{approveShareReq?.other_org_name}</strong>:</p>
    {#if ownedCollections.length === 0}
      <p class="muted-note">This tenant owns no knowledge bases.</p>
    {:else}
      <table class="data-table">
        <thead>
          <tr>
            <th></th>
            <th>Collection</th>
            <th>Max classification</th>
          </tr>
        </thead>
        <tbody>
          {#each ownedCollections as col}
            <tr>
              <td>
                <input type="checkbox" bind:checked={shareSelections[col.id].checked} />
              </td>
              <td class="name">{col.id}</td>
              <td>
                <select class="inline-select" bind:value={shareSelections[col.id].max_classification} disabled={!shareSelections[col.id].checked}>
                  <option value={0}>Public</option>
                  <option value={1}>Internal</option>
                  <option value={2}>Confidential</option>
                  <option value={3}>Restricted</option>
                  <option value={4}>Secret</option>
                </select>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
  <svelte:fragment slot="footer">
    <button class="btn-primary" onclick={handleApproveShare} disabled={approvingShare}>
      {approvingShare ? 'Sharing…' : 'Share selected'}
    </button>
  </svelte:fragment>
</Modal>

<!-- ── Reject sharing request modal ───────────────────────────────────────── -->
<Modal title="Reject Sharing Request" open={rejectShareReq !== null} onClose={() => (rejectShareReq = null)}>
  <div class="form-stack">
    <p>Reject the sharing request from <strong>{rejectShareReq?.other_org_name}</strong>?</p>
    <label class="field">
      <span>Reason (optional)</span>
      <textarea rows="3" bind:value={rejectShareReason} placeholder="Visible to the requesting tenant's moderators"></textarea>
    </label>
  </div>
  <svelte:fragment slot="footer">
    <button class="danger-btn" onclick={handleRejectShare} disabled={rejectingShare}>
      {rejectingShare ? 'Rejecting…' : 'Reject'}
    </button>
  </svelte:fragment>
</Modal>

<ConfirmDeleteModal
  open={confirmDeleteCol !== null}
  title="Delete Collection"
  onClose={() => (confirmDeleteCol = null)}
  onConfirm={handleDeleteCollection}
  successMessage="Collection deleted."
>
  <p>Permanently delete <strong>{confirmDeleteCol}</strong> and all its documents?</p>
  <p>This cannot be undone.</p>
</ConfirmDeleteModal>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-4xl);
  margin-inline: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.avatar {
  width: 52px; height: 52px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-blue-600) 80%, transparent);
  color: white;
  font-size: var(--text-2xl);
  font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.title-row {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.title { font-size: var(--text-2xl); font-weight: 700; margin-bottom: 0.15rem; }
.meta { font-size: var(--text-sm); color: var(--color-neutral-500); }

.danger-card {
  border: 1px solid var(--color-red-200);
}
.danger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.danger-title {
  font-weight: 600;
  color: var(--color-neutral-800);
  margin-bottom: 0.2rem;
}
.danger-desc {
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
  max-width: 40rem;
}

.card {
  background: var(--color-neutral-50);
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.section-title {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-neutral-800);
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.section-header .section-title { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }

.card-footer {
  margin-top: 1.25rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.info-grid { display: flex; flex-direction: column; gap: 0; }
.info-row {
  display: grid;
  grid-template-columns: 10rem 1fr;
  align-items: baseline;
  gap: 1rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--color-neutral-100);
}
.info-row:last-child { border-bottom: none; }
.info-row dt { font-size: var(--text-sm); font-weight: 600; color: var(--color-neutral-500); }
.info-row dd { font-size: var(--text-sm); color: var(--color-neutral-800); }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.875rem 1.25rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input[type="text"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
}
.field input[type="text"]:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.field select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
}
.field select:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-100);
  text-align: left;
  vertical-align: middle;
  font-size: var(--text-sm);
}
.data-table thead th {
  font-weight: 600;
  color: var(--color-neutral-600);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: var(--color-neutral-50); }
.data-table tbody tr.clickable { cursor: pointer; }

td.num { width: 3.5rem; text-align: right; color: var(--color-neutral-400); }
td.name { font-weight: 500; }
td.muted { color: var(--color-neutral-500); }
td.actions-cell { width: 5rem; text-align: right; }
.clickable-row { cursor: pointer; }


.empty-note {
  color: var(--color-neutral-500);
  font-size: var(--text-sm);
  padding: 1rem 0;
}

.inline-select {
  padding: 0.2rem 0.4rem;
  font-size: var(--text-xs);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-neutral-300);
  background: var(--color-white);
  color: var(--color-neutral-800);
  cursor: pointer;
}
.inline-select:focus { outline: none; border-color: var(--color-blue-500); }
.inline-select:disabled {
  background: var(--color-neutral-100);
  color: var(--color-neutral-400);
  cursor: not-allowed;
}

.abbr-chip {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.03em;
}

.col-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.add-col-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.col-table td { font-size: var(--text-sm); }
.col-table td.name { font-weight: 500; }
.no-access { color: var(--color-neutral-400); font-style: italic; font-size: var(--text-xs); }

.status-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--color-neutral-400);
}
.status-dot.green { background: var(--color-green-500); }

.abbr-chip-sm {
  display: inline-block;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
}


.btn-primary {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.danger-btn {
  background: var(--color-red-600); color: white;
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
  white-space: nowrap;
}
.danger-btn:hover:not(:disabled) { background: var(--color-red-700); }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: var(--color-neutral-100); color: var(--color-neutral-800);
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-size: var(--text-sm); font-weight: 500; border: 1px solid var(--color-neutral-300); cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { background: var(--color-neutral-200); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: var(--text-xs);
}

.del-btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.3rem;
  border-radius: var(--radius-md);
  cursor: pointer;
}
.del-btn-icon:hover { background: var(--color-red-50); }

.form-stack { display: flex; flex-direction: column; gap: 0.875rem; }
.muted-note { color: var(--color-neutral-500); font-size: var(--text-sm); }

.field textarea {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
  font-family: inherit;
  resize: vertical;
}
.field textarea:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.send-btn {
  padding: calc(var(--spacing) * 1.25);
  transform: scale(1.5);
}
.send-btn:hover {
  transform: scale(1.05);
}
.send-btn :global(svg) {
  width: 12px;
  height: 12px;
}
.send-btn:hover :global(svg) {
  transform: none;
}

.inbox-header-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-neutral-500);
}

.inbox-count-badge {
  position: absolute;
  top: -0.5rem;
  right: -0.6rem;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: var(--color-red-300, #dc2626);
  color: white;
  font-size: 0.6rem;
  line-height: 1rem;
  font-weight: 600;
  text-align: center;
}

.show-more-btn {
  display: block;
  margin: 0.25rem auto 0;
  padding: 0.3rem 0.9rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-neutral-300);
  background: transparent;
  color: var(--color-neutral-600);
  font-size: var(--text-xs);
  font-weight: 500;
  cursor: pointer;
}
.show-more-btn:hover {
  background: var(--color-neutral-100);
}

.pending-tag {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: var(--text-xs);
  font-weight: 600;
  background: var(--color-yellow-100, #fef3c7);
  color: var(--color-yellow-700, #b45309);
  white-space: nowrap;
}

.inbox-rows {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
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
.icon-btn-sm.approve {
  color: var(--color-green-600, #16a34a);
  border-color: var(--color-green-300, #86efac);
}
.icon-btn-sm.approve:hover {
  background: var(--color-green-50, #f0fdf4);
}
.icon-btn-sm.reject {
  color: var(--color-red-600, #dc2626);
  border-color: var(--color-red-300, #fca5a5);
}
.icon-btn-sm.reject:hover {
  background: var(--color-red-50, #fef2f2);
}
</style>
