<script lang="ts">
  import InfoIcon from './icons/infoIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';
  import { DOCUMENT_CLASSIFICATION_OPTIONS } from '$lib/classification';
  import { LANGUAGE_OPTIONS } from '$lib/language';
  import { addToast } from '$lib/stores/toast';
  import {
    META_FIELDS, RESERVED_METADATA_KEYS,
    customFieldKeyError as _customFieldKeyError, toCustomFieldsRecord,
    type CustomField,
  } from '$lib/upload/documentMetadata';

  type Props = {
    collectionName: string;
    sourceUri: string;
    docInfo: Record<string, string>;
    /** Called after a successful save, with the metadata that was saved. */
    onSaved?: (metadata: Record<string, string>) => void;
  };

  let { collectionName, sourceUri, docInfo, onSaved }: Props = $props();

  let mode: 'view' | 'edit' = $state('view');
  let metadata: Record<string, string> = $state({});
  let customFields: CustomField[] = $state([]);
  let saving = $state(false);

  function loadFromDocInfo() {
    const info = docInfo ?? {};
    metadata = Object.fromEntries(
      [...META_FIELDS.map((f) => f.key), 'classification', 'lang'].map((key) => [key, info[key] ?? ''])
    );
    customFields = Object.entries(info)
      .filter(([key]) => !RESERVED_METADATA_KEYS.includes(key))
      .map(([key, value]) => ({ key, value: String(value ?? '') }));
  }

  // Re-derive whenever the underlying doc_info changes (e.g. after a save
  // triggers a page reload), so the view mode always reflects the server.
  $effect(() => {
    docInfo;
    loadFromDocInfo();
  });

  function customFieldKeyError(key: string, index: number): string | null {
    return _customFieldKeyError(customFields, key, index);
  }

  const hasCustomFieldErrors = $derived(
    customFields.some((f, i) => customFieldKeyError(f.key, i) !== null)
  );

  const classificationLabel = $derived(
    DOCUMENT_CLASSIFICATION_OPTIONS.find((o) => o.value === metadata.classification)?.label ?? '—'
  );

  const languageLabel = $derived(
    LANGUAGE_OPTIONS.find((o) => o.value === metadata.lang)?.label ?? '—'
  );

  function addCustomField() {
    customFields = [...customFields, { key: '', value: '' }];
  }

  function removeCustomField(index: number) {
    customFields = customFields.filter((_, i) => i !== index);
  }

  function startEdit() {
    mode = 'edit';
  }

  function cancelEdit() {
    loadFromDocInfo();
    mode = 'view';
  }

  async function handleSave() {
    saving = true;
    try {
      const merged = { ...metadata, ...toCustomFieldsRecord(customFields) };
      const res = await fetch(
        `/api/admin/collections/${encodeURIComponent(collectionName)}/documents`,
        {
          method: 'PATCH',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ source_uri: sourceUri, metadata: merged }),
        },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      addToast('Metadata updated.', 'success');
      mode = 'view';
      onSaved?.(merged);
    } catch {
      addToast('Failed to update metadata.', 'error');
    } finally {
      saving = false;
    }
  }
</script>

