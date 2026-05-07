<script lang="ts">

    import { page } from '$app/state';
    import Modal from '$lib/components/Modal.svelte';
    import InfoIcon from '../icons/infoIcon.svelte';
    import { activeCorpusId, activeCorpusName, isIsmsActive } from '$lib/stores/isms';

    /** Props passed from parent */
    const { open, onClose} = $props();

    const user = page.data.user;

    let mode = $state<'select' | 'create'>('select');
    let corpora = $state<{ id: string; name: string }[]>([]);
    let selectedCorpusId = $state('');
    let isCorporaLoaded = $state(false);
    type Collection = { id: string; name: string };

    async function loadCorpora() {
      isCorporaLoaded = false;

      const allowed = user?.permissions?.allowed_collections;

      if (!allowed) {
        corpora = [];
        isCorporaLoaded = true;
        return;
      }

      // Admin: wildcard → list all collections
      if (allowed['*']?.access === true) {
        const res = await fetch('/api/collections');
        const data: { collections: Collection[] } = await res.json();
        corpora = data.collections;
      } else {
        // Regular users: only those with access === true
        corpora = Object.entries(allowed)
          .filter(([, v]) => v.access === true)
          .map(([id]) => ({ id, name: id }));
      }

      isCorporaLoaded = true;
    }

    $effect(() => {
        if (open) loadCorpora();
    });


    function handleCorpusSelect() {
        const corpus = corpora.find(c => c.id === selectedCorpusId);
        activeCorpusId.set(selectedCorpusId);
        activeCorpusName.set(corpus?.name ?? null);

        isIsmsActive.set(true);
        onClose();
    }
    function deactivateCorpusSelect() {
        activeCorpusId.set(null)
        activeCorpusName.set(null);
        isIsmsActive.set(false);
    }

    /** Create mode state */
    let newCorpusName = $state("");
    let newCorpusDesc = $state("");
    let files = $state<File[]>([]);

    let fileInputRef: HTMLInputElement | null = null;


    function openFileDialog() {
        fileInputRef?.click();
    }

    /** Accept .docx/.md/.markdown/.pdf (you can add more) */
    const ACCEPT = '.docx,.md,.markdown,.pdf';

    function onFilesChosen(e: Event) {
        const selected = Array.from((e.target as HTMLInputElement).files ?? []);
        files = mergeUnique(files, selected);
    }

    /** Drag & drop (optional) */
    let isDragging = $state(false);
    function onDragOver(e: DragEvent) {
        e.preventDefault();
        isDragging = true;
    }
    function onDragLeave(e: DragEvent) {
        e.preventDefault();
        isDragging = false;
    }
    function onDrop(e: DragEvent) {
        e.preventDefault();
        isDragging = false;
        if (!e.dataTransfer) return;
        const dropped = Array.from(e.dataTransfer.files ?? []);
        files = mergeUnique(files, dropped);
    }

    /** Avoid duplicates by name + size + lastModified (cheap, good enough) */
    function mergeUnique(existing: File[], incoming: File[]) {
        const key = (f: File) => `${f.name}::${f.size}::${f.lastModified}`;
        const seen = new Set(existing.map(key));
        const merged = [...existing];
        for (const f of incoming) if (!seen.has(key(f))) merged.push(f);
        return merged;
    }

    function removeFile(i: number) {
        files = files.filter((_, idx) => idx !== i);
    }

    async function createCorpus() {
        console.log("Creating corpus:", newCorpusName, files);

        newCorpusName = "";
        newCorpusDesc = "";
        files = [];
        mode = "select";
    }

</script>

