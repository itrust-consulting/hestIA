<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import type { PageData } from './$types';
  import { addToast } from '$lib/stores/toast';
  import EditIcon from '$lib/components/icons/editIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  const { data }: { data: PageData } = $props();

  type Role = { id: number; name: string; description: string };
  type Org  = { id: number; name: string; abbreviation: string };

  let user = $derived(data.user);
  let allRoles: Role[] = $derived(data.allRoles ?? []);
  let allOrgs:  Org[]  = $derived(data.allOrgs  ?? []);

  const formatDateTime = (ts: number | null) => {
    if (!ts) return 'Never';
    return new Date(ts).toLocaleString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit'
    });
  };

  // ── Profile form ─────────────────────────────────────────────────────────
  let firstName   = $state('');
  let lastName    = $state('');
  let email       = $state('');
  let username    = $state('');
  let expiresAt   = $state('');        // ISO date string for <input type="date">
  let selectedRoleIds = $state<number[]>([]);
  let editing = $state(false);

  function syncFieldsFromUser() {
    firstName = user.first_name ?? '';
    lastName  = user.last_name  ?? '';
    email     = user.email      ?? '';
    username  = user.username   ?? '';
    expiresAt = user.expires_at ? new Date(user.expires_at).toISOString().slice(0, 10) : '';
    selectedRoleIds = (user.roles ?? []).map((r: Role) => r.id);
  }

  $effect(() => { syncFieldsFromUser(); });

  function startEdit() {
    syncFieldsFromUser();
    editing = true;
  }

  function cancelEdit() {
    editing = false;
  }

  let saving = $state(false);

  async function handleSave() {
    saving = true;
    try {
      const res = await fetch(`/api/admin/users/user/${user.id}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name:  lastName.trim(),
          email:      email.trim(),
          username:   username.trim(),
          expires_at: expiresAt ? new Date(expiresAt).getTime() : null,
          role_ids:   selectedRoleIds,
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      editing = false;
      addToast('Changes saved.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to save changes.', 'error');
    } finally {
      saving = false;
    }
  }

  // ── Password reset ────────────────────────────────────────────────────────
  let newPassword   = $state('');
  let confirmPw     = $state('');
  let pwSaving      = $state(false);

  async function handlePasswordReset() {
    if (!newPassword || newPassword !== confirmPw) return;
    pwSaving = true;
    try {
      const res = await fetch(`/api/admin/users/user/${user.id}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ new_password: newPassword }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      newPassword = '';
      confirmPw   = '';
      addToast('Password reset. User must change it on next login.', 'success');
    } catch (e: any) {
      addToast(e.message ?? 'Failed to reset password.', 'error');
    } finally {
      pwSaving = false;
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────────
  let confirmDeleteOpen = $state(false);

  async function deleteUser() {
    const res = await fetch(`/api/admin/users/user/${user.id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete user.');
    goto('/admin/users');
  }

  function toggleRole(id: number) {
    if (selectedRoleIds.includes(id)) {
      selectedRoleIds = selectedRoleIds.filter(r => r !== id);
    } else {
      selectedRoleIds = [...selectedRoleIds, id];
    }
  }

  const pwMismatch = $derived(confirmPw.length > 0 && newPassword !== confirmPw);

  // ── Organisations ─────────────────────────────────────────────────────────
  let userOrgs = $state<{ id: number; name: string; abbr: string }[]>([]);

  $effect(() => {
    userOrgs = (user.orgs ?? []).map((o: any) => ({ id: o.id, name: o.name, abbr: o.abbr }));
  });

  const availableOrgs = $derived(allOrgs.filter(o => !userOrgs.some(uo => uo.id === o.id)));

  let addOrgId = $state<number | ''>('');
  let orgSaving = $state(false);

  async function addOrg() {
    if (!addOrgId || orgSaving) return;
    orgSaving = true;
    try {
      const res = await fetch(`/api/admin/organizations/${addOrgId}/members/${user.id}`, { method: 'POST' });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      const org = allOrgs.find(o => o.id === addOrgId);
      if (org) userOrgs = [...userOrgs, { id: org.id, name: org.name, abbr: org.abbreviation }];
      addOrgId = '';
      addToast('User added to organisation.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to add to organisation.', 'error');
    } finally {
      orgSaving = false;
    }
  }

  async function removeOrg(orgId: number) {
    try {
      const res = await fetch(`/api/admin/organizations/${orgId}/members/${user.id}`, { method: 'DELETE' });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      userOrgs = userOrgs.filter(o => o.id !== orgId);
      addToast('User removed from organisation.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to remove from organisation.', 'error');
    }
  }
</script>

<div class="admin-content">
  <!-- ── Header ─────────────────────────────────────────────────────────── -->
  <div class="page-header">
    <div class="page-header-left">
      <div class="avatar">{user.username?.charAt(0).toUpperCase()}</div>
      <div>
        <h1 class="title">{user.username}</h1>
        <span class="auth-badge">{user.auth_source ?? 'local'}</span>
      </div>
    </div>
  </div>

  <!-- ── Profile section ───────────────────────────────────────────────── -->
  <section class="card">
    <div class="section-header">
      <h2 class="section-title">Profile</h2>
      {#if !editing}
        <button class="icon-btn" aria-label="Edit" use:tooltip={"Edit"} onclick={startEdit}>
          <EditIcon />
        </button>
      {/if}
    </div>

    {#if editing}
      <div class="form-grid">
        <label class="field">
          <span>First name</span>
          <input type="text" bind:value={firstName} />
        </label>
        <label class="field">
          <span>Last name</span>
          <input type="text" bind:value={lastName} />
        </label>
        <label class="field">
          <span>Email</span>
          <input type="email" bind:value={email} />
        </label>
        <label class="field">
          <span>Expires</span>
          <input type="date" bind:value={expiresAt} />
          {#if expiresAt}
            <button class="clear-btn" onclick={() => (expiresAt = '')}>Never expires</button>
          {/if}
        </label>
      </div>

      <div class="field" style="margin-top:1.25rem">
        <span>Roles</span>
        <div class="role-list">
          {#each allRoles as role}
            <label class="role-option">
              <input type="checkbox" checked={selectedRoleIds.includes(role.id)}
                onchange={() => toggleRole(role.id)} />
              <span class="role-name">{role.name}</span>
              {#if role.description}<span class="role-desc">{role.description}</span>{/if}
            </label>
          {/each}
        </div>
      </div>

      <div class="card-footer">
        <button class="btn-secondary" onclick={cancelEdit} disabled={saving}>Cancel</button>
        <button class="btn-primary" onclick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    {:else}
      <div class="profile-fields">
        <div class="profile-row">
          <div class="info-item">
            <span class="info-label">First name</span>
            <span class="info-value">{user.first_name || '—'}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Last name</span>
            <span class="info-value">{user.last_name || '—'}</span>
          </div>
        </div>
        <div class="profile-row">
          <div class="info-item">
            <span class="info-label">Email</span>
            <span class="info-value">{user.email}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Expires</span>
            <span class="info-value">{user.expires_at ? formatDateTime(user.expires_at) : 'Never'}</span>
          </div>
        </div>
        <div class="info-item">
          <span class="info-label">Roles</span>
          {#if (user.roles ?? []).length > 0}
            <div class="role-chips">
              {#each user.roles as role}
                <span class="role-chip">{role.name}</span>
              {/each}
            </div>
          {:else}
            <span class="info-value">No roles assigned.</span>
          {/if}
        </div>
      </div>
    {/if}
  </section>

  <!-- ── Additional info section ──────────────────────────────────────── -->
  <section class="card">
    <h2 class="section-title">Activity</h2>
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">Last Login</span>
        <span class="info-value">{formatDateTime(user.last_login_at)}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Activity</span>
        <span class="info-value">{user.conversation_count} conversation{user.conversation_count === 1 ? '' : 's'} · {user.message_count} message{user.message_count === 1 ? '' : 's'}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Failed Logins (7d)</span>
        <span class="info-value">
          {#if user.failed_logins_7d > 0}
            <span class="failed-logins-badge">{user.failed_logins_7d}</span>
          {:else}
            0
          {/if}
        </span>
      </div>
    </div>
  </section>

  <!-- ── Organisations section ────────────────────────────────────────── -->
  <section class="card">
    <h2 class="section-title">Organisations</h2>

    {#if userOrgs.length > 0}
      <div class="org-list">
        {#each userOrgs as org (org.id)}
          <div class="org-item">
            <span class="org-abbr">{org.abbr}</span>
            <span class="org-name">{org.name}</span>
            <button class="org-remove" onclick={() => removeOrg(org.id)} aria-label="Remove from organisation" use:tooltip={"Remove from organisation"}>×</button>
          </div>
        {/each}
      </div>
    {:else}
      <p class="section-note">No organisation memberships.</p>
    {/if}

    {#if availableOrgs.length > 0}
      <div class="org-add-row">
        <select bind:value={addOrgId} class="org-select">
          <option value="">Select organisation…</option>
          {#each availableOrgs as org (org.id)}
            <option value={org.id}>{org.name} ({org.abbreviation})</option>
          {/each}
        </select>
        <button class="btn-primary" onclick={addOrg} disabled={!addOrgId || orgSaving}>
          {orgSaving ? 'Adding…' : 'Add'}
        </button>
      </div>
    {/if}
  </section>

  <!-- ── Password reset section ────────────────────────────────────────── -->
  <section class="card">
    <h2 class="section-title">Reset Password</h2>
    <p class="section-note">Sets a new temporary password. The user will be prompted to change it on next login.</p>
    <div class="form-grid">
      <label class="field">
        <span>New password</span>
        <input type="password" bind:value={newPassword} autocomplete="new-password" />
      </label>
      <label class="field">
        <span>Confirm password</span>
        <input type="password" bind:value={confirmPw} class:input-error={pwMismatch} autocomplete="new-password" />
        {#if pwMismatch}<span class="field-error">Passwords do not match.</span>{/if}
      </label>
    </div>

    <div class="card-footer">
      <button class="btn-primary" onclick={handlePasswordReset}
        disabled={pwSaving || !newPassword || pwMismatch}>
        {pwSaving ? 'Saving…' : 'Reset password'}
      </button>
    </div>
  </section>

  <!-- ── Danger zone ────────────────────────────────────────────────────── -->
  <section class="card danger-card">
    <div class="danger-row">
      <div>
        <p class="danger-title">Delete this user</p>
        <p class="danger-desc">
          Permanently delete <strong>{user.username}</strong>.
        </p>
      </div>
      <button class="danger-btn" onclick={() => (confirmDeleteOpen = true)}>Delete user</button>
    </div>
  </section>
</div>

<ConfirmDeleteModal
  open={confirmDeleteOpen}
  title="Delete User"
  onClose={() => (confirmDeleteOpen = false)}
  onConfirm={deleteUser}
  successMessage="User deleted."
>
  <p>Permanently delete <strong>{user.username}</strong>?</p>
  <p> This cannot be undone.</p>
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

/* ── Header ── */
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
.title { font-size: var(--text-2xl); font-weight: 700; margin-bottom: 0.2rem; }
.auth-badge {
  display: inline-block;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: var(--color-neutral-100);
  color: var(--color-neutral-600);
}
/* ── Cards ── */
.card {
  background: var(--color-neutral-50);
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
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
.section-title {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-neutral-800);
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.section-note {
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
  margin-bottom: 1rem;
  margin-top: -0.5rem;
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

.role-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.role-chip {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
}

/* ── Form ── */
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
.field input[type="text"],
.field input[type="email"],
.field input[type="password"],
.field input[type="date"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
}
.field input:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.input-error { border-color: var(--color-red-400) !important; }
.field-error { font-size: var(--text-xs); color: var(--color-red-600); font-weight: 400; }
.clear-btn {
  align-self: flex-start;
  font-size: var(--text-xs);
  color: var(--color-neutral-500);
  background: none; border: none; cursor: pointer; padding: 0; text-decoration: underline;
}
.clear-btn:hover { color: var(--color-neutral-800); }

/* ── Roles ── */
.role-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.role-option {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.4rem 0.5rem;
  border-radius: var(--radius-md);
  cursor: pointer;
}
.role-option:hover { background: var(--color-neutral-50); }
.role-name { font-size: var(--text-sm); font-weight: 500; }
.role-desc { font-size: var(--text-xs); color: var(--color-neutral-500); margin-left: 0.25rem; }


/* ── Additional info ── */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 1rem;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.info-label {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-500);
}
.info-value {
  font-size: var(--text-sm);
  color: var(--color-neutral-800);
}

/* ── Read-only profile view ── */
.profile-fields {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.profile-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}

.failed-logins-badge {
  display: inline-block;
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 600;
}

/* ── Organisations ── */
.org-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 1rem;
}
.org-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.6rem;
  border-radius: var(--radius-md);
  background: var(--color-neutral-50);
}
.org-abbr {
  font-size: var(--text-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--color-blue-100);
  color: var(--color-blue-700);
  flex-shrink: 0;
}
.org-name { font-size: var(--text-sm); font-weight: 500; flex: 1; }
.org-remove {
  background: none; border: none;
  font-size: 1.1rem; line-height: 1;
  color: var(--color-neutral-400);
  cursor: pointer; padding: 0 0.25rem; flex-shrink: 0;
}
.org-remove:hover { color: var(--color-red-500); }
.org-add-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.org-select {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
}
.org-select:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

/* ── Buttons ── */
.btn-primary {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: var(--color-neutral-100); color: var(--color-neutral-800);
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-size: var(--text-sm); font-weight: 500; border: 1px solid var(--color-neutral-300); cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { background: var(--color-neutral-200); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.danger-btn {
  background: var(--color-red-600); color: white;
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
  white-space: nowrap;
}
.danger-btn:hover:not(:disabled) { background: var(--color-red-700); }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }

</style>
