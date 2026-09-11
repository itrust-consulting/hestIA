<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import InfoIcon from '../icons/infoIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';
  import { enqueueUpload, createBatchToast } from '$lib/stores/uploadQueue';
  import { fromFileList, type SelectedFile } from '$lib/upload/folderSelect';
  import { sha256Hex } from '$lib/upload/hash';
  import { DOCUMENT_CLASSIFICATION_OPTIONS } from '$lib/classification';
  import { LANGUAGE_OPTIONS } from '$lib/language';

  type Props = {
    open: boolean;
    onClose: () => void;
    collectionName: string;
    defaultTenants?: string[];
    onSuccess?: () => void;
  };

  let { open, onClose, collectionName, defaultTenants = [], onSuccess }: Props = $props();

  type SyncItem = {
    relPath: string;
    status: 'pending' | 'uploading' | 'done' | 'error';
    error?: string;
    duplicateOf?: string;
  };
  type DeleteItem = {
    sourceUri: string;
    status: 'pending' | 'deleting' | 'done' | 'error';
    error?: string;
  };

  let phase = $state<'pick' | 'review' | 'diffing' | 'classify' | 'syncing' | 'confirmDelete' | 'done'>('pick');
  let selected: SelectedFile[] = $state([]);
  let syncId = $state('');

  let addedItems   = $state<SyncItem[]>([]);
  let modifiedItems = $state<SyncItem[]>([]);
  let deleteItems  = $state<DeleteItem[]>([]);
  let unmodifiedCount = $state(0);
  let lastSyncedAt: number | null = $state(null);
  let hashByPath: Map<string, string> = new Map();

  // Per-document classification, keyed by relPath. Required for every added
  // or modified document before syncing can proceed.
  let classificationByPath: Record<string, string> = $state({});
  let bulkClassification = $state('public');

  // Per-document stemmer language, keyed by relPath. Defaults to English for
  // every changed document, matching the hardcoded value sent previously.
  // Also required before syncing can proceed.
  let languageByPath: Record<string, string> = $state({});
  let bulkLanguage = $state('english');

  // Chunking config applies once to the whole sync run, not per-file --
  // matches how tenants are already applied uniformly here.
  let syncChunkingStrategy = $state('auto');
  let syncMaxChars: number | undefined = $state(undefined);
  let syncMaxDepth: number | undefined = $state(undefined);

  const hasMissingRequiredFields = $derived(
    [...addedItems, ...modifiedItems].some(
      (item) => !classificationByPath[item.relPath] || !languageByPath[item.relPath]
    )
  );

  function slugify(name: string): string {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'sync';
  }

  // Deterministic per (collection, folder name) so re-syncing the same folder later
  // reuses the same sync_id and correctly diffs against what was synced before.
  // Falls back to a fresh id if localStorage is unavailable (e.g. private browsing) —
  // that just means the next sync of that folder starts fresh instead of incrementally,
  // never destructively, since a missing prior manifest only ever looks like "everything added".
  function getOrCreateSyncId(folderName: string): string {
    const slug = slugify(folderName);
    const key = `sync-folder-id:${collectionName}:${slug}`;
    try {
      const existing = localStorage.getItem(key);
      if (existing) return existing;
      const generated = `${slug}-${crypto.randomUUID().slice(0, 8)}`;
      localStorage.setItem(key, generated);
      return generated;
    } catch {
      return `${slug}-${crypto.randomUUID().slice(0, 8)}`;
    }
  }

  export function openModal() {
    phase = 'pick';
    selected = [];
    syncId = '';
    addedItems = [];
    modifiedItems = [];
    deleteItems = [];
    unmodifiedCount = 0;
    lastSyncedAt = null;
    hashByPath = new Map();
    classificationByPath = {};
    bulkClassification = 'public';
    languageByPath = {};
    bulkLanguage = 'english';
    syncChunkingStrategy = 'auto';
    syncMaxChars = undefined;
    syncMaxDepth = undefined;
  }

  async function markSynced() {
    try {
      await fetch(`/api/admin/collections/${encodeURIComponent(collectionName)}/sync/complete`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ sync_id: syncId }),
      });
    } catch { /* best-effort — a failed timestamp update shouldn't block the sync flow */ }
  }

  function closeModal() {
    openModal();
    onClose();
  }

  function onFolderInputChange(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const fileList = input.files;
    input.value = '';
    if (!fileList || !fileList.length) return;
    applySelection(fromFileList(fileList));
  }

  function applySelection(files: SelectedFile[]) {
    if (!files.length) return;
    selected = files;
    syncId = getOrCreateSyncId(files[0].relPath.split('/')[0]);
    lastSyncedAt = null;
    classificationByPath = {};
    bulkClassification = 'public';
    languageByPath = {};
    bulkLanguage = 'english';
    computeDiff();
  }

  function applyBulkValues() {
    if (!bulkClassification || !bulkLanguage) return;
    for (const item of [...addedItems, ...modifiedItems]) {
      classificationByPath[item.relPath] = bulkClassification;
      languageByPath[item.relPath] = bulkLanguage;
    }
  }

  async function computeDiff() {
    phase = 'diffing';

    hashByPath = new Map();
    const manifest: { path: string; checksum: string }[] = [];
    for (const s of selected) {
      const checksum = await sha256Hex(s.file);
      hashByPath.set(s.relPath, checksum);
      manifest.push({ path: s.relPath, checksum });
    }

    const res = await fetch(`/api/admin/collections/${encodeURIComponent(collectionName)}/sync/diff`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ sync_id: syncId, manifest }),
    });
    if (!res.ok) {
      phase = 'review';
      return;
    }
    const diff: {
      added: string[]; modified: string[]; deleted: string[]; unmodified_count: number;
      last_synced_at: number | null; previous_classifications: Record<string, string>;
    } = await res.json();

    unmodifiedCount = diff.unmodified_count;
    addedItems      = diff.added.map(relPath => ({ relPath, status: 'pending' as const }));
    modifiedItems   = diff.modified.map(relPath => ({ relPath, status: 'pending' as const }));
    deleteItems     = diff.deleted.map(sourceUri => ({ sourceUri, status: 'pending' as const }));
    lastSyncedAt    = diff.last_synced_at;

    // Modified documents already have a classification from their last sync —
    // pre-fill it rather than defaulting to "auto-detect" for a file whose
    // content only changed slightly. Added files have no prior classification.
    for (const [relPath, classification] of Object.entries(diff.previous_classifications ?? {})) {
      classificationByPath[relPath] = classification;
    }
    for (const item of [...addedItems, ...modifiedItems]) {
      languageByPath[item.relPath] = 'english';
    }

    if (addedItems.length + modifiedItems.length > 0) {
      phase = 'classify';
    } else {
      await finishAfterUpload();
    }
  }

  async function confirmClassifications() {
    phase = 'syncing';
    await uploadChanged();
    await finishAfterUpload();
  }

  async function finishAfterUpload() {
    if (deleteItems.length > 0) {
      phase = 'confirmDelete';
    } else {
      await markSynced();
      phase = 'done';
    }
  }

  async function uploadChanged() {
    const byPath = new Map(selected.map(s => [s.relPath, s.file]));
    const jobs = [...addedItems, ...modifiedItems];
    if (!jobs.length) return;
    const batchId = createBatchToast(collectionName, jobs.length);

    await Promise.all(jobs.map(item => new Promise<void>(resolve => {
      const file = byPath.get(item.relPath);
      const contentHash = hashByPath.get(item.relPath);
      if (!file || !contentHash) { resolve(); return; }
      const classification = classificationByPath[item.relPath];
      item.status = 'uploading';
      enqueueUpload({
        id: crypto.randomUUID(),
        file,
        relPath: item.relPath,
        collection: collectionName,
        tenants: defaultTenants,
        metadata: classification ? { classification } : {},
        language: languageByPath[item.relPath] || 'english',
        chunkingStrategy: syncChunkingStrategy,
        maxChars: syncMaxChars,
        maxDepth: syncMaxDepth,
        syncId,
        contentHash,
        onDone: (_n_chunks, info) => {
          item.status = 'done';
          if (info?.deduped) item.duplicateOf = info.duplicateOf;
          resolve();
        },
        onError: (err) => { item.status = 'error'; item.error = err; resolve(); },
      }, batchId);
    })));
  }

  async function confirmDeletes() {
    phase = 'syncing';
    await Promise.all(deleteItems.map(async item => {
      item.status = 'deleting';
      try {
        const res = await fetch(
          `/api/admin/collections/${encodeURIComponent(collectionName)}/documents?source_uri=${encodeURIComponent(item.sourceUri)}`,
          { method: 'DELETE' },
        );
        if (!res.ok) throw new Error(`${res.status}`);
        item.status = 'done';
      } catch (err: any) {
        item.status = 'error';
        item.error = err.message ?? 'Delete failed';
      }
    }));
    await markSynced();
    phase = 'done';
  }

  async function skipDeletes() {
    await markSynced();
    phase = 'done';
  }

  function finishSync() {
    closeModal();
    onSuccess?.();
  }
