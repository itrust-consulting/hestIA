<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import { addToast } from '$lib/stores/toast';
  import { CLASSIFICATION_LABELS, CLASSIFICATION_OPTIONS } from '$lib/classification';

  type Org = { id: string | number; name: string; abbreviation: string };
  type AccessEntry = { abbr: string; maxClass: number | null };

  type Props = {
    open: boolean;
    onClose: () => void;
    /** Tenants the user can set as owner (moderator: their tenant(s); admin: all tenants) */
    ownerOrgs: Org[];
    /** Tenants available for access grants — only show for admins, empty hides the section */
    accessOrgs?: Org[];
    /** Collection names that already exist (for collision warning) */
    existingCollections?: string[];
    /** Abbreviation to pre-select as owner */
    defaultOwner?: string;
    /** Called after successful creation with the new collection name */
    onSuccess?: (collectionName: string) => void;
  };

  let {
    open,
    onClose,
    ownerOrgs,
    accessOrgs = [],
    existingCollections = [],
    defaultOwner,
    onSuccess,
  }: Props = $props();

  let name = $state('');
  let selectedOwner = $state('');
  let selectedAccess = $state<AccessEntry[]>([]);
  let saving = $state(false);

  $effect(() => {
    if (open) {
      name = '';
      selectedOwner = defaultOwner ?? ownerOrgs[0]?.abbreviation ?? '';
      selectedAccess = [];
    }
  });

  const nameExists = $derived(existingCollections.includes(name.trim()));
  const selectedOwnerOrg = $derived(ownerOrgs.find((o) => o.abbreviation === selectedOwner));
  const availableAccess = $derived(accessOrgs.filter((o) => o.abbreviation !== selectedOwner));

  function toggleAccess(abbr: string) {
    if (selectedAccess.some((e) => e.abbr === abbr)) {
      selectedAccess = selectedAccess.filter((e) => e.abbr !== abbr);
    } else {
      selectedAccess = [...selectedAccess, { abbr, maxClass: null }];
    }
  }

  function setMaxClass(abbr: string, val: string) {
    selectedAccess = selectedAccess.map((e) =>
      e.abbr === abbr ? { ...e, maxClass: val === 'null' ? null : parseInt(val) } : e
    );
  }

  async function handleCreate() {
    if (!name.trim() || !selectedOwnerOrg || nameExists) return;
    saving = true;
    try {
      const createRes = await fetch('/api/admin/collections', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), owner_org_id: selectedOwnerOrg.id }),
      });
      if (!createRes.ok) {
        const d = await createRes.json().catch(() => ({}));
        throw new Error(d.detail ?? `${createRes.status}`);
      }

      await Promise.all(
        selectedAccess.map(({ abbr, maxClass }) => {
          const org = availableAccess.find((o) => o.abbreviation === abbr);
          if (!org) return Promise.resolve();
          return fetch(
            `/api/admin/tenants/${org.id}/collections/${encodeURIComponent(name.trim())}`,
            {
              method: 'PUT',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ role: 'access', max_classification: maxClass }),
            }
          );
        })
      );

      onSuccess?.(name.trim());
      onClose();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to create collection.', 'error');
    } finally {
      saving = false;
    }
  }
</script>

<Modal title="Create Collection" {open} {onClose}>
  <div class="form-stack">
    <label class="field">
      <span>Collection name <span class="req">*</span></span>
      <input
        type="text"
        bind:value={name}
        placeholder="my-collection"
        class:input-warn={nameExists}
      />
      {#if nameExists}
        <p class="warn-text">A collection with this name already exists.</p>
      {/if}
    </label>

    {#if ownerOrgs.length === 1}
      <div class="field">
        <span>Owner</span>
        <div class="owner-display">
          <span class="abbr-chip">{ownerOrgs[0].abbreviation}</span>
          <span class="org-name">{ownerOrgs[0].name}</span>
        </div>
      </div>
    {:else if ownerOrgs.length > 1}
      <label class="field">
        <span>Owner <span class="req">*</span></span>
        <select bind:value={selectedOwner}>
          {#each ownerOrgs as org}
            <option value={org.abbreviation}>{org.name} ({org.abbreviation})</option>
          {/each}
        </select>
      </label>
    {/if}

    {#if availableAccess.length > 0}
      <div class="field">
        <span>Access permissions</span>
        <div class="tenant-list">
          {#each availableAccess as org}
            {@const entry = selectedAccess.find((e) => e.abbr === org.abbreviation)}
            <div class="tenant-option">
              <input
                type="checkbox"
                checked={!!entry}
                onchange={() => toggleAccess(org.abbreviation)}
              />
              <span class="tenant-label">{org.name} <span class="tenant-abbr">({org.abbreviation})</span></span>
              {#if entry}
                <select
                  class="class-cap-select"
                  onchange={(e) => setMaxClass(org.abbreviation, (e.currentTarget as HTMLSelectElement).value)}
                >
                  <option value="null" selected={entry.maxClass === null}>No cap</option>
                  {#each CLASSIFICATION_OPTIONS as lvl}
                    <option value={String(lvl)} selected={entry.maxClass === lvl}>{CLASSIFICATION_LABELS[lvl]}</option>
                  {/each}
                </select>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <svelte:fragment slot="footer">
    <button
      class="btn-primary"
      onclick={handleCreate}
      disabled={saving || !name.trim() || !selectedOwnerOrg || nameExists}
    >
      {saving ? 'Creating…' : 'Create collection'}
    </button>
  </svelte:fragment>
</Modal>

<style>
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}

.field input[type='text'],
.field select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
}
.field input[type='text']:focus,
.field select:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.field input.input-warn { border-color: var(--color-yellow-400); }

.owner-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.65rem;
  background: var(--color-neutral-50);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
}

.abbr-chip {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--color-blue-50);
  color: var(--color-blue-700);
  font-size: var(--text-xs);
  font-weight: 600;
}

.org-name {
  font-size: var(--text-sm);
  color: var(--color-neutral-700);
}

.tenant-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 140px;
  overflow-y: auto;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  padding: 0.375rem 0.5rem;
  background: var(--color-white);
}

.tenant-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--text-sm);
  font-weight: 400;
  padding: 0.15rem 0;
}

.tenant-label { flex: 1; cursor: pointer; }

.class-cap-select {
  padding: 0.2rem 0.4rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  background: var(--color-white);
  color: var(--color-neutral-700);
  flex-shrink: 0;
}
.class-cap-select:focus { outline: none; border-color: var(--color-blue-400); }

.tenant-abbr {
  color: var(--color-neutral-500);
  font-size: var(--text-xs);
}

.warn-text {
  font-size: var(--text-xs);
  color: var(--color-yellow-700);
  background: var(--color-yellow-50);
  border: 1px solid var(--color-yellow-200);
  border-radius: var(--radius-md);
  padding: 0.3rem 0.6rem;
  margin: 0;
}

.req { color: var(--color-red-500); }

.btn-primary {
  background: var(--color-blue-600);
  color: white;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-lg);
  font-weight: 600;
  font-size: var(--text-sm);
  border: none;
  cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
