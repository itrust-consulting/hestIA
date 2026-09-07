<script lang="ts">
  import { page } from '$app/state';
  import { goto, invalidateAll } from '$app/navigation';
  import { onMount } from 'svelte';
  import HelpSidebar from '$lib/components/HelpSidebar.svelte';
  import DiagramModal from '$lib/components/modals/DiagramModal.svelte';
  import ImageManagerModal from '$lib/components/modals/ImageManagerModal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import { api } from '$lib/api/client';
  import { marked } from '$lib/render/markdown';
  import DOMPurify from 'isomorphic-dompurify';
  import { addToast } from '$lib/stores/toast';
  import EditIcon from '$lib/components/icons/editIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  let { data } = $props();

  let editing    = $state(false);
  let editContent = $state('');
  let saving     = $state(false);
  let confirmDeleteOpen = $state(false);
  let mermaidLib = $state<any>(null);
  let contentEl  = $state<HTMLDivElement | undefined>(undefined);
  let previewEl  = $state<HTMLDivElement | undefined>(undefined);
  let modalSvg         = $state<string | null>(null);
  let imageManagerOpen = $state(false);
  let textareaEl       = $state<HTMLTextAreaElement | undefined>(undefined);
  let insertCursor     = $state(0);

  const isAdmin     = $derived(page.data.user?.permissions?.is_admin === true);
  const rendered    = $derived(DOMPurify.sanitize(marked.parse(data.content) as string));
  const editRendered = $derived(DOMPurify.sanitize(marked.parse(editContent) as string));

  function getMermaidTheme(): 'dark' | 'default' {
    // Layout applies the .dark class in its own onMount, which fires AFTER ours
    // (Svelte mounts children before parents). Read from localStorage directly
    // so we get the correct theme on first load without waiting for the class.
    const stored = localStorage.getItem('theme');
    const isDark =
      stored === 'dark' ||
      document.documentElement.classList.contains('dark') ||
      (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches);
    return isDark ? 'dark' : 'default';
  }

  function rerenderMermaid() {
    // Restore original source text so mermaid can re-process with the new theme
    document.querySelectorAll('pre.mermaid[data-processed]').forEach((el) => {
      const src = (el as HTMLElement).dataset.mermaidSrc;
      if (src) {
        el.removeAttribute('data-processed');
        (el as HTMLElement).textContent = src;
      }
    });
    const nodes = Array.from(document.querySelectorAll('pre.mermaid:not([data-processed])'));
    if (nodes.length) mermaidLib?.run({ nodes });
  }

  // @MRS-086
  onMount(() => {
    let observer: MutationObserver | undefined;

    (async () => {
      const mod = await import('mermaid');
      mermaidLib = mod.default;
      mermaidLib.initialize({ startOnLoad: false, theme: getMermaidTheme() });

      // Re-render diagrams whenever the user toggles light/dark mode
      observer = new MutationObserver(() => {
        mermaidLib.initialize({ startOnLoad: false, theme: getMermaidTheme() });
        rerenderMermaid();
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    })();

    return () => observer?.disconnect();
  });

  $effect(() => {
    rendered;
    if (mermaidLib && contentEl) {
      const nodes = Array.from(contentEl.querySelectorAll<HTMLElement>('pre.mermaid:not([data-processed])'));
      if (nodes.length) {
        // Persist source so rerenderMermaid() can restore it on theme toggle
        nodes.forEach(n => { if (!n.dataset.mermaidSrc) n.dataset.mermaidSrc = n.textContent ?? ''; });
        mermaidLib.run({ nodes });
      }
    }
  });

  $effect(() => {
    editRendered;
    if (mermaidLib && previewEl) {
      const nodes = Array.from(previewEl.querySelectorAll<HTMLElement>('pre.mermaid:not([data-processed])'));
      if (nodes.length) {
        nodes.forEach(n => { if (!n.dataset.mermaidSrc) n.dataset.mermaidSrc = n.textContent ?? ''; });
        mermaidLib.run({ nodes });
      }
    }
  });

  // Cancel edit when navigating to a different section
  $effect(() => {
    data.section;
    editing = false;
  });

  // ── Edit ────────────────────────────────────────────

  function startEdit() {
    editContent = data.content;
    editing = true;
  }

  function cancelEdit() {
    editing = false;
  }

  async function saveEdit() {
    saving = true;
    try {
      const res = await api.put(`/api/help/${data.section}`, { content: editContent });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? 'Failed to save page.');
      }
      editing = false;
      addToast('Page saved.', 'success');
      await invalidateAll();
    } catch (e: any) {
      addToast(e.message ?? 'Failed to save page.', 'error');
    } finally {
      saving = false;
    }
  }

  // ── Create ──────────────────────────────────────────

  async function createSection(title: string) {
    const slug = title
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');

    if (!slug) return;

    const initial = `# ${title}\n\nWrite your content here.\n`;
    try {
      const res = await api.put(`/api/help/${slug}`, { content: initial });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? 'Failed to create page.');
      }
      addToast('Page created.', 'success');
      await invalidateAll();
      goto(`/help?section=${slug}`);
    } catch (e: any) {
      addToast(e.message ?? 'Failed to create page.', 'error');
    }
  }

  // ── Diagram modal ───────────────────────────────────

  function handleContentClick(e: MouseEvent) {
    const svg = (e.target as Element).closest('svg');
    if (!svg || !contentEl?.contains(svg)) return;
    // Clone and strip mermaid's inline max-width so the modal can size it freely
    const clone = svg.cloneNode(true) as SVGElement;
    clone.removeAttribute('style');
    clone.removeAttribute('width');
    clone.removeAttribute('height');
    modalSvg = clone.outerHTML;
  }

  // ── Image paste ─────────────────────────────────────

  async function handleImagePaste(e: ClipboardEvent) {
    const imageItem = Array.from(e.clipboardData?.items ?? [])
      .find(item => item.type.startsWith('image/'));
    if (!imageItem) return; // no image — let normal paste proceed

    e.preventDefault();
    const blob = imageItem.getAsFile();
    if (!blob) return;

    const ta = e.target as HTMLTextAreaElement;
    const before = editContent.slice(0, ta.selectionStart);
    const after  = editContent.slice(ta.selectionEnd);

    // Insert placeholder so the author sees something immediately
    const placeholder = '![uploading…]()';
    editContent = `${before}${placeholder}${after}`;

    const form = new FormData();
    form.append('file', blob, `paste-${Date.now()}.png`);

    try {
      const res = await fetch('/api/help/images', { method: 'POST', body: form });
      if (res.ok) {
        const { url } = await res.json();
        editContent = editContent.replace(placeholder, `![image](${url})`);
      } else {
        editContent = editContent.replace(placeholder, '');
        addToast('Failed to upload image.', 'error');
      }
    } catch {
      editContent = editContent.replace(placeholder, '');
      addToast('Failed to upload image.', 'error');
    }
  }

  // ── Delete ──────────────────────────────────────────

  async function handleDeleteConfirm() {
    const res = await api.delete(`/api/help/${data.section}`);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail ?? 'Failed to delete page.');
    }
    const remaining = data.sections.filter((s: any) => s.id !== data.section);
    const next = remaining[0]?.id ?? 'getting-started';
    await invalidateAll();
    goto(`/help?section=${next}`);
  }
