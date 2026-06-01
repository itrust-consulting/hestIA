<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import InfoIcon from '../icons/infoIcon.svelte';
  import { renderChatContent } from '$lib/render/renderChatContent';
  import { enqueueUpload } from '$lib/stores/uploadQueue';
  import { tooltip } from '$lib/actions/tooltip';

  type Props = {
    open: boolean;
    onClose: () => void;
    collectionName: string;
    /** Tenant abbreviations to use when uploading */
    defaultTenants?: string[];
    /** Called after a single-file upload completes */
    onSuccess?: (collectionName: string, tenants: string[]) => void;
  };

  let {
    open,
    onClose,
    collectionName,
    defaultTenants = [],
    onSuccess,
  }: Props = $props();

  const META_FIELDS: { key: string; label: string }[] = [
    { key: 'title',          label: 'Title' },
    { key: 'subject',        label: 'Subject' },
    { key: 'category',       label: 'Category' },
    { key: 'author',         label: 'Author' },
    { key: 'reference',      label: 'Reference' },
    { key: 'version',        label: 'Version' },
    { key: 'classification', label: 'Classification' },
    { key: 'description',    label: 'Description' },
    { key: 'lang',           label: 'Language' },
  ];

  type BatchItem = {
    file: File;
    status: 'pending' | 'parsing' | 'queued' | 'uploading' | 'done' | 'skipped' | 'error';
    error?: string;
    n_chunks?: number;
  };

  let uploadDone = $state(false);

  // Batch
  let batchFiles: File[]      = $state([]);
  let batchItems: BatchItem[] = $state([]);
  let batchIndex               = $state(0);
  let batchMode: 'interactive' | 'auto' | null = $state(null);
  let autoRunning              = $state(false);

  // Current-file state
  let uploadFile: File | null   = $state(null);
  let uploadTenants: string[]   = $state([...defaultTenants]);
  let uploadITR                 = $state(false);
  let uploadLanguage            = $state('english');
  let parsing                   = $state(false);
  let parseError: string | null = $state(null);
  let parseDone                 = $state(false);
  let markdownContent           = $state('');
  let previewRaw                = $state(false);
  let metadata: Record<string, string> = $state({});

  $effect(() => {
    if (open) uploadTenants = [...defaultTenants];
  });

  const filledCount = $derived(META_FIELDS.filter(({ key }) => !!metadata[key]).length);
  const isBatch     = $derived(batchFiles.length > 1);
  const isLastFile  = $derived(batchIndex >= batchFiles.length - 1);

  let isDragOver = $state(false);
  const EXCEL_EXTS    = ['.xlsx', '.xlsm'];
  const ACCEPTED_EXTS = ['.docx', '.pdf', '.xlsx', '.xlsm', '.json', '.csv', '.txt', '.md', '.markdown', '.pptx'];

  // Excel sheet selection / navigation
  let allSheets: string[]                   = $state([]);
  let selectedSheets: string[]              = $state([]);
  let activeSheet: string | null            = $state(null);
  let sheetContents: Record<string, string> = $state({});

  const isExcel = $derived(
    uploadFile ? EXCEL_EXTS.some(ext => uploadFile!.name.toLowerCase().endsWith(ext)) : false
  );
  const displayMarkdown = $derived(
    isExcel && activeSheet && sheetContents[activeSheet] !== undefined
      ? sheetContents[activeSheet]
      : markdownContent
  );

  function _extractSheets(md: string): string[] {
    const names: string[] = [];
    for (const line of md.split('\n')) {
      const m = /^## (.+)$/.exec(line.trim());
      if (m) names.push(m[1].trim());
    }
    return names;
  }

  function _splitToSheets(md: string, sheets: string[]): Record<string, string> {
    const result: Record<string, string> = {};
    const sections = md.split(/\n(?=## )/);
    for (const section of sections) {
      const name = /^## (.+)/.exec(section.trimStart())?.[1]?.trim();
      if (name && sheets.includes(name)) result[name] = section.trimStart();
    }
    return result;
  }

  function onDragOver(e: DragEvent) {
    if (autoRunning) return;
    e.preventDefault();
    isDragOver = true;
  }

  function onDragLeave(e: DragEvent) {
    if (!(e.currentTarget as Element).contains(e.relatedTarget as Element))
      isDragOver = false;
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault();
    isDragOver = false;
    if (autoRunning) return;

    const dropped = Array.from(e.dataTransfer?.files ?? [])
      .filter(f => ACCEPTED_EXTS.some(ext => f.name.toLowerCase().endsWith(ext)));
    if (!dropped.length) return;

    if (batchMode === 'interactive' && batchFiles.length > 0) {
      batchFiles = [...batchFiles, ...dropped];
      batchItems = [...batchItems, ...dropped.map(f => ({ file: f, status: 'pending' as const }))];
    } else {
      batchFiles = dropped;
      batchItems = dropped.map(f => ({ file: f, status: 'pending' as const }));
      batchIndex = 0;
      resetFileState();
      if (dropped.length === 1) {
        batchMode  = 'interactive';
        uploadFile = dropped[0];
        await triggerParse();
      } else {
        batchMode = null;
      }
    }
  }

  function resetFileState() {
    uploadFile      = null;
    parsing         = false;
    parseError      = null;
    parseDone       = false;
    markdownContent = '';
    previewRaw      = false;
    metadata        = {};
    allSheets       = [];
    selectedSheets  = [];
    activeSheet     = null;
    sheetContents   = {};
  }

  export function openModal() {
    batchFiles       = [];
    batchItems       = [];
    batchIndex       = 0;
    batchMode        = null;
    autoRunning      = false;
    uploadTenants    = [...defaultTenants];
    uploadITR        = false;
    uploadLanguage   = 'english';
    uploadDone       = false;
    resetFileState();
  }

  function closeModal() {
    uploadDone = false;
    onClose();
  }

  async function onFileChange(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) return;

    batchFiles = files;
    batchItems = files.map(f => ({ file: f, status: 'pending' as const }));
    batchIndex = 0;
    resetFileState();

    if (files.length === 1) {
      batchMode  = 'interactive';
      uploadFile = files[0];
      await triggerParse();
    }
  }

  async function loadFileAtIndex(i: number) {
    resetFileState();
    uploadFile = batchFiles[i];
    await triggerParse();
  }

  async function startInteractive() {
    batchMode = 'interactive';
    await loadFileAtIndex(0);
  }

  async function startAuto() {
    batchMode   = 'auto';
    autoRunning = true;

    for (let i = 0; i < batchFiles.length; i++) {
      const file = batchFiles[i];
      batchItems[i] = { ...batchItems[i], status: 'parsing' };
      batchItems = [...batchItems];

      let parsedMeta: Record<string, string> = {};
      try {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('itrust_template', String(uploadITR));
        const pr   = await fetch('/api/admin/collections/parse', { method: 'POST', body: fd });
        const pdat = await pr.json();
        if (pr.ok && !pdat.parse_error)
          parsedMeta = Object.fromEntries(META_FIELDS.map(({ key }) => [key, (pdat.metadata ?? {})[key] ?? '']));
      } catch { /* proceed with empty metadata */ }

      batchItems[i] = { ...batchItems[i], status: 'queued' };
      batchItems = [...batchItems];

      const capturedI = i;
      enqueueUpload({
        id: crypto.randomUUID(),
        file,
        collection: collectionName,
        tenants: uploadTenants,
        itrTemplate: uploadITR,
        metadata: parsedMeta,
        language: uploadLanguage,
        onDone: (n_chunks) => {
          batchItems[capturedI] = { ...batchItems[capturedI], status: 'done', n_chunks };
          batchItems = [...batchItems];
        },
        onError: (err) => {
          batchItems[capturedI] = { ...batchItems[capturedI], status: 'error', error: err };
          batchItems = [...batchItems];
        },
      });
    }

    autoRunning = false;
    uploadDone = true;
  }

  async function triggerParse() {
    if (!uploadFile) return;
    parsing         = true;
    parseError      = null;
    parseDone       = false;
    markdownContent = '';
    metadata        = {};

    const form = new FormData();
    form.append('file', uploadFile);
    form.append('itrust_template', String(uploadITR));

    try {
      const res  = await fetch('/api/admin/collections/parse', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `${res.status}`);
      markdownContent = data.markdown ?? '';
      const sheets = _extractSheets(markdownContent);
      allSheets      = sheets;
      selectedSheets = [...sheets];
      sheetContents  = sheets.length > 1 ? _splitToSheets(markdownContent, sheets) : {};
      activeSheet    = sheets.length > 1 ? sheets[0] : null;
      if (data.parse_error) {
        parseError = data.parse_error;
        metadata   = Object.fromEntries(META_FIELDS.map(({ key }) => [key, '']));
      } else {
        const raw: Record<string, string> = data.metadata ?? {};
        metadata = Object.fromEntries(META_FIELDS.map(({ key }) => [key, raw[key] ?? '']));
      }
      parseDone = true;
    } catch (err: any) {
      parseError      = err.message ?? 'Could not parse document.';
      markdownContent = '';
      metadata        = Object.fromEntries(META_FIELDS.map(({ key }) => [key, '']));
      parseDone       = true;
    } finally {
      parsing = false;
    }
  }

  function onITRChange() { if (uploadFile) triggerParse(); }

  function _enqueue(i: number) {
    const file = batchFiles[i];
    batchItems[i] = { ...batchItems[i], status: 'queued' };
    batchItems = [...batchItems];
    enqueueUpload({
      id: crypto.randomUUID(),
      file,
      collection: collectionName,
      tenants: uploadTenants,
      itrTemplate: uploadITR,
      metadata,
      language: uploadLanguage,
      selectedSheets: isExcel && selectedSheets.length > 0 && selectedSheets.length < allSheets.length
        ? [...selectedSheets] : undefined,
      onDone: (n_chunks) => {
        batchItems[i] = { ...batchItems[i], status: 'done', n_chunks };
        batchItems = [...batchItems];
        if (!isBatch) onSuccess?.(collectionName, [...uploadTenants]);
      },
      onError: (err) => {
        batchItems[i] = { ...batchItems[i], status: 'error', error: err };
        batchItems = [...batchItems];
      },
    });
  }

  function handleUpload() {
    if (!uploadFile) return;
    _enqueue(batchIndex);
    if (isBatch) { uploadDone = true; } else { closeModal(); }
  }

  async function uploadAndNext() {
    if (!uploadFile) return;
    _enqueue(batchIndex);
    if (isLastFile) { uploadDone = true; return; }
    batchIndex++;
    await loadFileAtIndex(batchIndex);
  }

  async function skipCurrent() {
    batchItems[batchIndex] = { ...batchItems[batchIndex], status: 'skipped' };
    batchItems = [...batchItems];
    if (isLastFile) { uploadDone = true; return; }
    batchIndex++;
    await loadFileAtIndex(batchIndex);
  }
</script>

<Modal
  title={
    uploadDone                               ? (isBatch ? 'Batch Complete' : 'Upload Complete') :
    batchMode === 'auto'                     ? 'Auto-Upload' :
    (batchMode === 'interactive' && isBatch) ? `Upload (${batchIndex + 1} / ${batchFiles.length})` :
                                               'Add Document'
  }
  {open}
  onClose={closeModal}
  wide={true}
>

  <!-- ── Done ──────────────────────────────────────────────────────────── -->
  {#if uploadDone}
    <div class="batch-summary">
      {#each batchItems as item}
        <div class="batch-row"
          class:active={item.status === 'queued' || item.status === 'uploading'}
          class:done={item.status === 'done'}
          class:skipped={item.status === 'skipped'}
          class:error={item.status === 'error'}>
          <span class="batch-icon">
            {#if item.status === 'done'}✓
            {:else if item.status === 'error'}✗
            {:else if item.status === 'queued' || item.status === 'uploading'}⟳
            {:else}—{/if}
          </span>
          <span class="batch-filename">{item.file.name}</span>
          <span class="batch-file-status">
            {#if item.status === 'queued'}Queued…
            {:else if item.status === 'uploading'}Uploading…
            {:else if item.status === 'done'}{item.n_chunks} chunks
            {:else if item.status === 'error'}<span class="error-text">{item.error}</span>
            {:else}skipped{/if}
          </span>
        </div>
      {/each}
    </div>

  <!-- ── Mode selection ─────────────────────────────────────────────────── -->
  {:else if batchMode === null && isBatch}
    <p class="mode-intro">{batchFiles.length} files selected. How would you like to proceed?</p>
    <div class="mode-cards">
      <button class="mode-card" onclick={startInteractive}>
        <span class="mode-title">Review each file</span>
        <span class="mode-desc">Preview and edit content and metadata for each document before uploading.</span>
      </button>
      <button class="mode-card mode-card-auto" onclick={startAuto}>
        <span class="mode-title">Auto-upload all</span>
        <span class="mode-desc">Parse and upload all files automatically using extracted metadata.</span>
        <span class="mode-warn">⚠ Metadata may be incomplete, which can reduce retrieval accuracy.</span>
      </button>
    </div>

  <!-- ── Auto-upload progress ───────────────────────────────────────────── -->
  {:else if batchMode === 'auto'}
    {#if autoRunning}
      <div class="auto-warn">
        ⚠ Uploading without metadata review — retrieval accuracy may be reduced for some documents.
      </div>
    {/if}
    <div class="batch-summary">
      {#each batchItems as item}
        <div class="batch-row"
          class:active={item.status === 'parsing' || item.status === 'uploading'}
          class:done={item.status === 'done'}
          class:error={item.status === 'error'}>
          <span class="batch-icon">
            {#if item.status === 'done'}✓
            {:else if item.status === 'error'}✗
            {:else if item.status === 'parsing' || item.status === 'queued'}⟳
            {:else}·{/if}
          </span>
          <span class="batch-filename">{item.file.name}</span>
          <span class="batch-file-status">
            {#if item.status === 'parsing'}Parsing…
            {:else if item.status === 'queued'}Queued…
            {:else if item.status === 'done'}{item.n_chunks} chunks
            {:else if item.status === 'error'}<span class="error-text">{item.error}</span>
            {:else}Pending{/if}
          </span>
        </div>
      {/each}
    </div>

  <!-- ── Interactive ────────────────────────────────────────────────────── -->
  {:else}
    {#if isBatch}
      <div class="batch-queue">
        {#each batchItems as item, i}
          <button
            class="queue-chip"
            class:queue-active={i === batchIndex}
            class:queue-done={item.status === 'done'}
            class:queue-queued={item.status === 'queued'}
            class:queue-skipped={item.status === 'skipped'}
            class:queue-error={item.status === 'error'}
            title={item.file.name}
            onclick={() => { batchIndex = i; loadFileAtIndex(i); }}
          >{i + 1}</button>
        {/each}
        <span class="queue-label">{batchIndex + 1} of {batchFiles.length}</span>
      </div>
    {/if}

    <div class="upload-layout">
      <div class="upload-left">
        <div class="field">
          <span>Collection</span>
          <span class="collection-name-display">{collectionName}</span>
        </div>

        {#if isBatch}
          <div class="field">
            <span>Current file</span>
            <span class="current-filename">{uploadFile?.name ?? '—'}</span>
          </div>
        {:else}
          <label class="field">
            <span>Select File(s) <span class="req">*</span></span>
            <input type="file" accept=".docx,.pdf,.xlsx,.xlsm,.json,.csv,.txt,.md,.markdown,.pptx" multiple onchange={onFileChange} />
          </label>
        {/if}
        <label class="field toggle-field">
          <input type="checkbox" bind:checked={uploadITR} onchange={onITRChange} />
          <span>itrust document template
            <span class="info-icon" use:tooltip={"Parser will assume itrust template to extract metadata."}><InfoIcon/></span>
          </span>
        </label>

        {#if isExcel && allSheets.length > 1 && parseDone}
          <div class="field">
            <span>Sheets
              <span class="info-icon" use:tooltip={"Select which sheets to include in the upload."}><InfoIcon/></span>
            </span>
            <div class="sheet-list">
              {#each allSheets as sheet}
                <label class="sheet-item">
                  <input
                    type="checkbox"
                    checked={selectedSheets.includes(sheet)}
                    onchange={() => {
                      selectedSheets = selectedSheets.includes(sheet)
                        ? selectedSheets.filter(s => s !== sheet)
                        : [...selectedSheets, sheet];
                    }}
                  />
                  <span class="sheet-name">{sheet}</span>
                </label>
              {/each}
            </div>
          </div>
        {/if}

        <label class="field">
          <span>Stemmer language
            <span class="info-icon" use:tooltip={"Language used for keyword stemming. Locked after first document is ingested into a collection."}><InfoIcon/></span>
          </span>
          <select bind:value={uploadLanguage}>
            <option value="english">English</option>
            <option value="french">French</option>
            <option value="german">German</option>
          </select>
        </label>
      </div>

      <div class="upload-right"
        role="region"
        aria-label="Document preview — drop files here to add them"
        class:drag-over={isDragOver}
        ondragover={onDragOver}
        ondragleave={onDragLeave}
        ondrop={onDrop}
      >
        {#if isDragOver}
          <div class="drop-overlay">Drop to add files</div>
        {/if}
        <div class="preview-header">
          <span class="preview-label">Document preview</span>
          <div class="preview-header-right">
            {#if uploadFile}
              {#if parsing}
                <span class="status-indicator parsing">Parsing…</span>
              {:else if parseError}
                <span class="status-indicator error">Parse error — <button class="link-btn" onclick={triggerParse}>retry</button></span>
              {:else if parseDone}
                <span class="status-indicator ok">Ready</span>
              {/if}
            {/if}
            {#if parseDone && !parseError}
              <div class="preview-toggle">
                <button class="toggle-btn" class:active={!previewRaw} onclick={() => (previewRaw = false)}>Preview</button>
                <button class="toggle-btn" class:active={previewRaw}  onclick={() => (previewRaw = true)}>Edit</button>
              </div>
            {/if}
          </div>
        </div>
        {#if previewRaw}
          {#if isExcel && activeSheet && sheetContents[activeSheet] !== undefined}
            <textarea
              class="preview-area raw-editor"
              value={sheetContents[activeSheet]}
              oninput={(e) => { sheetContents = { ...sheetContents, [activeSheet!]: (e.currentTarget as HTMLTextAreaElement).value }; }}
              spellcheck={false}
            ></textarea>
          {:else}
            <textarea class="preview-area raw-editor" bind:value={markdownContent} spellcheck={false}></textarea>
          {/if}
        {:else}
          <div class="preview-area prose dark:prose-invert max-w-none" class:error-area={!!parseError}>
            {#if parseError}
              <pre class="parse-error-text">{parseError}</pre>
            {:else if displayMarkdown}
              {@html renderChatContent(displayMarkdown)}
            {:else}
              <span class="preview-placeholder">Select a file to preview its content…</span>
            {/if}
          </div>
        {/if}

        {#if isExcel && allSheets.length > 1 && parseDone && !parseError}
          <div class="sheet-tabs-bar">
            {#each allSheets as sheet}
              <button
                class="sheet-tab-btn"
                class:active={activeSheet === sheet}
                onclick={() => (activeSheet = sheet)}
              >{sheet}</button>
            {/each}
          </div>
        {/if}
      </div>

      <div class="upload-meta">
        <span class="meta-header">
          Metadata
          {#if parseDone}<span class="meta-count">({filledCount}/{META_FIELDS.length})</span>{/if}
        </span>
        <div class="meta-fields">
          {#each META_FIELDS as { key, label }}
            <label class="field">
              <span>{label}</span>
              <input type="text" bind:value={metadata[key]} placeholder="—" />
            </label>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <svelte:fragment slot="footer">
    {#if uploadDone}
      <button class="action-btn" onclick={openModal}>Upload another</button>
    {:else if batchMode === 'interactive'}
      {#if isBatch && !isLastFile}
        <button class="secondary-btn" onclick={skipCurrent} disabled={parsing}>Skip</button>
        <button class="action-btn" onclick={uploadAndNext}
          disabled={!uploadFile || parsing || (isExcel && allSheets.length > 1 && selectedSheets.length === 0)}>
          Upload & Next
        </button>
      {:else}
        <button class="action-btn" onclick={handleUpload}
          disabled={!uploadFile || parsing || (isExcel && allSheets.length > 1 && selectedSheets.length === 0)}>
          {isBatch ? 'Upload & Finish' : 'Upload'}
        </button>
      {/if}
    {:else if batchMode === null && !isBatch}
      <button class="action-btn" onclick={handleUpload}
        disabled={!uploadFile || parsing || (isExcel && allSheets.length > 1 && selectedSheets.length === 0)}>
        Upload
      </button>
    {/if}
  </svelte:fragment>
</Modal>

<style>
.collection-name-display {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-neutral-800);
  padding: 0.4rem 0.65rem;
  background: var(--color-neutral-100);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-neutral-200);
}

/* ── Mode selection ── */
.mode-intro { color: var(--color-neutral-600); font-size: var(--text-sm); margin-bottom: 1rem; }
.mode-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.mode-card {
  display: flex; flex-direction: column; gap: 0.5rem;
  padding: 1.25rem; border: 2px solid var(--color-neutral-200);
  border-radius: var(--radius-xl); background: var(--color-white);
  text-align: left; cursor: pointer;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}
.mode-card:hover { border-color: var(--color-blue-400); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.mode-card-auto:hover { border-color: var(--color-yellow-500); }
.mode-title { font-size: var(--text-md); font-weight: 600; color: var(--color-neutral-900); }
.mode-desc  { font-size: var(--text-sm); color: var(--color-neutral-600); line-height: 1.5; }
.mode-warn  {
  font-size: var(--text-xs); color: var(--color-yellow-700);
  background: var(--color-yellow-50); border: 1px solid var(--color-yellow-200);
  border-radius: var(--radius-md); padding: 0.35rem 0.6rem; margin-top: 0.25rem;
}

/* ── Batch ── */
.batch-queue { display: flex; align-items: center; gap: 0.375rem; flex-wrap: wrap; margin-bottom: 0.875rem; }
.queue-chip {
  width: 2rem; height: 2rem; border-radius: var(--radius-md);
  border: 1px solid var(--color-neutral-300); background: var(--color-white);
  font-size: var(--text-xs); font-weight: 600; cursor: pointer; color: var(--color-neutral-600);
}
.queue-chip:hover:not(.queue-active) { background: var(--color-neutral-100); }
.queue-chip.queue-active  { background: var(--color-blue-600);   color: white; border-color: var(--color-blue-600); }
.queue-chip.queue-done    { background: var(--color-green-100);  color: var(--color-green-700); border-color: var(--color-green-300); }
.queue-chip.queue-queued  { background: var(--color-blue-50);    color: var(--color-blue-600);  border-color: var(--color-blue-200); }
.queue-chip.queue-skipped { background: var(--color-neutral-100); color: var(--color-neutral-400); }
.queue-chip.queue-error   { background: var(--color-red-100);    color: var(--color-red-700);   border-color: var(--color-red-300); }
.queue-label { font-size: var(--text-xs); color: var(--color-neutral-500); margin-left: 0.25rem; }

.auto-warn {
  background: var(--color-yellow-50); border: 1px solid var(--color-yellow-200);
  color: var(--color-yellow-800); padding: 0.6rem 0.875rem;
  border-radius: var(--radius-md); font-size: var(--text-sm); margin-bottom: 1rem;
}
.batch-summary { display: flex; flex-direction: column; gap: 0.35rem; }
.batch-row {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.5rem 0.75rem; border-radius: var(--radius-md);
  background: var(--color-neutral-50); font-size: var(--text-sm);
}
.batch-row.active  { background: var(--color-blue-50); }
.batch-row.done    { background: var(--color-green-50); }
.batch-row.error   { background: var(--color-red-50); }
.batch-row.skipped { opacity: 0.55; }
.batch-icon        { width: 1.25rem; text-align: center; flex-shrink: 0; font-size: 1rem; }
.batch-filename    { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.batch-file-status { color: var(--color-neutral-500); font-size: var(--text-xs); white-space: nowrap; }
.batch-row.done .batch-file-status { color: var(--color-green-700); }
.error-text { color: var(--color-red-700); }
.current-filename { font-size: var(--text-sm); font-weight: 500; color: var(--color-neutral-800); word-break: break-all; }

/* ── Upload layout ── */
.upload-layout {
  display: grid; grid-template-columns: 240px 1fr 200px; gap: 1.25rem;
  height: 420px;
}
.upload-left  { display: flex; flex-direction: column; gap: 0.875rem; overflow-y: auto; min-height: 0; }
.upload-right { display: flex; flex-direction: column; gap: 0.5rem; position: relative; overflow: hidden; }
.upload-meta  {
  display: flex; flex-direction: column; gap: 0.5rem;
  border-left: 1px solid var(--color-neutral-200); padding-left: 1rem;
  overflow: hidden;
}
.meta-header {
  font-size: var(--text-sm); font-weight: 600; color: var(--color-neutral-700);
  flex-shrink: 0;
}
.meta-count { font-weight: 400; color: var(--color-neutral-400); margin-left: 0.25rem; }
.meta-fields {
  flex: 1; min-height: 0; overflow-y: auto;
  display: flex; flex-direction: column; gap: 0.5rem;
}
.upload-right.drag-over .preview-area {
  border-color: var(--color-blue-400);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.drop-overlay {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in oklab, var(--color-blue-500) 8%, transparent);
  border: 2px dashed var(--color-blue-400); border-radius: var(--radius-md);
  font-size: var(--text-lg); font-weight: 600; color: var(--color-blue-600);
  pointer-events: none; z-index: 10;
}

/* ── Preview ── */
.preview-header { display: flex; align-items: center; justify-content: space-between; }
.preview-header-right { display: flex; align-items: center; gap: 0.75rem; }
.preview-label { font-size: var(--text-sm); font-weight: 500; color: var(--color-neutral-700); }
.preview-toggle {
  display: flex; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); overflow: hidden;
}
.toggle-btn {
  flex: 1; padding: 0.2rem 0.65rem; font-size: var(--text-xs); font-weight: 500;
  background: var(--color-white); color: var(--color-neutral-600); border: none; cursor: pointer;
  text-align: center;
}
.toggle-btn + .toggle-btn { border-left: 1px solid var(--color-neutral-300); }
.toggle-btn.active { background: var(--color-blue-600); color: white; }
.toggle-btn:not(.active):hover { background: var(--color-neutral-100); }
.raw-editor {
  font-family: var(--font-mono, ui-monospace, monospace); font-size: var(--text-xs);
  line-height: 1.6; resize: none; white-space: pre; overflow-wrap: normal; overflow-x: auto;
}
.preview-area {
  flex: 1; min-height: 0; overflow-y: auto;
  padding: 0.75rem 1rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); background: var(--color-neutral-50);
  font-size: var(--text-sm); line-height: 1.7;
}
.preview-area.error-area { background: var(--color-red-50); border-color: var(--color-red-200); }
.parse-error-text { color: var(--color-red-700); font-family: var(--font-mono, ui-monospace, monospace); font-size: var(--text-xs); white-space: pre-wrap; margin: 0; }
.preview-placeholder { color: var(--color-neutral-400); font-size: var(--text-sm); }
.status-indicator { display: flex; align-items: center; gap: 0.4rem; font-size: var(--text-sm); }
.status-indicator.parsing { color: var(--color-neutral-500); }
.status-indicator.ok      { color: var(--color-green-700); }
.status-indicator.error   { color: var(--color-yellow-700); }


/* ── Form elements ── */
.field {
  display: flex; flex-direction: column; gap: 0.3rem;
  font-size: var(--text-sm); font-weight: 500; color: var(--color-neutral-700);
}
.field input[type="text"],
.field input[type="file"],
.field select {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-white);
}
.field input[type="text"]:focus,
.field select:focus {
  outline: none; border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}
.toggle-field { flex-direction: row; align-items: center; gap: 0.5rem; font-weight: 400; color: var(--color-neutral-800); }
.req { color: var(--color-red-500); }

/* ── Buttons ── */
.action-btn {
  background: var(--color-blue-600); color: white; padding: 0.5rem 1rem;
  border-radius: var(--radius-lg); cursor: pointer; font-weight: 600;
  display: flex; align-items: center; gap: 0.4rem; border: none;
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.secondary-btn {
  background: var(--color-neutral-100); color: var(--color-neutral-700); padding: 0.5rem 1rem;
  border-radius: var(--radius-lg); cursor: pointer; font-weight: 500; border: 1px solid var(--color-neutral-200);
}
.secondary-btn:hover:not(:disabled) { background: var(--color-neutral-200); }
.secondary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.link-btn { background: none; border: none; color: var(--color-blue-600); cursor: pointer; padding: 0; font-size: inherit; text-decoration: underline; }

/* ── Info icon ── */
.info-icon {
  display: inline-block; vertical-align: middle; margin-left: 0.25rem; cursor: pointer;
}

/* ── Sheet selection (left panel checkboxes) ── */
.sheet-list {
  display: flex; flex-direction: column; gap: 0.25rem;
  padding: 0.375rem 0.5rem; border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); background: var(--color-white);
  max-height: 160px; overflow-y: auto;
}
.sheet-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.2rem 0.25rem; border-radius: var(--radius-sm);
  cursor: pointer; font-weight: 400; color: var(--color-neutral-800);
}
.sheet-item:hover { background: var(--color-neutral-50); }
.sheet-item input[type="checkbox"] { margin: 0; cursor: pointer; flex-shrink: 0; }
.sheet-name { font-size: var(--text-xs); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Sheet tabs (preview navigation) ── */
.sheet-tabs-bar {
  display: flex; flex-wrap: wrap; gap: 0.25rem;
  padding-top: 0.5rem; flex-shrink: 0;
  border-top: 1px solid var(--color-neutral-200); margin-top: 0.375rem;
}
.sheet-tab-btn {
  padding: 0.2rem 0.65rem; font-size: var(--text-xs); font-weight: 500;
  border: 1px solid var(--color-neutral-300); border-radius: var(--radius-md);
  background: var(--color-white); color: var(--color-neutral-600); cursor: pointer;
  white-space: nowrap; max-width: 140px; overflow: hidden; text-overflow: ellipsis;
  transition: background 80ms ease, border-color 80ms ease;
}
.sheet-tab-btn:hover:not(.active) { background: var(--color-neutral-100); }
.sheet-tab-btn.active {
  background: var(--color-blue-600); color: white;
  border-color: var(--color-blue-600);
}
</style>