</script>

<Modal title="Sync Folder" {open} onClose={closeModal} wide={true} closeLabel="Cancel">
  {#if phase === 'pick'}
    <div class="field">
      <span>Collection</span>
      <span class="collection-name-display">{collectionName}</span>
    </div>
    <label class="field">
      <span>Select a folder to sync</span>
      <input type="file" multiple {...{ webkitdirectory: true }} onchange={onFolderInputChange} />
    </label>

    <details class="advanced-settings">
      <summary>Advanced settings</summary>

      <div class="field-row">
        <label class="field">
          <span>Chunking
            <span class="info-icon" use:tooltip={"How each document is split for retrieval. Auto uses section headings when present, otherwise falls back to paragraph/table-based chunking. Applies to every file in this sync."}><InfoIcon/></span>
          </span>
          <select bind:value={syncChunkingStrategy}>
            <option value="auto">Auto (recommended)</option>
            <option value="section">Sections only (by heading)</option>
            <option value="block">Paragraphs &amp; tables</option>
          </select>
        </label>
      </div>

      <div class="field-row">
        <label class="field">
          <span>Max chunk size
            <span class="info-icon" use:tooltip={"Maximum characters per chunk before it's split further. Leave blank to use the default (100,000)."}><InfoIcon/></span>
          </span>
          <input type="number" min="200" max="500000" step="100" placeholder="100,000 (default)" bind:value={syncMaxChars} />
        </label>
        <label class="field">
          <span>Section depth
            <span class="info-icon" use:tooltip={"How many heading levels (# through ######) start a new section. Only applies when splitting by headings, not to \"Paragraphs & tables\". Leave blank to use the default (5)."}><InfoIcon/></span>
          </span>
          <input type="number" min="1" max="6" step="1" placeholder="5 (default)" disabled={syncChunkingStrategy === 'block'} bind:value={syncMaxDepth} />
        </label>
      </div>
    </details>

  {:else if phase === 'review'}
    <p class="mode-intro">{selected.length} document(s) found:</p>
    <div class="batch-summary">
      {#each selected as s}
        <div class="batch-row">
          <span class="batch-filename">{s.relPath}</span>
        </div>
      {/each}
    </div>

  {:else if phase === 'diffing'}
    <div class="scan-status">
      <div class="scan-radar" aria-hidden="true">
        <div class="scan-radar-dot"></div>
      </div>
      <p class="mode-intro">Scanning…</p>
    </div>

  {:else if phase === 'classify' || phase === 'syncing' || phase === 'confirmDelete' || phase === 'done'}
    <p class="mode-intro">
      {#if lastSyncedAt}Last synced: {new Date(lastSyncedAt * 1000).toLocaleString()}
      {/if}
    </p>
    <p class="mode-intro">
      {addedItems.length} added, {modifiedItems.length} modified, {deleteItems.length} deleted, {unmodifiedCount} unchanged.
    </p>

    {#if phase === 'classify'}
      <div class="review-header-row">
        <div class="column-header">Language<span class="req">*</span></div>
        <div class="column-header">Classification<span class="req">*</span></div>
      </div>
      <div class="bulk-classify">
        <button class="secondary-btn" disabled={!bulkClassification || !bulkLanguage} onclick={applyBulkValues}>
          Apply to all
        </button>
        <select class="classification-select" bind:value={bulkLanguage}>
          {#each LANGUAGE_OPTIONS as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
        <select class="classification-select" bind:value={bulkClassification}>
          {#each DOCUMENT_CLASSIFICATION_OPTIONS as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </div>
    {/if}

    {#snippet changedRow(item: SyncItem)}
      <div class="batch-row" class:done={item.status === 'done'} class:error={item.status === 'error'}>
        <span class="batch-filename">{item.relPath}</span>
        {#if phase === 'classify'}
          <select class="classification-select" bind:value={languageByPath[item.relPath]} required>
            {#each LANGUAGE_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
          <select class="classification-select" bind:value={classificationByPath[item.relPath]} required>
            {#each DOCUMENT_CLASSIFICATION_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        {:else}
          <span class="batch-file-status">
            {#if item.status === 'uploading'}Uploading…
            {:else if item.status === 'done' && item.duplicateOf}Duplicate of {item.duplicateOf}
            {:else if item.status === 'done'}Done
            {:else if item.status === 'error'}<span class="error-text">{item.error}</span>
            {:else}Pending{/if}
          </span>
        {/if}
      </div>
    {/snippet}

    {#if addedItems.length}
      <p class="group-label">Added ({addedItems.length})</p>
      <div class="batch-summary">
        {#each addedItems as item}
          {@render changedRow(item)}
        {/each}
      </div>
    {/if}

    {#if modifiedItems.length}
      <p class="group-label">Modified ({modifiedItems.length})</p>
      <div class="batch-summary">
        {#each modifiedItems as item}
          {@render changedRow(item)}
        {/each}
      </div>
    {/if}

    {#if deleteItems.length}
      <p class="group-label">Deleted ({deleteItems.length})</p>
      <div class="batch-summary">
        {#each deleteItems as item}
          <div class="batch-row" class:done={item.status === 'done'} class:error={item.status === 'error'}>
            <span class="batch-filename">{item.sourceUri}</span>
            <span class="batch-file-status">
              {#if item.status === 'deleting'}Removing…
              {:else if item.status === 'done'}Removed
              {:else if item.status === 'error'}<span class="error-text">{item.error}</span>
              {:else}Pending removal{/if}
            </span>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <svelte:fragment slot="footer">
    {#if phase === 'review'}
      <button class="action-btn" onclick={computeDiff}>Start sync</button>
    {:else if phase === 'classify'}
      <button class="action-btn" onclick={confirmClassifications} disabled={hasMissingRequiredFields}>
        Upload {addedItems.length + modifiedItems.length} document(s)
      </button>
    {:else if phase === 'syncing'}
      <button class="action-btn" disabled>
        <svg class="btn-spinner" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <circle class="track" cx="12" cy="12" r="9" />
          <circle class="fill" cx="12" cy="12" r="9" stroke-dasharray="14.14 42.41" transform="rotate(-90 12 12)" />
        </svg>
        Syncing
      </button>
    {:else if phase === 'confirmDelete'}
      <button class="secondary-btn" onclick={skipDeletes}>Skip removal</button>
      <button class="action-btn" onclick={confirmDeletes}>Remove {deleteItems.length} document(s)</button>
    {:else if phase === 'done'}
      <button class="action-btn" onclick={finishSync}>Finish sync</button>
    {/if}
  </svelte:fragment>
</Modal>

<style>
.collection-name-display {
  font-size: var(--text-sm); font-weight: 600; color: var(--color-neutral-800);
  padding: 0.4rem 0.65rem; background: var(--color-neutral-100);
  border-radius: var(--radius-md); border: 1px solid var(--color-neutral-200);
}
.field {
  display: flex; flex-direction: column; gap: 0.3rem;
  font-size: var(--text-sm); font-weight: 500; color: var(--color-neutral-700);
  margin-bottom: 0.875rem;
}
.field input[type="file"],
.field input[type="number"],
.field select {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-white);
}
.field input[type="number"]:focus,
.field select:focus {
  outline: none; border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.field-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;
}
.info-icon {
  display: inline-block; vertical-align: middle; margin-left: 0.25rem; cursor: pointer;
}
.advanced-settings { display: flex; flex-direction: column; gap: 1.25rem; margin-bottom: 0.875rem; }
.advanced-settings summary {
  cursor: pointer; font-size: var(--text-sm); font-weight: 500;
  color: var(--color-neutral-500); user-select: none;
}
.advanced-settings summary:hover { color: var(--color-neutral-700); }
.mode-intro { color: var(--color-neutral-600); font-size: var(--text-sm); margin-bottom: 1rem; }
.group-label { font-size: var(--text-sm); font-weight: 600; color: var(--color-neutral-700); margin-bottom: 0.35rem; }
.scan-status {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 1rem; padding: 2.5rem 0;
}
.scan-status .mode-intro { margin-bottom: 0; }
.scan-radar {
  position: relative;
  width: 56px; height: 56px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: inset 0 0 0 2px var(--color-neutral-200);
}
.scan-radar::before {
  content: '';
  position: absolute; inset: 0;
  background: conic-gradient(from 0deg, var(--color-blue-600), transparent 35%);
  animation: scan-radar-sweep 1.1s linear infinite;
}
.scan-radar-dot {
  position: absolute; top: 50%; left: 50%;
  width: 6px; height: 6px; margin: -3px 0 0 -3px;
  border-radius: 50%; background: var(--color-blue-600);
  z-index: 1;
}
@keyframes scan-radar-sweep {
  to { transform: rotate(360deg); }
}
.review-header-row {
  display: flex; align-items: center; justify-content: flex-end; gap: 0.75rem;
  padding-right: 0.75rem; margin-bottom: 0.35rem;
}
.column-header {
  width: 120px; text-align: center;
  font-size: var(--text-xs); font-weight: 600; color: var(--color-neutral-500);
}
.req { color: var(--color-red-500); }
.bulk-classify { 
  display: flex; 
  align-items: center; 
  justify-content: flex-end; 
  gap: 0.5rem; 
  margin-bottom: 0.75rem; 
  padding-right: 0.75rem; }
.bulk-classify .secondary-btn { padding: 0.35rem 0.75rem; font-size: var(--text-sm); }
.classification-select {
  width: 120px; padding: 0.35rem 0.6rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-white);
  text-align: center; text-align-last: center;
}
.batch-summary {
  display: flex; flex-direction: column; gap: 0.35rem; margin-bottom: 1rem;
  max-height: 50vh; overflow-y: auto;
}
.batch-row {
  display: flex; align-items: center; justify-content: space-between; gap: 0.75rem;
  padding: 0.5rem 0.75rem; border-radius: var(--radius-md);
  background: var(--color-neutral-50); font-size: var(--text-sm);
}
.batch-row.done  { background: var(--color-green-50); }
.batch-row.error { background: var(--color-red-50); }
.batch-filename { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.batch-file-status { color: var(--color-neutral-500); font-size: var(--text-xs); white-space: nowrap; }
.error-text { color: var(--color-red-700); }
.action-btn {
  display: flex; align-items: center; gap: 0.4rem;
  background: var(--color-blue-600); color: white; padding: 0.5rem 1rem;
  border-radius: var(--radius-lg); cursor: pointer; font-weight: 600; border: none;
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-spinner { animation: btn-spin 1s linear infinite; }
.btn-spinner .track { fill: none; stroke: rgba(255, 255, 255, 0.35); stroke-width: 2.5; }
.btn-spinner .fill { fill: none; stroke: white; stroke-width: 2.5; stroke-linecap: round; }
@keyframes btn-spin { to { transform: rotate(360deg); } }
.secondary-btn {
  background: var(--color-neutral-100); color: var(--color-neutral-700); padding: 0.5rem 1rem;
  border-radius: var(--radius-lg); cursor: pointer; font-weight: 500; border: 1px solid var(--color-neutral-200);
}
.secondary-btn:hover { background: var(--color-neutral-200); }
</style>