</script>

<div class="layout">
  <HelpSidebar
    sections={data.sections}
    currentSection={data.section}
    {isAdmin}
    onCreate={createSection}
  />

  <main class="page-content">

    {#if editing}
      <div class="edit-toolbar">
        <span class="edit-label">Editing — <em>{data.section}</em></span>
        <div class="edit-actions">
          <button class="btn-danger" onclick={() => (confirmDeleteOpen = true)}>
            Delete page
          </button>
          <button class="btn-secondary" onclick={() => {
            insertCursor = textareaEl?.selectionStart ?? editContent.length;
            imageManagerOpen = true;
          }}>Images</button>
          <button class="btn-secondary" onclick={cancelEdit}>Cancel</button>
          <button class="btn-primary" onclick={saveEdit} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      <div class="editor-layout">
        <div class="editor-pane">
          <textarea
            class="editor-textarea"
            bind:value={editContent}
            bind:this={textareaEl}
            placeholder="Write markdown here…"
            spellcheck="false"
            onkeydown={(e) => {
              if (e.key === 'Enter') e.stopPropagation();
              if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveEdit();
              }
            }}
            onpaste={handleImagePaste}
          ></textarea>
        </div>
        <div class="editor-pane editor-preview help-section" bind:this={previewEl}>
          {@html editRendered}
        </div>
      </div>

    {:else}
      <div class="content-card">
        {#if isAdmin}
          <button class="edit-btn" aria-label="Edit this section" use:tooltip={"Edit"} onclick={startEdit}>
            <EditIcon />
          </button>
        {/if}
        <div class="help-section" bind:this={contentEl} onclick={handleContentClick}>
          {@html rendered}
        </div>
      </div>
    {/if}

  </main>
</div>

<DiagramModal
  open={!!modalSvg}
  onClose={() => modalSvg = null}
  svgHtml={modalSvg ?? ''}
/>

<ImageManagerModal
  open={imageManagerOpen}
  onClose={() => imageManagerOpen = false}
  onInsert={(md) => {
    const before = editContent.slice(0, insertCursor);
    const after  = editContent.slice(insertCursor);
    const sep    = before.length > 0 && !before.endsWith('\n') ? '\n' : '';
    editContent  = `${before}${sep}${md}\n${after}`;
    imageManagerOpen = false;
  }}
/>

<ConfirmDeleteModal
  open={confirmDeleteOpen}
  title="Delete Page"
  onClose={() => (confirmDeleteOpen = false)}
  onConfirm={handleDeleteConfirm}
  successMessage="Page deleted."
>
  <p>Delete <strong>{data.section}</strong>? This cannot be undone.</p>
</ConfirmDeleteModal>

<style>
  .layout {
    display: flex;
    height: 100%;
    overflow: hidden;
  }

  .page-content {
    flex: 1;
    padding: 2rem;
    overflow-y: auto;
    position: relative;
  }

  /* ── Content card (view mode) ────────────────────── */

  .content-card {
    position: relative;
    max-width: 860px;
    margin: 0 auto;
    background: var(--color-neutral-50);
    padding: 2.5rem 3rem;
    border-radius: var(--radius-2xl);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  }

  /* ── Normal view ─────────────────────────────────── */

  .help-section {
    /* max-width handled by .content-card */
  }

  .help-section :global(h1) {
    font-size: var(--text-2xl);
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .help-section :global(h2) {
    font-size: var(--text-lg);
    font-weight: 600;
    margin-top: 1.75rem;
    margin-bottom: 0.5rem;
  }

  .help-section :global(p) {
    font-size: var(--text-sm);
    line-height: 1.7;
    color: var(--color-neutral-700);
    text-align: justify;
  }

  .help-section :global(li) {
    font-size: var(--text-sm);
    line-height: 1.7;
    color: var(--color-neutral-700);
  }

  /* ── Unordered lists ─────────────────────────────── */

  .help-section :global(ul) {
    padding-left: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  /* ── Ordered lists → step cards ──────────────────── */

  .help-section :global(ol) {
    list-style: none;
    padding-left: 0;
    counter-reset: step-counter;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0.75rem 0;
  }

  .help-section :global(ol > li) {
    counter-increment: step-counter;
    display: flex;
    gap: 0.875rem;
    align-items: flex-start;
    padding: 0.75rem 1rem;
    background: var(--color-neutral-50);
    border: 1px solid var(--color-neutral-200);
    border-radius: var(--radius-lg);
  }

  .help-section :global(ol > li::before) {
    content: counter(step-counter);
    flex-shrink: 0;
    width: 1.5rem;
    height: 1.5rem;
    background: var(--color-blue-600);
    color: white;
    border-radius: 50%;
    font-size: 0.7rem;
    font-weight: 700;
    line-height: 1.5rem;
    text-align: center;
    display: block;
    margin-top: 0.1rem;
  }

  /* ── Alert callouts (> [!WARNING] etc.) ──────────── */

  .help-section :global(.callout) {
    border-radius: var(--radius-md);
    padding: 0.75rem 1rem;
    margin: 1rem 0;
    border-left: 4px solid;
  }

  .help-section :global(.callout-label) {
    display: block;
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.25rem;
  }

  .help-section :global(.callout p) {
    text-align: left;
    margin: 0;
    color: inherit;
  }

  .help-section :global(.callout-warning),
  .help-section :global(.callout-caution) {
    background: var(--color-yellow-50);
    border-color: var(--color-yellow-400);
    color: var(--color-yellow-700);
  }

  .help-section :global(.callout-note) {
    background: var(--color-blue-50);
    border-color: var(--color-blue-600);
    color: var(--color-blue-700);
  }

  .help-section :global(.callout-important) {
    background: var(--color-red-50);
    border-color: var(--color-red-600);
    color: var(--color-red-700);
  }

  .help-section :global(.callout-tip) {
    background: var(--color-green-50);
    border-color: var(--color-green-600);
    color: var(--color-green-700);
  }

  .help-section :global(blockquote) {
    border-left: 3px solid var(--color-neutral-400);
    margin: 1rem 0;
    padding: 0.5rem 1rem;
    color: var(--color-neutral-500);
    font-size: var(--text-sm);
    font-style: italic;
  }

  .help-section :global(table) {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-sm);
    margin-top: 0.75rem;
  }

  .help-section :global(th),
  .help-section :global(td) {
    text-align: left;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--color-neutral-200);
  }

  .help-section :global(th) {
    font-weight: 600;
    color: var(--color-neutral-600);
    background: var(--color-neutral-100);
  }

  .help-section :global(details) {
    border-bottom: 1px solid var(--color-neutral-200);
    padding: 0.75rem 0;
  }

  .help-section :global(details:first-of-type) {
    border-top: 1px solid var(--color-neutral-200);
  }

  .help-section :global(summary) {
    cursor: pointer;
    font-weight: 500;
    font-size: var(--text-sm);
    user-select: none;
    list-style: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .help-section :global(summary::after) {
    content: '+';
    font-size: var(--text-lg);
    color: var(--color-neutral-400);
  }

  .help-section :global(details[open] summary::after) {
    content: '−';
  }

  .help-section :global(details p) {
    margin-top: 0.5rem;
    padding-left: 0.5rem;
  }

  /* ── Edit button ─────────────────────────────────── */

  .edit-btn {
    position: absolute;
    top: 1.25rem;
    right: 1.25rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.35rem;
    border: 1px solid var(--color-neutral-300);
    border-radius: var(--radius-md);
    background: var(--color-white);
    color: var(--color-neutral-700);
    cursor: pointer;
    transition: background-color 120ms ease, border-color 120ms ease;
  }

  .edit-btn:hover {
    background: var(--color-neutral-100);
    border-color: var(--color-neutral-400);
  }

  /* ── Edit toolbar ────────────────────────────────── */

  .edit-toolbar {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--color-white);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid var(--color-neutral-200);
  }

  .edit-label {
    font-size: var(--text-sm);
    color: var(--color-neutral-600);
  }

  .edit-actions {
    display: flex;
    gap: 0.5rem;
  }

  .btn-primary,
  .btn-secondary,
  .btn-danger {
    padding: 0.35rem 0.9rem;
    font-size: var(--text-sm);
    font-weight: 500;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: background-color 120ms ease;
  }

  .btn-primary {
    background: var(--color-blue-600);
    color: var(--color-white);
    border: none;
  }

  .btn-primary:hover:not(:disabled) { background: var(--color-blue-700); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

  .btn-secondary {
    background: var(--color-white);
    color: var(--color-neutral-700);
    border: 1px solid var(--color-neutral-300);
  }

  .btn-secondary:hover { background: var(--color-neutral-100); }

  .btn-danger {
    background: var(--color-white);
    color: var(--color-red-600);
    border: 1px solid var(--color-red-300);
  }

  .btn-danger:hover:not(:disabled) {
    background: var(--color-red-50);
  }

  .btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Split editor ────────────────────────────────── */

  .editor-layout {
    display: flex;
    gap: 1rem;
    height: calc(100vh - var(--header-height) - 5rem);
  }

  .editor-pane {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
  }

  .editor-textarea {
    width: 100%;
    height: 100%;
    font-family: 'Menlo', 'Consolas', monospace;
    font-size: var(--text-sm);
    line-height: 1.6;
    padding: 0.75rem;
    border: 1px solid var(--color-neutral-300);
    border-radius: var(--radius-md);
    background: var(--color-neutral-50);
    color: var(--color-neutral-900);
    resize: none;
    outline: none;
  }

  .editor-textarea:focus { border-color: var(--color-blue-300); }

  .editor-preview {
    padding: 0.75rem;
    border: 1px solid var(--color-neutral-200);
    border-radius: var(--radius-md);
    background: var(--color-white);
    max-width: none;
  }

  /* ── Mermaid ─────────────────────────────────────── */

  /* Reset pre.mermaid before mermaid processes it — prevents hljs dark theme bleeding in */
  :global(pre.mermaid) {
    background: transparent !important;
    padding: 0;
    border: none;
    box-shadow: none;
  }

  :global(.mermaid) {
    margin: 1rem 0;
    text-align: center;
  }

  :global(.mermaid svg) {
    border-radius: var(--radius-md);
    max-width: 100%;
    cursor: zoom-in;
    transition: opacity 120ms ease;
  }

  :global(.mermaid svg:hover) {
    opacity: 0.85;
  }

  /* ── Block images (screenshots, diagrams) ───────── */

  .help-section :global(img:not(.icon-img)) {
    display: block;
    max-width: 100%;
    height: auto;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-neutral-200);
    margin: 0.75rem 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  /* ── Inline UI icons ─────────────────────────────── */

  :global(.icon-img) {
    display: inline;
    width: 1em;
    height: 1em;
    vertical-align: -0.15em;
    margin: 0 0.1em;
  }

  /* Invert to near-white in dark mode (currentColor → black → white) */
  :global(html.dark .icon-img) {
    filter: invert(0.85);
  }

  /* Button-chip style for referencing UI buttons inline in text */
  :global(.ui-btn) {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    background: var(--color-neutral-100);
    border: 1px solid var(--color-neutral-200);
    border-radius: var(--radius-md);
    padding: 0.15em 0.6em;
    font-size: 0.875em;
    font-weight: 500;
    white-space: nowrap;
    vertical-align: middle;
  }

</style>
