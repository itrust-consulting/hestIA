<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';

  type ImageEntry = { filename: string; url: string; size: number };

  type Props = {
    open: boolean;
    onClose: () => void;
    onInsert?: (markdown: string) => void;
  };

  let { open, onClose, onInsert }: Props = $props();

  let images   = $state<ImageEntry[]>([]);
  let loading  = $state(false);
  let error    = $state('');

  // Per-image rename state
  let renamingFilename = $state<string | null>(null);
  let renameValue      = $state('');
  let renameError      = $state('');
  let renameBusy       = $state(false);

  let copiedFilename = $state<string | null>(null);

  $effect(() => {
    if (open) load();
    else resetRename();
  });

  async function load() {
    loading = true;
    error = '';
    try {
      const res = await fetch('/api/help/images');
      if (res.ok) images = (await res.json()).images ?? [];
      else error = 'Failed to load images.';
    } catch {
      error = 'Network error.';
    } finally {
      loading = false;
    }
  }

  function fmt(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function copyMarkdown(img: ImageEntry) {
    const md = `![image](${img.url})`;
    await navigator.clipboard.writeText(md);
    copiedFilename = img.filename;
    setTimeout(() => { copiedFilename = null; }, 1800);
  }

  function startRename(img: ImageEntry) {
    renamingFilename = img.filename;
    renameValue = img.filename;
    renameError = '';
  }

  function cancelRename() { resetRename(); }

  function resetRename() {
    renamingFilename = null;
    renameValue = '';
    renameError = '';
    renameBusy = false;
  }

  async function confirmRename(img: ImageEntry) {
    const newName = renameValue.trim();
    if (!newName || newName === img.filename) { cancelRename(); return; }
    renameBusy = true;
    renameError = '';
    try {
      const res = await fetch(`/api/help/images/${encodeURIComponent(img.filename)}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ filename: newName }),
      });
      if (res.ok) { await load(); resetRename(); }
      else { renameError = (await res.json()).detail ?? 'Rename failed.'; }
    } catch {
      renameError = 'Network error.';
    } finally {
      renameBusy = false;
    }
  }

  async function deleteImage(img: ImageEntry) {
    if (!confirm(`Delete "${img.filename}"? This cannot be undone.`)) return;
    const res = await fetch(`/api/help/images/${encodeURIComponent(img.filename)}`, { method: 'DELETE' });
    if (res.ok) images = images.filter(i => i.filename !== img.filename);
  }
</script>

<Modal title="Image Manager" {open} {onClose} wide={true}>
  {#if loading}
    <p class="status">Loading…</p>
  {:else if error}
    <p class="status error">{error}</p>
  {:else if images.length === 0}
    <p class="status muted">No images uploaded yet. Paste an image in the editor to add one.</p>
  {:else}
    <div class="grid">
      {#each images as img (img.filename)}
        <div class="card">
          <div class="thumb-wrap">
            <img src={img.url} alt={img.filename} class="thumb" />
          </div>

          {#if renamingFilename === img.filename}
            <div class="rename-row">
              <input
                class="rename-input"
                bind:value={renameValue}
                disabled={renameBusy}
                onkeydown={(e) => {
                  if (e.key === 'Enter')  { e.preventDefault(); confirmRename(img); }
                  if (e.key === 'Escape') cancelRename();
                }}
                autofocus
              />
              {#if renameError}<span class="rename-err">{renameError}</span>{/if}
            </div>
            <div class="actions">
              <button class="btn-confirm" onclick={() => confirmRename(img)} disabled={renameBusy}>
                {renameBusy ? '…' : '✓'}
              </button>
              <button class="btn-cancel" onclick={cancelRename}>✕</button>
            </div>
          {:else}
            <span class="filename" title={img.filename}>{img.filename}</span>
            <span class="filesize">{fmt(img.size)}</span>
            <div class="actions">
              {#if onInsert}
                <button
                  class="btn-insert"
                  onclick={() => onInsert?.(`![image](${img.url})`)}
                  title="Insert into editor"
                >Insert</button>
              {/if}
              <button
                class="btn-copy"
                class:copied={copiedFilename === img.filename}
                onclick={() => copyMarkdown(img)}
                title="Copy markdown"
              >{copiedFilename === img.filename ? 'Copied!' : 'Copy'}</button>
              <button class="btn-rename" onclick={() => startRename(img)} title="Rename">Rename</button>
              <button class="btn-delete" onclick={() => deleteImage(img)} title="Delete">Delete</button>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</Modal>

<style>
  .status {
    font-size: var(--text-sm);
    text-align: center;
    padding: 2rem 0;
  }
  .muted  { color: var(--color-neutral-400); }
  .error  { color: var(--color-red-600); }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 0.75rem;
  }

  .card {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    padding: 0.6rem;
    border: 1px solid var(--color-neutral-200);
    border-radius: var(--radius-lg);
    background: var(--color-neutral-50);
    overflow: hidden;
  }

  .thumb-wrap {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: var(--color-neutral-200);
    border-radius: var(--radius-md);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .thumb {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .filename {
    font-size: var(--text-xs);
    font-weight: 500;
    color: var(--color-neutral-700);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .filesize {
    font-size: var(--text-xs);
    color: var(--color-neutral-400);
  }

  .actions {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    margin-top: 0.1rem;
  }

  .actions button {
    flex: 1;
    padding: 0.2rem 0;
    font-size: 0.7rem;
    font-weight: 500;
    border-radius: var(--radius-sm);
    cursor: pointer;
    border: 1px solid var(--color-neutral-300);
    background: var(--color-white);
    color: var(--color-neutral-700);
    transition: background-color 100ms ease;
    white-space: nowrap;
  }

  .actions button:hover { background: var(--color-neutral-100); }

  .btn-insert { border-color: var(--color-blue-300); color: var(--color-blue-700); }
  .btn-insert:hover { background: var(--color-blue-50); }

  .btn-copy.copied { background: var(--color-green-50); color: var(--color-green-700); border-color: var(--color-green-300); }

  .btn-delete { color: var(--color-red-600); border-color: var(--color-red-300); }
  .btn-delete:hover { background: var(--color-red-50); }

  /* Rename inline */
  .rename-row {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .rename-input {
    width: 100%;
    font-size: var(--text-xs);
    padding: 0.2rem 0.4rem;
    border: 1px solid var(--color-blue-300);
    border-radius: var(--radius-sm);
    background: var(--color-white);
    color: var(--color-neutral-900);
    outline: none;
  }

  .rename-err {
    font-size: 0.65rem;
    color: var(--color-red-600);
  }

  .btn-confirm {
    background: var(--color-blue-600) !important;
    color: white !important;
    border-color: var(--color-blue-600) !important;
  }
</style>
