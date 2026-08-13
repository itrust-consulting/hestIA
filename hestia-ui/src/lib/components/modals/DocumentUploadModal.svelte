<script lang="ts">
  import { tick } from 'svelte';
  import Modal from '$lib/components/Modal.svelte';
  import InfoIcon from '../icons/infoIcon.svelte';
  import { renderChatContent } from '$lib/render/renderChatContent';
  import { enqueueUpload, createBatchToast } from '$lib/stores/uploadQueue';
  import { tooltip } from '$lib/actions/tooltip';
  import { fromDataTransferItems, ACCEPTED_EXTS, type SelectedFile } from '$lib/upload/folderSelect';
  import { sha256Hex } from '$lib/upload/hash';
  import { DOCUMENT_CLASSIFICATION_OPTIONS } from '$lib/classification';
  import { LANGUAGE_OPTIONS, guessLanguage } from '$lib/language';

  // Fixed pseudo sync_id for plain (non-Sync-Folder) uploads — lets these
  // participate in the same collection-wide content-hash dedup as Sync
  // Folder sources without the backend needing to special-case "no sync_id".
  const MANUAL_SYNC_ID = 'manual';

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

  // Free-text fields rendered in the "Document information" step, in the
  // fixed layout: Title (full width), then Author/Publisher, then
  // Classification/Language (rendered separately, see template), then
  // Version/Year.
  const META_FIELDS: { key: string; label: string }[] = [
    { key: 'title',     label: 'Title' },
    { key: 'author',    label: 'Author' },
    { key: 'publisher', label: 'Publisher' },
    { key: 'version',   label: 'Version' },
    { key: 'year',      label: 'Year' },
  ];

  // Full set of keys the parse endpoint may populate / that get sent as
  // metadata overrides on upload.
  const ALL_METADATA_KEYS = [...META_FIELDS.map(({ key }) => key), 'classification', 'lang'];

  // Field names a power user's custom metadata field may not use — they're
  // already owned by a fixed form field or computed server-side.
  const RESERVED_METADATA_KEYS = [...ALL_METADATA_KEYS, 'source', 'source_uri', 'document_id'];

  type CustomField = { key: string; value: string };

  type BatchItem = {
    file: File;
    /** Relative path (e.g. "docs/guide.md") when the file came from a folder pick/drop. */
    relPath?: string;
    status: 'pending' | 'parsing' | 'queued' | 'uploading' | 'done' | 'skipped' | 'error';
    error?: string;
    n_chunks?: number;
    duplicateOf?: string;
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
  let uploadLanguage            = $state('');
  let docStep: 'select' | 'details' = $state('select');
  let parsing                   = $state(false);
  let parseError: string | null = $state(null);
  let parseDone                 = $state(false);
  let markdownContent           = $state('');
  let previewRaw                = $state(false);
  let metadata: Record<string, string> = $state({});
  let customFields: CustomField[]      = $state([]);

  $effect(() => {
    if (open) uploadTenants = [...defaultTenants];
  });

  // The Language select (step 2) is the single source of truth for the
  // document's language — it drives both the stemmer (`uploadLanguage`,
  // sent as the `language` form field) and the stored `lang` metadata value,
  // so there is no separate manual stemmer picker to keep in sync.
  $effect(() => {
    metadata.lang = uploadLanguage;
  });

  const isBatch     = $derived(batchFiles.length > 1);
  const isLastFile  = $derived(batchIndex >= batchFiles.length - 1);

  // Blank-key rows are just in-progress additions, not errors — they're
  // ignored on upload rather than blocked.
  function customFieldKeyError(key: string, index: number): string | null {
    const trimmed = key.trim().toLowerCase();
    if (!trimmed) return null;
    if (RESERVED_METADATA_KEYS.includes(trimmed)) return 'Reserved field name';
    if (customFields.some((f, i) => i !== index && f.key.trim().toLowerCase() === trimmed)) return 'Duplicate field name';
    return null;
  }

  const hasCustomFieldErrors = $derived(
    customFields.some((f, i) => customFieldKeyError(f.key, i) !== null)
  );

  const customFieldsRecord = $derived(
    Object.fromEntries(
      customFields
        .filter((f, i) => f.key.trim() && !customFieldKeyError(f.key, i))
        .map((f) => [f.key.trim(), f.value])
    )
  );

  let customFieldsListEl: HTMLDivElement | null = $state(null);

  async function addCustomField() {
    customFields = [...customFields, { key: '', value: '' }];
    await tick();
    customFieldsListEl?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function removeCustomField(index: number) {
    customFields = customFields.filter((_, i) => i !== index);
  }

  let isDragOver = $state(false);
  const EXCEL_EXTS = ['.xlsx', '.xlsm'];

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

    let selected: SelectedFile[];
    const items = e.dataTransfer?.items;
    const traversed = items && items.length ? await fromDataTransferItems(items) : null;
    if (traversed) {
      selected = traversed;
    } else {
      selected = Array.from(e.dataTransfer?.files ?? [])
        .filter(f => ACCEPTED_EXTS.some(ext => f.name.toLowerCase().endsWith(ext)))
        .map(f => ({ file: f, relPath: f.name }));
    }
    if (!selected.length) return;

    if (batchMode === 'interactive' && batchFiles.length > 0) {
      batchFiles = [...batchFiles, ...selected.map(s => s.file)];
      batchItems = [...batchItems, ...selected.map(s => ({ file: s.file, relPath: s.relPath, status: 'pending' as const }))];
    } else {
      toBatch(selected);
      batchIndex = 0;
      resetFileState();
      if (selected.length === 1) {
        batchMode  = 'interactive';
        uploadFile = selected[0].file;
        await triggerParse();
      } else {
        batchMode = null;
      }
    }
  }

  function toBatch(selected: { file: File; relPath?: string }[]) {
    batchFiles = selected.map(s => s.file);
    batchItems = selected.map(s => ({ file: s.file, relPath: s.relPath, status: 'pending' as const }));
  }

  function resetFileState() {
    uploadFile      = null;
    docStep         = 'select';
    parsing         = false;
    parseError      = null;
    parseDone       = false;
    markdownContent = '';
    previewRaw      = false;
    metadata        = {};
    customFields    = [];
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
    uploadLanguage   = '';
    uploadDone       = false;
    resetFileState();
  }

  function closeModal() {
    openModal();
    onClose();
  }

  async function onFileChange(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) return;

    toBatch(files.map(f => ({ file: f })));
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
    const batchId = createBatchToast(collectionName, batchFiles.length);

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
          parsedMeta = Object.fromEntries(ALL_METADATA_KEYS.map((key) => [key, (pdat.metadata ?? {})[key] ?? '']));
      } catch { /* proceed with empty metadata */ }

      batchItems[i] = { ...batchItems[i], status: 'queued' };
      batchItems = [...batchItems];

      const capturedI = i;
      const contentHash = await sha256Hex(file);
      enqueueUpload({
        id: crypto.randomUUID(),
        file,
        relPath: batchItems[i].relPath,
        collection: collectionName,
        tenants: uploadTenants,
        itrTemplate: uploadITR,
        metadata: parsedMeta,
        language: uploadLanguage,
        syncId: MANUAL_SYNC_ID,
        contentHash,
        onDone: (n_chunks, info) => {
          batchItems[capturedI] = { ...batchItems[capturedI], status: 'done', n_chunks, duplicateOf: info?.duplicateOf };
          batchItems = [...batchItems];
        },
        onError: (err) => {
          batchItems[capturedI] = { ...batchItems[capturedI], status: 'error', error: err };
          batchItems = [...batchItems];
        },
      }, batchId);
    }

    autoRunning = false;
    uploadDone = true;
  }

  // Best-effort match of a parsed classification string against the
  // controlled option list. Returns '' when unsure — Classification is
  // required in step 2, so an uncertain guess must fall back to an explicit
  // user choice rather than silently picking the wrong value.
  function guessClassification(raw: string | undefined | null): string {
    if (!raw) return '';
    const cleaned = raw.trim().toLowerCase();
    const match = DOCUMENT_CLASSIFICATION_OPTIONS.find(
      (opt) => opt.value === cleaned || opt.label.toLowerCase() === cleaned
    );
    return match?.value ?? '';
  }

  // @MRS-102
  async function triggerParse() {
    if (!uploadFile) return;
    docStep         = 'select';
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
        parseError     = data.parse_error;
        metadata       = Object.fromEntries(ALL_METADATA_KEYS.map((key) => [key, '']));
        uploadLanguage = '';
      } else {
        const raw: Record<string, string> = data.metadata ?? {};
        metadata = Object.fromEntries(ALL_METADATA_KEYS.map((key) => [key, raw[key] ?? '']));
        metadata.classification = guessClassification(raw.classification);
        uploadLanguage = guessLanguage(raw.lang);
      }
      parseDone = true;
    } catch (err: any) {
      parseError      = err.message ?? 'Could not parse document.';
      markdownContent = '';
      metadata        = Object.fromEntries(ALL_METADATA_KEYS.map((key) => [key, '']));
      uploadLanguage  = '';
      parseDone       = true;
    } finally {
      parsing = false;
    }
  }

  function onITRChange() { if (uploadFile) triggerParse(); }

  async function _enqueue(i: number) {
    const file = batchFiles[i];
    batchItems[i] = { ...batchItems[i], status: 'queued' };
    batchItems = [...batchItems];
    const contentHash = await sha256Hex(file);
    enqueueUpload({
      id: crypto.randomUUID(),
      file,
      relPath: batchItems[i].relPath,
      collection: collectionName,
      tenants: uploadTenants,
      itrTemplate: uploadITR,
      metadata: { ...metadata, ...customFieldsRecord },
      language: uploadLanguage,
      selectedSheets: isExcel && selectedSheets.length > 0 && selectedSheets.length < allSheets.length
        ? [...selectedSheets] : undefined,
      syncId: MANUAL_SYNC_ID,
      contentHash,
      onDone: (n_chunks, info) => {
        batchItems[i] = { ...batchItems[i], status: 'done', n_chunks, duplicateOf: info?.duplicateOf };
        batchItems = [...batchItems];
        if (!isBatch) onSuccess?.(collectionName, [...uploadTenants]);
      },
      onError: (err) => {
        batchItems[i] = { ...batchItems[i], status: 'error', error: err };
        batchItems = [...batchItems];
      },
    });
  }

  // @MRS-102
  async function handleUpload() {
    if (!uploadFile) return;
    await _enqueue(batchIndex);
    if (isBatch) { uploadDone = true; } else { closeModal(); }
  }

  async function uploadAndNext() {
    if (!uploadFile) return;
    await _enqueue(batchIndex);
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
    docStep === 'details'                    ? 'Document Information' :
    (batchMode === 'interactive' && isBatch) ? `Upload (${batchIndex + 1} / ${batchFiles.length})` :
                                               'Add Document'
  }
  {open}
  onClose={closeModal}
  wide={true}
  xl={docStep === 'select' && parseDone && !uploadDone}
  closeLabel="Cancel"
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
          <span class="batch-filename">{item.relPath ?? item.file.name}</span>
          <span class="batch-file-status">
            {#if item.status === 'queued'}Queued…
            {:else if item.status === 'uploading'}Uploading…
            {:else if item.status === 'done' && item.duplicateOf}Duplicate of {item.duplicateOf}
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
          <span class="batch-filename">{item.relPath ?? item.file.name}</span>
          <span class="batch-file-status">
            {#if item.status === 'parsing'}Parsing…
            {:else if item.status === 'queued'}Queued…
            {:else if item.status === 'done' && item.duplicateOf}Duplicate of {item.duplicateOf}
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
            title={item.relPath ?? item.file.name}
            onclick={() => { batchIndex = i; loadFileAtIndex(i); }}
          >{i + 1}</button>
        {/each}
        <span class="queue-label">{batchIndex + 1} of {batchFiles.length}</span>
      </div>
    {/if}

    {#if docStep === 'select'}
      <div class="upload-layout" class:upload-layout-lg={parseDone}>
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
      </div>
    {:else}
      <div class="upload-details">
        <label class="field field-full">
          <span>Title</span>
          <input type="text" bind:value={metadata.title} placeholder="—" />
        </label>

        <div class="field-row">
          <label class="field">
            <span>Author</span>
            <input type="text" bind:value={metadata.author} placeholder="—" />
          </label>
          <label class="field">
            <span>Publisher</span>
            <input type="text" bind:value={metadata.publisher} placeholder="—" />
          </label>
        </div>

        <div class="field-row">
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
            <span>Language <span class="req">*</span>
              <span class="info-icon" use:tooltip={"Selected Language determines the stemmer used for keyword search."}><InfoIcon/></span>
            </span>
            <select bind:value={uploadLanguage} required>
              <option value="" disabled>Select…</option>
              {#each LANGUAGE_OPTIONS as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="field-row">
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
            <div class="custom-fields-list" bind:this={customFieldsListEl}>
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
      </div>
    {/if}
  {/if}

  <svelte:fragment slot="footer">
    {#if uploadDone}
      <button class="action-btn" onclick={openModal}>Upload another</button>
    {:else if batchMode === 'interactive' || (batchMode === null && !isBatch)}
      {#if docStep === 'select'}
        {#if isBatch && !isLastFile}
          <button class="secondary-btn" onclick={skipCurrent} disabled={parsing}>Skip</button>
        {/if}
        <button class="action-btn" onclick={() => (docStep = 'details')}
          disabled={!uploadFile || parsing || !!parseError || (isExcel && allSheets.length > 1 && selectedSheets.length === 0)}>
          Proceed
        </button>
      {:else}
        <button class="secondary-btn" onclick={() => (docStep = 'select')} disabled={parsing}>Back</button>
        {#if isBatch && !isLastFile}
          <button class="secondary-btn" onclick={skipCurrent} disabled={parsing}>Skip</button>
          <button class="action-btn" onclick={uploadAndNext}
            disabled={!uploadFile || parsing || !metadata.classification || !uploadLanguage || hasCustomFieldErrors}>
            Upload & Next
          </button>
        {:else}
          <button class="action-btn" onclick={handleUpload}
            disabled={!uploadFile || parsing || !metadata.classification || !uploadLanguage || hasCustomFieldErrors}>
            {isBatch ? 'Upload & Finish' : 'Upload'}
          </button>
        {/if}
      {/if}
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

/* ── Upload layout (step 1: select & preview) ── */
.upload-layout {
  display: grid; grid-template-columns: 240px 1fr; gap: 1.25rem;
  height: 420px;
  transition: height 180ms ease;
}
.upload-layout.upload-layout-lg {
  height: min(65vh, 780px);
}
.upload-left  { display: flex; flex-direction: column; gap: 0.875rem; overflow-y: auto; min-height: 0; }
.upload-right { display: flex; flex-direction: column; gap: 0.5rem; position: relative; overflow: hidden; }

/* ── Document information (step 2) ── */
.upload-details {
  display: flex; flex-direction: column; gap: 1.25rem;
  min-height: 300px;
}
.field-full { width: 100%; }
.field-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;
}

/* ── Custom fields (step 2) ── */
.custom-fields { display: flex; flex-direction: column; gap: 0.5rem; }
.custom-fields-actions { display: flex; justify-content: flex-end; font-size: smaller;}
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