<Modal {open} {onClose}>
    <span slot="title" class="title-with-info">
        <strong>ISMS Agent</strong>
        <span class="info-icon"><InfoIcon/>
            <div class="tooltip">
            <strong>What is the ISMS Agent?</strong><br/>
            The ISMS Agent uses Retrieval-Augmented Generation (RAG)
            to answer questions using your organization's ISMS documentation.<br/><br/>

            It retrieves relevant passages from your selected ISMS corpus
            and uses them to ground responses.<br/><br/>

            <em>Note:</em> Creating new corpora is restricted to administrators.
            </div>
        </span>
    </span>

  {#if mode === 'select'}
    <div class="isms-content">
        
            <select class="dropdown" bind:value={selectedCorpusId}>
            <option value="" disabled>Select a corpus…</option>
            {#if isCorporaLoaded}
                {#each corpora as c}
                    <option value={c.id}>{c.name}</option>
                {/each}
            {/if}
            </select>
        <!-- Only expose this for admins -->
         {#if user?.permissions?.data_management}
            <button class="primary-btn" onclick={() => mode = "create"}>
                + Create New Corpus
            </button>
        {/if}
    </div>

  {:else}
    <div class="isms-content">
      <h3>Create New ISMS Corpus</h3>

      <!-- Info message -->
      <div class="info">
        <strong>Tip:</strong> For best performance, prefer <code>.docx</code> or prepared
        <code>.md</code>/<code>.markdown</code> files over <code>.pdf</code>.
      </div>

      <label class="field">
        <span>Corpus Name</span>
        <input
          type="text"
          class="input"
          bind:value={newCorpusName}
          placeholder="e.g., HestIA ISMS Corpus"
        />
      </label>

      <!-- Hidden file input + buttons -->
      <input
        bind:this={fileInputRef}
        type="file"
        class="hidden-file"
        multiple
        accept={ACCEPT}
        onchange={onFilesChosen}
      />

      <div
        class="uploader {isDragging ? 'dragging' : ''}"
        ondragover={onDragOver}
        ondragleave={onDragLeave}
        ondrop={onDrop}
      >
        <p>Drag & drop files here, or</p>
        <button type="button" class="secondary-btn" onclick={openFileDialog}>
          Browse files
        </button>
        <small class="hint">Accepted: .docx, .md, .markdown, .pdf</small>
      </div>

      {#if files.length > 0}
        <div class="file-list">
          {#each files as f, i}
            <div class="file-row">
              <div class="file-meta">
                <span class="name" title={f.name}>{f.name}</span>
                <span class="size">{(f.size / 1024).toFixed(1)} KB</span>
              </div>
              <button class="link-btn" onclick={() => removeFile(i)}>Remove</button>
            </div>
          {/each}
        </div>
      {/if}

      <div class="actions">
        <button class="secondary-btn" onclick={() => (mode = 'select')}>Back</button>
        <button class="primary-btn" disabled={!newCorpusName || files.length === 0} onclick={createCorpus}>
          Create Corpus
        </button>
      </div>
    </div>
  {/if}
  <span slot="footer">
    <button class="primary-btn" onclick={handleCorpusSelect}>
        Select
    </button>
    {#if $isIsmsActive}
        <button class="primary-btn" onclick={deactivateCorpusSelect}>
            Deactivate
        </button>
    {/if}
  </span>
</Modal>

<style>
  .isms-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  h3 { margin: 0; font-size: var(--text-lg); }

  .field { display: flex; flex-direction: column; gap: .375rem; }
  .input, .textarea, .dropdown {
    width: 100%;
    padding: .625rem .75rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-neutral-300);
    background: var(--color-white);
    font: inherit;
  }
  .textarea { min-height: 100px; resize: vertical; }

  .dropdown { background: var(--color-neutral-100); }
  .dropdown:hover { background: var(--color-neutral-200); }

  /* File upload area */
  .hidden-file { display: none; }

  .uploader {
    border: 2px dashed var(--color-neutral-300);
    border-radius: var(--radius-lg);
    padding: 1rem;
    text-align: center;
    background: var(--color-neutral-50);
    display: flex; flex-direction: column; align-items: center; gap: .5rem;
  }
  .uploader.dragging {
    border-color: var(--color-blue-600);
    background: color-mix(in oklab, var(--color-blue-50) 60%, transparent);
  }
  .hint { color: var(--color-neutral-600); font-size: var(--text-xs); }

  .file-list { display: flex; flex-direction: column; gap: .5rem; }
  .file-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: .5rem .75rem; border: 1px solid var(--color-neutral-300);
    border-radius: var(--radius-md); background: var(--color-neutral-50);
  }
  .file-meta { display: flex; gap: .75rem; align-items: baseline; }
  .file-meta .name {
    max-width: 24rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .file-meta .size { color: var(--color-neutral-600); font-size: var(--text-sm); }

  .actions { display: flex; justify-content: flex-end; gap: .75rem; }

  .primary-btn {
    background: var(--color-blue-600); color: white; border: none;
    padding: .5rem 1rem; border-radius: var(--radius-md); cursor: pointer;
  }
  .primary-btn:disabled { opacity: .5; cursor: not-allowed; }
  .primary-btn:hover:enabled { background: var(--color-blue-700); }

  .secondary-btn {
    background: var(--color-neutral-200); border: none; padding: .5rem 1rem;
    border-radius: var(--radius-md); cursor: pointer;
  }
  .secondary-btn:hover { background: var(--color-neutral-300); }

  .link-btn {
    border: none; background: transparent; color: var(--color-blue-700);
    cursor: pointer; padding: .25rem .375rem; border-radius: .375rem;
  }
  .link-btn:hover {
    background: color-mix(in oklab, var(--color-blue-100) 60%, transparent);
  }
</style>