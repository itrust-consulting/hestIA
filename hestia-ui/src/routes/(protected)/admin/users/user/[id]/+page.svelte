<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import type { PageData } from './$types';
  import { addToast } from '$lib/stores/toast';

  const { data }: { data: PageData } = $props();

  type Role = { id: number; name: string; description: string };
  type Org  = { id: number; name: string; abbreviation: string };

  let user = $derived(data.user);
  let allRoles: Role[] = $derived(data.allRoles ?? []);
  let allOrgs:  Org[]  = $derived(data.allOrgs  ?? []);

  // ── Profile form ─────────────────────────────────────────────────────────
  let firstName   = $state('');
  let lastName    = $state('');
  let email       = $state('');
  let username    = $state('');
  let expiresAt   = $state('');        // ISO date string for <input type="date">
  let selectedRoleIds = $state<number[]>([]);

  $effect(() => {
    firstName = user.first_name ?? '';
    lastName  = user.last_name  ?? '';
    email     = user.email      ?? '';
    username  = user.username   ?? '';
    expiresAt = user.expires_at ? new Date(user.expires_at).toISOString().slice(0, 10) : '';
    selectedRoleIds = (user.roles ?? []).map((r: Role) => r.id);
  });

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
    <div class="danger-zone">
      <button class="btn-danger" onclick={() => (confirmDeleteOpen = true)}>Delete User</button>
    </div>
  </div>

  <!-- ── Profile section ───────────────────────────────────────────────── -->
  <section class="card">
    <h2 class="section-title">Profile</h2>
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
        <span>Username</span>
        <input type="text" bind:value={username} />
      </label>
      <label class="field">
        <span>Expires</span>
        <input type="date" bind:value={expiresAt} />
        {#if expiresAt}
          <button class="clear-btn" onclick={() => (expiresAt = '')}>Never expires</button>
        {/if}
      </label>
    </div>

    <h2 class="section-title" style="margin-top:1.5rem">Roles</h2>
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

    <div class="card-footer">
      <button class="btn-primary" onclick={handleSave} disabled={saving}>
        {saving ? 'Saving…' : 'Save changes'}
      </button>
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
            <button class="org-remove" onclick={() => removeOrg(org.id)} title="Remove from organisation">×</button>
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
.danger-zone { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }

/* ── Cards ── */
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
.section-note {
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
  margin-bottom: 1rem;
  margin-top: -0.5rem;
}
.card-footer {
  margin-top: 1.25rem;
  display: flex;
  justify-content: flex-end;
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

.btn-danger {
  background: var(--color-red-600); color: white;
  padding: 0.4rem 0.9rem; border-radius: var(--radius-md);
  font-size: var(--text-sm); font-weight: 500; border: none; cursor: pointer;
}
.btn-danger:hover:not(:disabled) { background: var(--color-red-700); }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

</style>