<section class="card">
  <div class="section-header">
    <h2 class="section-title">Metadata</h2>
    {#if mode === 'view'}
      <button class="btn-secondary" onclick={startEdit}>Edit</button>
    {/if}
  </div>

  {#if mode === 'view'}
    <div class="form-grid">
      <div class="view-field field-full">
        <span class="view-label">Title</span>
        <span class="view-value">{metadata.title || '—'}</span>
      </div>
      <div class="view-field">
        <span class="view-label">Author</span>
        <span class="view-value">{metadata.author || '—'}</span>
      </div>
      <div class="view-field">
        <span class="view-label">Publisher</span>
        <span class="view-value">{metadata.publisher || '—'}</span>
      </div>
      <div class="view-field">
        <span class="view-label">Classification</span>
        <span class="view-value">{classificationLabel}</span>
      </div>
      <div class="view-field">
        <span class="view-label">Language</span>
        <span class="view-value">{languageLabel}</span>
      </div>
      <div class="view-field">
        <span class="view-label">Version</span>
        <span class="view-value">{metadata.version || '—'}</span>
      </div>
      <div class="view-field">
        <span class="view-label">Year</span>
        <span class="view-value">{metadata.year || '—'}</span>
      </div>
      {#each customFields as field}
        <div class="view-field">
          <span class="view-label">{field.key}</span>
          <span class="view-value">{field.value || '—'}</span>
        </div>
      {/each}
    </div>
  {:else}
    <div class="form-grid">
      <label class="field field-full">
        <span>Title</span>
        <input type="text" bind:value={metadata.title} placeholder="—" />
      </label>
      <label class="field">
        <span>Author</span>
        <input type="text" bind:value={metadata.author} placeholder="—" />
      </label>
      <label class="field">
        <span>Publisher</span>
        <input type="text" bind:value={metadata.publisher} placeholder="—" />
      </label>
      <label class="field">
        <span>Classification <span class="req">*</span>
          <span class="info-icon" use:tooltip={"Document classification set for retrieval."}><InfoIcon/></span>
        </span>
        <select bind:value={metadata.classification} required>
          <option value="" disabled>Select…</option>
          {#each DOCUMENT_CLASSIFICATION_OPTIONS as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </label>
      <label class="field">
        <span>Language
          <span class="info-icon" use:tooltip={"Stored for reference only — changing it does not re-stem already-indexed chunks."}><InfoIcon/></span>
        </span>
        <select bind:value={metadata.lang}>
          <option value="">—</option>
          {#each LANGUAGE_OPTIONS as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </label>
      <label class="field">
        <span>Version</span>
        <input type="text" bind:value={metadata.version} placeholder="—" />
      </label>
      <label class="field">
        <span>Year</span>
        <input type="text" bind:value={metadata.year} placeholder="—" />
      </label>
    </div>

    <div class="custom-fields">
      <div class="custom-fields-actions">
        <button type="button" class="link-btn" onclick={addCustomField}>+ Add field</button>
      </div>
      {#if customFields.length}
        <div class="custom-fields-list">
          {#each customFields as field, i}
            {@const error = customFieldKeyError(field.key, i)}
            <div class="custom-field-row">
              <input type="text" placeholder="Field name" bind:value={field.key} class:input-error={!!error} />
              <input type="text" placeholder="Value" bind:value={field.value} />
              <button type="button" class="remove-btn" onclick={() => removeCustomField(i)} aria-label="Remove field">×</button>
            </div>
            {#if error}<span class="field-error">{error}</span>{/if}
          {/each}
        </div>
      {/if}
    </div>

    <div class="card-footer">
      <button class="btn-secondary" onclick={cancelEdit} disabled={saving}>Cancel</button>
      <button class="btn-primary" onclick={handleSave} disabled={saving || !metadata.classification || hasCustomFieldErrors}>
        {saving ? 'Saving…' : 'Save changes'}
      </button>
    </div>
  {/if}
</section>

<style>
.card {
  background: var(--color-neutral-50);
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-neutral-200);
}
.section-title { font-size: var(--text-base); font-weight: 700; color: var(--color-neutral-800); margin: 0; }

/* ── View mode ── */
.view-field { display: flex; flex-direction: column; gap: 0.15rem; }
.view-label { font-size: var(--text-xs); color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: 0.03em; }
.view-value { font-size: var(--text-sm); color: var(--color-neutral-900); word-break: break-word; }

/* ── Edit mode: form ── */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.875rem 1.25rem;
}
.field-full { grid-column: 1 / -1; }
.field {
  display: flex; flex-direction: column; gap: 0.3rem;
  font-size: var(--text-sm); font-weight: 500; color: var(--color-neutral-700);
}
.field input[type="text"],
.field select {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-white);
}
.field input[type="text"]:focus,
.field select:focus {
  outline: none; border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.req { color: var(--color-red-500); }
.info-icon { display: inline-block; vertical-align: middle; margin-left: 0.25rem; cursor: pointer; }

/* ── Custom fields ── */
.custom-fields { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1.25rem; }
.custom-fields-actions { display: flex; justify-content: flex-end; font-size: smaller; }
.custom-fields-list { display: flex; flex-direction: column; gap: 0.35rem; }
.custom-field-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.5rem; align-items: center; }
.custom-field-row input {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-white);
}
.custom-field-row input.input-error { border-color: var(--color-red-400); }
.remove-btn {
  width: 1.75rem; height: 1.75rem; border-radius: var(--radius-md);
  border: 1px solid var(--color-neutral-200); background: var(--color-neutral-50);
  color: var(--color-neutral-500); cursor: pointer; font-size: var(--text-md); line-height: 1;
}
.remove-btn:hover { background: var(--color-red-50); color: var(--color-red-700); border-color: var(--color-red-200); }
.field-error { font-size: var(--text-xs); color: var(--color-red-700); margin-top: -0.15rem; }
.link-btn { background: none; border: none; color: var(--color-blue-600); cursor: pointer; padding: 0; font-size: inherit; text-decoration: underline; }

/* ── Buttons ── */
.card-footer { margin-top: 1.25rem; display: flex; justify-content: flex-end; gap: 0.5rem; }
.btn-primary {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
  font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  background: var(--color-neutral-100); color: var(--color-neutral-700);
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  font-size: var(--text-sm); font-weight: 500; border: 1px solid var(--color-neutral-200); cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { background: var(--color-neutral-200); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
